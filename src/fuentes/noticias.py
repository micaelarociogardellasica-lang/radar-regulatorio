"""Fuente de noticias: Google News RSS.

Fase 1: consulta una lista de queries configurables (PROYECTO.md sección 2),
trae los últimos ítems de cada una dentro de una ventana de días (para no
reprocesar la misma noticia en cada corrida) y los deja listos con la misma
interfaz que `NormaCandidata` (norma_id, organismo, fecha_bo, url_detalle,
texto_completo, codigo, rubro, tipo) para que `src/analisis.py` los procese
sin distinguir la fuente.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

import feedparser
import requests

from fuentes.http import sesion_resiliente


def _partir_fuente(titulo: str) -> tuple[str, str | None]:
    """Google News suele armar el título como 'Título de la nota - Medio'."""
    if " - " in titulo:
        cuerpo, medio = titulo.rsplit(" - ", 1)
        return cuerpo.strip(), medio.strip()
    return titulo.strip(), None


@dataclass
class NoticiaCandidata:
    query: str
    titulo: str
    fuente: str | None
    fecha_pub: str | None  # YYYY-MM-DD
    link: str
    tipo: str = "noticia"
    rubro: str = "NOTICIA"
    codigo: str | None = None

    def __post_init__(self):
        # Identificador único y estable por artículo — el badge (norma_id)
        # es la query, no sirve para diferenciar ítems de una misma corrida.
        self.codigo = hashlib.sha1(self.link.encode("utf-8")).hexdigest()[:10]

    @property
    def norma_id(self) -> str:
        return f"NOTICIA · {self.query.upper()}"

    @property
    def organismo(self) -> str | None:
        return self.fuente or "Prensa"

    @property
    def fecha_bo(self) -> str | None:
        return self.fecha_pub

    @property
    def url_detalle(self) -> str:
        return self.link

    @property
    def texto_completo(self) -> str:
        return self.titulo

    @property
    def titulo_sumario(self) -> str:
        # El título de Google News hace de "epígrafe": es la única
        # descripción de la noticia disponible sin llamar a la API.
        return self.titulo


class NoticiasScraper:
    def __init__(self, config: dict, session: requests.Session | None = None):
        self.config = config.get("noticias", {})
        self.session = session or sesion_resiliente()

    def _url_rss(self, query: str) -> str:
        idioma = self.config.get("idioma", "es-419")
        region = self.config.get("region", "AR")
        return (
            f"https://news.google.com/rss/search?q={quote(query)}"
            f"&hl={idioma}&gl={region}&ceid={region}:{idioma.split('-')[0]}"
        )

    def _relevar_query(self, query: str, desde: date) -> list[NoticiaCandidata]:
        resp = self.session.get(self._url_rss(query), timeout=30)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)

        max_items = self.config.get("max_items_por_query", 6)
        candidatos = []
        for entry in parsed.entries[:max_items]:
            fecha_pub = None
            if getattr(entry, "published_parsed", None):
                fecha_pub = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).date()
                if fecha_pub < desde:
                    continue

            titulo_crudo = entry.get("title", "").strip()
            titulo, fuente_titulo = _partir_fuente(titulo_crudo)
            fuente = entry.get("source", {}).get("title") if entry.get("source") else fuente_titulo

            candidatos.append(NoticiaCandidata(
                query=query,
                titulo=titulo,
                fuente=fuente,
                fecha_pub=fecha_pub.isoformat() if fecha_pub else None,
                link=entry.get("link", ""),
            ))
        return candidatos

    def relevar(self, fecha: date | None = None) -> list[NoticiaCandidata]:
        """Trae noticias de todas las queries configuradas, dedupeadas por
        link, dentro de la ventana de días configurada."""
        fecha = fecha or date.today()
        ventana = self.config.get("ventana_dias", 2)
        desde = fecha - timedelta(days=ventana)

        vistos: set[str] = set()
        resultado: list[NoticiaCandidata] = []
        for query in self.config.get("queries", []):
            for candidato in self._relevar_query(query, desde):
                if not candidato.link or candidato.link in vistos:
                    continue
                vistos.add(candidato.link)
                resultado.append(candidato)
        return resultado
