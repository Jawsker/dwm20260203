"""Puertos y ubicación de cada pieza (misma convención que el material del curso).

gateway 8000 · auth-service 8100 · GraphQL 8090 · backends privados 9000, 9100, 9200, 9300
Vault 8200 · MongoDB 27017 · broker STOMP 61613
"""
PORTS = {"gateway": 8000, "auth": 8100, "graphql": 8090,
         "inventory": 9000, "orders": 9100, "clients": 9200, "payments": 9300}

# servicio -> (carpeta relativa a evaluacion2, módulo de uvicorn)
LAYOUT = {
    "gateway": ("apigateway/gateway", "gateway"),
    "auth": ("apigateway/auth-service", "auth_service"),
    "inventory": ("apigateway/inventory", "backend_api"),
    "orders": ("apigateway/orders", "backend_api"),
    "clients": ("apigateway/clients", "backend_api"),
    "payments": ("apigateway/payments", "backend_api"),
    "graphql": ("graphql", "server"),
}


def default_url(service: str) -> str:
    """URL por nombre de servicio (red de contenedores). En local se reemplaza con LR_<SERVICIO>_URL."""
    return f"http://{service}:{PORTS[service]}"
