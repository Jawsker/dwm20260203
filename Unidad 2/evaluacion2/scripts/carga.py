#!/usr/bin/env python3
"""Prueba de carga REPRODUCIBLE (Módulo 9). Es una MEDICIÓN sobre el stack local, no una proyección.

Entorno: los 7 servicios como procesos locales, base mongomock (en memoria, sin red ni disco) y el
generador de carga en la misma máquina. Por eso las latencias de base de datos son optimistas y
la CPU del generador compite con la del sistema. Sirve para comparar contra los objetivos declarados
y para detectar cuellos de botella de la lógica propia, NO para dimensionar producción con MongoDB real.
Se desactivan los límites de solicitudes del gateway (se miden capacidades, no políticas).

Uso: python scripts/carga.py [--segundos 15] [--concurrencia 25] [--salida docs/evidencia/carga.md]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import platform
import random
import statistics
import time
import uuid
from pathlib import Path

import httpx
import psutil

import dev_local
from dev_local import Stack

ORIGIN = {"Origin": "http://localhost:8080"}
API = "/api/v1"

# Objetivos declarados ANTES de medir (volumen proyectado: ~200 pedidos/día, pico de sábado ~30 pedidos/hora,
# ~20 clientes simultáneos navegando; lecturas de catálogo ≈ 10× las escrituras).
OBJETIVOS = {
    "catalogo": ("GET /products (anónimo)", 300, 0.0),
    "graphql": ("POST /graphql pedidos+productos", 500, 0.0),
    "crear_pedido": ("POST /orders", 800, 0.0),
    "pagar": ("POST /orders/{id}/pay", 800, 0.0),
    "pago_sandbox": ("POST sandbox-decision (webhook→payments→orders→inventory)", 1500, 0.0),
    "panel": ("POST /graphql panelOperacion (agregación, ver volumen)", 1000, 0.0),
}


def pct(values, p):
    if not values:
        return float("nan")
    values = sorted(values)
    return values[min(len(values) - 1, int(round(p / 100 * (len(values) - 1))))]


class Medidor:
    def __init__(self):
        self.lat: dict[str, list[float]] = {}
        self.err: dict[str, int] = {}
        self.t0 = time.perf_counter()

    def ok(self, k, ms): self.lat.setdefault(k, []).append(ms)
    def fail(self, k): self.err[k] = self.err.get(k, 0) + 1


async def timed(m: Medidor, key: str, coro, expect=(200, 201)):
    t = time.perf_counter()
    try:
        r = await coro
    except httpx.HTTPError:
        m.fail(key); return None
    ms = (time.perf_counter() - t) * 1000
    if r.status_code in expect:
        m.ok(key, ms)
        return r
    m.fail(key)
    return r


async def sampler(stack: Stack, stop: asyncio.Event, out: dict):
    procs = {n: psutil.Process(p.pid) for n, p in stack.procs.items()}
    for p in procs.values():
        p.cpu_percent(None)
    while not stop.is_set():
        await asyncio.sleep(0.5)
        total = 0.0
        for n, p in procs.items():
            c = p.cpu_percent(None)
            total += c
            out.setdefault(n, {"cpu": [], "rss": 0})
            out[n]["cpu"].append(c)
            out[n]["rss"] = max(out[n]["rss"], p.memory_info().rss)
        out.setdefault("_total", {"cpu": [], "rss": 0})["cpu"].append(total)


async def run_phase(nombre, workers, segundos, worker_fn):
    deadline = time.perf_counter() + segundos
    m = Medidor()
    await asyncio.gather(*(worker_fn(i, m, deadline) for i in range(workers)))
    elapsed = time.perf_counter() - m.t0
    return m, elapsed


async def main_async(args):
    stack = Stack(overrides={"LR_RATE_PUBLIC": "10000000", "LR_RATE_AUTH": "10000000", "LR_RATE_WRITE": "10000000",
                             "LR_RATE_LOGIN": "10000000", "LR_ORDER_TTL_SECONDS": "3600",
                             "LR_SWEEP_INTERVAL_SECONDS": "0"}).start()
    cpu: dict = {}
    stop = asyncio.Event()
    samp = asyncio.create_task(sampler(stack, stop, cpu))
    resultados = {}
    try:
        base = stack.base
        # --- preparación: usuarios y stock alto
        admin = httpx.AsyncClient(base_url=base, headers=ORIGIN, timeout=30)
        await admin.post(API + "/auth/login", json={"email": "tienda@libreyrico.test", "password": stack.seed_password})
        for i in range(1, 13):
            await admin.put(f"{API}/admin/products/p{i:02d}/stock", json={"stock": 100000})
        clientes = []
        for i in range(args.concurrencia):
            c = httpx.AsyncClient(base_url=base, headers=ORIGIN, timeout=30)
            r = await c.post(API + "/auth/register", json={"email": f"carga{i}-{uuid.uuid4().hex[:5]}@ejemplo.cl",
                                                          "password": "Clave-de-carga-123", "nombre": f"Carga {i}"})
            assert r.status_code == 201, r.text
            clientes.append(c)
        anon = httpx.AsyncClient(base_url=base, timeout=30, limits=httpx.Limits(max_connections=args.concurrencia * 2))

        # --- Fase C primero (crea pedidos reales que luego lee GraphQL)
        async def w_escritura(i, m, deadline):
            c = clientes[i]
            while time.perf_counter() < deadline:
                items = [{"product_id": f"p{random.randint(1, 12):02d}", "qty": random.randint(1, 3)}
                         for _ in range(random.randint(1, 3))]
                items = list({x["product_id"]: x for x in items}.values())
                r = await timed(m, "crear_pedido", c.post(API + "/orders", json={"items": items}))
                if not r or r.status_code != 201: continue
                oid = r.json()["id"]
                r = await timed(m, "pagar", c.post(f"{API}/orders/{oid}/pay"))
                if not r or r.status_code != 200: continue
                ref = r.json()["provider_ref"]
                await timed(m, "pago_sandbox", c.post(f"{API}/payments/{ref}/sandbox-decision", json={"outcome": "approve"}))

        # --- Fase A: catálogo
        async def w_catalogo(i, m, deadline):
            while time.perf_counter() < deadline:
                await timed(m, "catalogo", anon.get(API + "/products?limit=100"))

        # --- Fase B: GraphQL con agregación
        Q = "{ pedidos(primeros:10){ total items{ id estado total lineas{ nombre cantidad producto{ emoji precio disponible } } } } }"

        async def w_graphql(i, m, deadline):
            c = clientes[i]
            while time.perf_counter() < deadline:
                r = await timed(m, "graphql", c.post(API + "/graphql", json={"query": Q}))
                if r is not None and r.status_code == 200 and "errors" in r.json():
                    m.fail("graphql")

        fases = [("escritura", w_escritura), ("catalogo", w_catalogo), ("graphql", w_graphql)]
        for nombre, fn in fases:
            m, elapsed = await run_phase(nombre, args.concurrencia, args.segundos, fn)
            resultados[nombre] = (m, elapsed)

        # --- Fase V: engordar la base (solo crear pedidos) hasta --pedidos-panel y medir el panel con ese volumen
        faltan = [max(0, args.pedidos_panel - sum(len(m.lat.get("crear_pedido", [])) for _, (m, _) in resultados.items()))]

        async def w_volumen(i, m, deadline):
            c = clientes[i]
            while faltan[0] > 0:
                faltan[0] -= 1
                await timed(m, "volumen", c.post(API + "/orders", json={"items": [{"product_id": f"p{random.randint(1, 12):02d}", "qty": 1}]}))

        t_vol = time.perf_counter()
        mv, _ = await run_phase("volumen", args.concurrencia, 0, w_volumen)
        resultados["volumen"] = (mv, time.perf_counter() - t_vol)

        # --- Fase D: reporte (panel) con todos los pedidos creados
        totales = (await admin.post(API + "/graphql", json={"query": "{ pedidos(primeros:1){ total } }"})).json()["data"]["pedidos"]["total"]
        mp = Medidor()
        for _ in range(30):
            await timed(mp, "panel", admin.post(API + "/graphql", json={"query": "{ panelOperacion{ ventasPagadas pedidosPorEstado{ estado cantidad } } }"}))
        resultados["panel"] = (mp, 0.0)
    finally:
        stop.set(); await samp
        stack.stop()
    return resultados, cpu, totales


def informe(resultados, cpu, total_pedidos, args) -> str:
    L = ["# Reporte de carga (Módulo 9)\n",
         "**Tipo de dato: MEDICIÓN** en el stack local de desarrollo (ver limitaciones). Los objetivos son una **proyección** declarada antes de medir.\n",
         "## Entorno y método\n",
         f"- Máquina: {platform.platform()}, {psutil.cpu_count()} vCPU, {round(psutil.virtual_memory().total / 2**30, 1)} GiB RAM; Python {platform.python_version()}.",
         "- Sistema: 7 procesos (gateway, auth, clients, inventory, orders, payments, graphql) con base **mongomock en memoria** (sin red ni disco).",
         f"- Generador de carga en la misma máquina: {args.concurrencia} clientes concurrentes con sesión propia; {args.segundos} s por fase; límites de solicitudes del gateway desactivados.",
         "- Datos: 12 productos con stock alto; pedidos creados por la propia fase de escritura (entre 1 y 3 líneas).",
         f"- Reproducir: `python scripts/carga.py --segundos {args.segundos} --concurrencia {args.concurrencia}`.\n",
         "## Resultados vs objetivos\n",
         "| Operación | n | req/s | p50 ms | p95 ms | p99 ms | errores | objetivo p95 | veredicto |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for key, (desc, obj, _) in OBJETIVOS.items():
        for _, (m, el) in resultados.items():
            if key in m.lat or key in m.err:
                lat = m.lat.get(key, [])
                n = len(lat); e = m.err.get(key, 0)
                p95 = pct(lat, 95)
                rps = f"{n / el:.1f}" if el else "—"
                ver = "cumple" if n and p95 <= obj and e == 0 else "NO cumple"
                L.append(f"| {desc} | {n} | {rps} | {pct(lat, 50):.0f} | {p95:.0f} | {pct(lat, 99):.0f} | {e} | {obj} | {ver} |")
    L += ["", f"Pedidos totales en la base al medir el panel: **{total_pedidos}** (proyección: ~200/día ≈ 73 000/año; este volumen equivale a ~25 días; la agregación es lineal en el número de pedidos, así que el año completo es una extrapolación NO medida).\n", "## CPU y memoria por proceso\n",
          "| Proceso | CPU media % | CPU máx % | RSS máx MiB |", "|---|---:|---:|---:|"]
    for name, d in cpu.items():
        if name == "_total":
            continue
        c = d["cpu"]
        L.append(f"| {name} | {statistics.mean(c):.0f} | {max(c):.0f} | {d['rss'] / 2**20:.0f} |")
    tot = cpu.get("_total", {"cpu": [0]})["cpu"]
    L.append(f"| **suma de servicios** | {statistics.mean(tot):.0f} | {max(tot):.0f} | — |")
    L += ["", "(100 % = un núcleo completo; el generador de carga no está incluido en la tabla.)\n",
          "## Limitaciones\n",
          "- mongomock no refleja la latencia de MongoDB real (red, disco, índices): las cifras de base de datos son **optimistas**.",
          "- Generador y sistema comparten CPU: las latencias son **pesimistas** por esa competencia. Ambos sesgos se compensan solo en parte.",
          "- Una sola ejecución sin calentamiento dedicado; no hay intervalos de confianza. Repetir en el entorno de despliegue real antes de afirmar capacidad de producción.",
          "- Fuera de alcance de la medición: red entre contenedores, TLS, Vault real (el cliente de secretos cachea 5 min).", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--segundos", type=int, default=15)
    ap.add_argument("--concurrencia", type=int, default=25)
    ap.add_argument("--pedidos-panel", type=int, default=5000, dest="pedidos_panel", help="volumen de pedidos para medir el panel")
    ap.add_argument("--salida", default=str(Path(__file__).resolve().parent.parent / "docs" / "evidencia" / "carga.md"))
    args = ap.parse_args()
    resultados, cpu, total = asyncio.run(main_async(args))
    texto = informe(resultados, cpu, total, args)
    Path(args.salida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.salida).write_text(texto, encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()
