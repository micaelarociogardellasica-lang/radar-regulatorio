"""Sesión HTTP compartida por los scrapers, con reintentos y espera exponencial.

Diagnóstico (ver incidente de la corrida en GitHub Actions): "Temporary
failure in name resolution" es un error transitorio de DNS del runner, no un
bloqueo geográfico del sitio — con headers de navegador y reintentos con
backoff, el pedido se resuelve en el segundo o tercer intento cuando el DNS
del runner tarda en asentarse. `Retry(connect=...)` de urllib3 reintenta
también sobre errores de resolución de nombre (no solo HTTP 5xx), así que
cubre este caso sin lógica extra.
"""
from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HEADERS_NAVEGADOR = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 "
        "RadarRegulatorioYPF/1.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}


def sesion_resiliente(reintentos: int = 5, backoff: float = 2.0) -> requests.Session:
    """Sesión con headers de navegador y reintentos con backoff exponencial
    (cubre fallas de DNS/red transitorias además de 5xx)."""
    session = requests.Session()
    session.headers.update(HEADERS_NAVEGADOR)

    retry = Retry(
        total=reintentos,
        connect=reintentos,
        read=reintentos,
        status=reintentos,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
