"""Scraper del Boletín Oficial de la República Argentina (BORA), Primera Sección.

Fase 1 (MVP): releva el sumario del día, filtra por emisor y keywords del
sector, y trae el texto completo de cada norma candidata para que
`src/analisis.py` la mande a la API de Claude.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RadarRegulatorioYPF/1.0)"
}


def normalizar(texto: str) -> str:
    """Mayúsculas y sin acentos, para comparar contra la config sin líos de tildes."""
    if not texto:
        return ""
    sin_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", sin_acentos).strip().upper()


@dataclass
class NormaCandidata:
    id_bora: str
    rubro: str
    organismo: str | None       # None cuando el rubro usa "item" como título (DECRETOS)
    titulo_sumario: str | None  # solo lo trae el sumario para DECRETOS
    tipo_norma: str | None      # "Resolución", "Decreto", etc.
    numero_norma: str | None    # "275/2026"
    codigo: str | None          # "RESFC-2026-275-APN-D#INCUCAI"
    url_detalle: str
    fecha_bo: str | None = None
    texto_completo: str | None = None
    motivo_match: list[str] = field(default_factory=list)

    @property
    def norma_id(self) -> str:
        if self.tipo_norma and self.numero_norma:
            return f"{self.tipo_norma} {self.numero_norma}"
        return self.codigo or self.id_bora


class BoraScraper:
    def __init__(self, config: dict, session: requests.Session | None = None):
        self.config = config["bora"]
        self.keywords = [normalizar(k) for k in config.get("keywords", [])]
        self.session = session or requests.Session()
        self.session.headers.update(HEADERS)

    def _url_sumario(self, fecha: date | None) -> str:
        base = f"{self.config['base_url']}/seccion/{self.config['seccion']}"
        if fecha:
            return f"{base}/{fecha.strftime('%Y%m%d')}"
        return base

    def _url_detalle(self, id_bora: str, fecha: date) -> str:
        return f"{self.config['base_url']}/detalleAviso/{self.config['seccion']}/{id_bora}/{fecha.strftime('%Y%m%d')}"

    def obtener_sumario(self, fecha: date | None = None) -> list[NormaCandidata]:
        """Descarga el sumario del día y devuelve TODOS los ítems de los rubros
        relevados (sin filtrar todavía por emisor/keywords)."""
        resp = self.session.get(self._url_sumario(fecha), timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        rubros_relevados = set(self.config["rubros_relevados"])
        rubros_titulo_directo = set(self.config["rubros_titulo_directo"])

        items: list[NormaCandidata] = []
        rubro_actual = None

        for el in soup.find_all(["h5", "a"]):
            if el.name == "h5" and "seccion-rubro" in (el.get("class") or []):
                rubro_actual = el.get_text(strip=True)
                continue

            if el.name != "a":
                continue
            href = el.get("href") or ""
            m = re.match(r"^/detalleAviso/\w+/(\d+)/(\d+)$", href)
            if not m or rubro_actual not in rubros_relevados:
                continue

            id_bora, fecha_url = m.groups()
            linea = el.find("div", class_="linea-aviso")
            if not linea:
                continue
            item_p = linea.find("p", class_="item")
            detalles = linea.find_all("p", class_="item-detalle")
            campo_item = item_p.get_text(strip=True) if item_p else ""
            detalle_1 = detalles[0].get_text(strip=True) if len(detalles) > 0 else ""
            detalle_2 = detalles[1].get_text(strip=True) if len(detalles) > 1 else ""

            tipo_norma, numero_norma = _partir_tipo_numero(detalle_1)
            codigo = detalle_2.split(" - ")[0].strip() if detalle_2 else None

            es_titulo_directo = rubro_actual in rubros_titulo_directo
            fecha_dt = datetime.strptime(fecha_url, "%Y%m%d").date()

            items.append(NormaCandidata(
                id_bora=id_bora,
                rubro=rubro_actual,
                organismo=None if es_titulo_directo else campo_item,
                titulo_sumario=campo_item if es_titulo_directo else None,
                tipo_norma=tipo_norma,
                numero_norma=numero_norma,
                codigo=codigo,
                url_detalle=self._url_detalle(id_bora, fecha_dt),
                fecha_bo=fecha_dt.isoformat(),
            ))
        return items

    def filtrar_candidatos(self, items: list[NormaCandidata]) -> list[NormaCandidata]:
        """Aplica el filtro de emisor (rubros con organismo) o de keywords
        (DECRETOS, donde el sumario solo trae el título)."""
        emisores = [normalizar(e) for e in self.config.get("emisores", [])]
        emisores_exactos = [normalizar(e) for e in self.config.get("emisores_exactos", [])]

        seleccionados = []
        for it in items:
            motivos = []
            if it.organismo is not None:
                organismo_norm = normalizar(it.organismo)
                if any(e in organismo_norm for e in emisores):
                    motivos.append("emisor")
                elif organismo_norm in emisores_exactos:
                    motivos.append("emisor")
                elif any(kw in organismo_norm for kw in self.keywords):
                    motivos.append("keyword_en_organismo")
            else:
                titulo_norm = normalizar(it.titulo_sumario or "")
                if any(kw in titulo_norm for kw in self.keywords):
                    motivos.append("keyword_en_titulo")

            if motivos:
                it.motivo_match = motivos
                seleccionados.append(it)
        return seleccionados

    def enriquecer_con_detalle(self, item: NormaCandidata) -> NormaCandidata:
        """Trae el texto completo de la norma desde su página de detalle."""
        resp = self.session.get(item.url_detalle, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        detalle = soup.find(id="detalleAviso")
        if detalle is None:
            item.texto_completo = ""
            return item

        cuerpo = detalle.find(id="cuerpoDetalleAviso")
        item.texto_completo = cuerpo.get_text("\n", strip=True) if cuerpo else ""

        edicion_h6 = soup.find(string=re.compile("Edición del"))
        if edicion_h6:
            contenedor = edicion_h6.find_parent().find_next_sibling("h6")
            if contenedor:
                fecha_parseada = _parsear_fecha_es(contenedor.get_text(strip=True))
                if fecha_parseada:
                    item.fecha_bo = fecha_parseada.isoformat()
        return item

    def relevar(self, fecha: date | None = None, limite: int | None = None) -> list[NormaCandidata]:
        """Corrida completa: sumario -> filtro -> detalle. Devuelve candidatos
        listos para analizar con la API."""
        items = self.obtener_sumario(fecha)
        candidatos = self.filtrar_candidatos(items)
        if limite:
            candidatos = candidatos[:limite]
        return [self.enriquecer_con_detalle(c) for c in candidatos]


def _partir_tipo_numero(texto: str) -> tuple[str | None, str | None]:
    """'Resolución 275/2026' -> ('Resolución', '275/2026')"""
    m = re.match(r"^(.+?)\s+(\d[\d./-]*)\s*$", texto.strip())
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return (texto.strip() or None, None)


def _parsear_fecha_es(texto: str) -> date | None:
    """'3 de Agosto de 2026' -> date(2026, 8, 3)"""
    m = re.search(r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})", texto.strip().lower())
    if not m:
        return None
    dia, mes_txt, anio = m.groups()
    mes = MESES_ES.get(mes_txt)
    if not mes:
        return None
    return date(int(anio), mes, int(dia))
