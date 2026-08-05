"""Sesión HTTP compartida por los scrapers, con reintentos y espera exponencial,
más un fallback opcional vía proxy cuando el acceso directo queda bloqueado.

Diagnóstico del incidente en GitHub Actions:
1. Primer síntoma, "Temporary failure in name resolution": DNS transitorio
   del runner, resuelto con reintentos + backoff (`Retry(connect=...)` de
   urllib3 reintenta también sobre fallas de resolución, no solo HTTP 5xx).
2. Con el DNS resuelto, el BORA siguió fallando de forma más consistente
   desde Actions. La respuesta trae la cookie `TSxxxxxxxx=...`, firma típica
   de un WAF **F5 BIG-IP ASM** — estos WAF aplican bloqueo/rate-limit por
   reputación de IP notoriamente más agresivo contra rangos de datacenter
   (AWS/Azure/GCP, y por ende los runners de Actions) que contra IPs
   residenciales. Coincide con "funciona desde tu máquina, falla desde
   Actions" sin ser un bloqueo geográfico en sentido estricto.

Mitigación: `get_con_fallback` intenta el acceso directo primero (con los
reintentos de siempre) y, si falla, prueba una URL de proxy configurable
(`bora.proxy_url_template` en config.yaml) antes de rendirse — pensada para
un relay propio y gratuito (ver `scripts/proxy-bora-cloudflare-worker.js`) que
sale a internet desde una red distinta a la del runner. Si no hay proxy
configurado, se comporta igual que antes (falla directo a la corrida
marcando la fuente como caída, ver `src/main.py`).
"""
from __future__ import annotations

from urllib.parse import quote

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


def sesion_resiliente(reintentos: int = 3, backoff: float = 2.0) -> requests.Session:
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


def get_con_fallback(
    session: requests.Session,
    url: str,
    timeout: int = 30,
    proxy_url_template: str | None = None,
) -> requests.Response:
    """GET con reintentos (vía la sesión resiliente) y, si el acceso directo
    falla, un segundo intento a través de `proxy_url_template` (con `{url}`
    como placeholder de la URL original, ya URL-encodeada).

    Pensado para un relay propio (Cloudflare Worker u otro) que sale a
    internet desde una IP distinta a la del runner — no depende de proxies
    públicos de terceros, que en la práctica resultaron poco confiables
    (caídos o dados de baja) al evaluarlos para este mismo incidente.
    """
    try:
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp
    except requests.exceptions.RequestException as directo_exc:
        if not proxy_url_template:
            raise
        try:
            proxy_url = proxy_url_template.format(url=quote(url, safe=""))
            resp = session.get(proxy_url, timeout=timeout * 2)
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as proxy_exc:
            raise requests.exceptions.RequestException(
                f"acceso directo falló ({directo_exc}) y el proxy de respaldo también ({proxy_exc})"
            ) from proxy_exc
