import hashlib
import hmac
import json
import sys
import time
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from dev_local import PORTS, Stack  # noqa: E402

ORIGIN = "http://localhost:8080"
API = "/api/v1"


@pytest.fixture(scope="session")
def stack():
    s = Stack(overrides={"LR_ORDER_TTL_SECONDS": "6", "LR_SWEEP_INTERVAL_SECONDS": "1", "LR_RATE_LOGIN": "500",
                         "LR_RATE_WRITE": "500", "LR_LOGIN_MAX_FAILS": "5"}).start()
    yield s
    s.stop()


class Api:
    """Cliente de pruebas: conserva la cookie de sesión como lo haría un navegador."""

    def __init__(self, base: str, origin: str | None = ORIGIN):
        headers = {"Origin": origin} if origin else {}
        self.c = httpx.Client(base_url=base, headers=headers, timeout=15)

    def req(self, method, path, **kw):
        return self.c.request(method, API + path, **kw)

    def get(self, path, **kw): return self.req("GET", path, **kw)
    def post(self, path, **kw): return self.req("POST", path, **kw)
    def put(self, path, **kw): return self.req("PUT", path, **kw)
    def delete(self, path, **kw): return self.req("DELETE", path, **kw)

    def login(self, email, password):
        r = self.post("/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        return self

    def gql(self, query, variables=None):
        r = self.post("/graphql", json={"query": query, "variables": variables or {}})
        return r


def _client(stack, email):
    return Api(stack.base).login(email, stack.seed_password)


@pytest.fixture(scope="session")
def anon(stack): return Api(stack.base)
@pytest.fixture(scope="session")
def ana(stack): return _client(stack, "ana@ejemplo.cl")
@pytest.fixture(scope="session")
def beto(stack): return _client(stack, "beto@ejemplo.cl")
@pytest.fixture(scope="session")
def staff(stack): return _client(stack, "tienda@libreyrico.test")
@pytest.fixture(scope="session")
def admin(stack): return _client(stack, "admin@libreyrico.test")
@pytest.fixture(scope="session")
def audit(stack): return _client(stack, "auditoria@libreyrico.test")


def sign_event(secret: str, event: dict, ts: int | None = None) -> tuple[bytes, str]:
    raw = json.dumps(event, separators=(",", ":")).encode()
    ts = ts or int(time.time())
    mac = hmac.new(secret.encode(), f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()
    return raw, f"t={ts},v1={mac}"


def post_webhook(stack, raw: bytes, signature: str | None):
    headers = {"Content-Type": "application/json"}
    if signature is not None:
        headers["X-Provider-Signature"] = signature
    return httpx.post(f"{stack.base}{API}/webhooks/payments", content=raw, headers=headers, timeout=10)


def stock_of(staff_api: Api, pid: str) -> dict:
    r = staff_api.get("/admin/products", params={"q": "", "limit": 100})
    assert r.status_code == 200, r.text
    return next(p for p in r.json()["items"] if p["id"] == pid)


def place_order(api: Api, items, key=None, **extra):
    headers = {"Idempotency-Key": key} if key else {}
    return api.post("/orders", json={"items": items, **extra}, headers=headers)


def pay_and_decide(api: Api, order_id: str, outcome="approve"):
    r = api.post(f"/orders/{order_id}/pay")
    assert r.status_code == 200, r.text
    ref = r.json()["provider_ref"]
    d = api.post(f"/payments/{ref}/sandbox-decision", json={"outcome": outcome})
    assert d.status_code == 200, d.text
    return ref, d.json()


def wait_for(fn, timeout=12.0, step=0.3):
    end = time.time() + timeout
    last = None
    while time.time() < end:
        last = fn()
        if last:
            return last
        time.sleep(step)
    return last
