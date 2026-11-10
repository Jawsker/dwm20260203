"""Topología de confianza: única fuente de verdad para aristas de servicio y servicios con base propia."""

SERVICES = ("gateway", "auth", "clients", "inventory", "orders", "payments", "graphql")
WITH_DB = ("auth", "clients", "inventory", "orders", "payments")  # graphql y gateway no tienen base

# arista = (llamador, destino): el llamador presenta la clave; el destino la verifica.
EDGES = [("gateway", d) for d in ("auth", "clients", "inventory", "orders", "payments", "graphql")] + [
    ("orders", "inventory"), ("orders", "payments"), ("payments", "orders"),
    ("graphql", "orders"), ("graphql", "inventory"), ("graphql", "clients"),
]

# secretos que no son de arista: referencia -> servicios que pueden leerlo
EXTRA = {"payments/webhook": ("payments",)}


def vault_paths_for(service: str) -> list[str]:
    """Referencias (sin el prefijo secret/data/lr/) que la política del servicio puede LEER."""
    paths = [f"edge/{a}__{b}" for a, b in EDGES if service in (a, b)]
    if service in WITH_DB:
        paths.append(f"db/{service}")
    paths += [p for p, who in EXTRA.items() if service in who]
    return paths
