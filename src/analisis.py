"""Análisis de normas candidatas con la API de Claude.

Fase 1: cada NormaCandidata del BORA se manda a la API con un prompt que
debe devolver el JSON estricto de la ficha (ver PROYECTO.md sección 3).

Si no hay ANTHROPIC_API_KEY configurada, el módulo no falla: devuelve las
normas detectadas con estado "pendiente" para que el resto del pipeline
(guardado + sitio) funcione igual, mostrando lo que el scraper encontró
aunque todavía no haya ficha ejecutiva generada por la API.
"""
from __future__ import annotations

import json
import os
import re
import unicodedata

PROMPT_SISTEMA = """Sos un analista de asuntos públicos y regulatorios de una petrolera \
integrada en Argentina (YPF). Analizás normas del Boletín Oficial y noticias \
periodísticas del sector para un dashboard ejecutivo de lectura matinal.

Te paso el texto de UN ítem: puede ser el texto completo de una norma del BORA, \
o el título y resumen de una noticia (Google News). Si es una noticia, analizala \
igual con la información disponible y dejá explícito en la síntesis que es \
cobertura de prensa, no texto oficial. Devolvé SOLO un objeto JSON válido, sin \
backticks ni preámbulo ni texto fuera del JSON, con este esquema exacto:

{
  "titulo": "string (una línea, lenguaje ejecutivo, parafraseado)",
  "segmento": "upstream | midstream | downstream | transversal",
  "tier": 1 | 2 | 3,
  "sintesis": "string (2-3 líneas, parafrasea, nunca copia texto de la fuente)",
  "vigencia_plazo": "string o null",
  "beneficiarios": "string o null",
  "afectados": "string o null",
  "impacto_ypf": {
    "grado": "directo | indirecto | contexto",
    "area": "string, ej: Comercial Gas, Logística, Trading, AAPP",
    "accion": "string: qué verificar/hacer concretamente"
  }
}

Criterio de tiers:
- Tier 1: efecto directo e inmediato sobre operaciones, ingresos u obligaciones \
de la compañía.
- Tier 2: efecto indirecto o mediato; seguimiento activo.
- Tier 3: contexto sectorial, benchmarking de competidores, patrón regulatorio.

Reglas estrictas:
- Si la norma NO es relevante para la industria de petróleo y gas (upstream, \
midstream o downstream), devolvé exactamente: {"descartar": true}
- No inventes datos: si un campo no surge del texto, usá null.
- La síntesis parafrasea, nunca copia literalmente el texto de la fuente.
- Respondé SOLO el JSON, nada más."""


def api_key_disponible() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _slug(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", sin_acentos.lower()).strip("-")


MAX_CHARS_EXTRACTO = 700

# "DECRETA:" / "RESUELVE:" / "DISPONE:" cierran el Visto/Considerando y abren
# la parte resolutiva — es un ancla mucho más confiable que buscar "Artículo
# 1°" directo, que también aparece citado dentro de los considerandos.
_ANCLA_RESOLUTIVO = re.compile(r"\b(DECRETA|RESUELVE|DISPONE)\s*:", re.IGNORECASE)
_ARTICULO_1 = re.compile(r"art[íi]culo\s*1(?!\d)\s*[°ºo]\.?[-–—]", re.IGNORECASE)
_ARTICULO_2 = re.compile(r"art[íi]culo\s*2(?!\d)\s*[°ºo]?\b", re.IGNORECASE)


def _recortar(fragmento: str, max_chars: int) -> str | None:
    fragmento = fragmento.strip()
    if not fragmento:
        return None
    if len(fragmento) > max_chars:
        return fragmento[:max_chars].strip() + "…"
    return fragmento


def _extraer_resolutivo(texto: str, max_chars: int = MAX_CHARS_EXTRACTO) -> str | None:
    """Fallback sin API: busca la parte resolutiva (Artículo 1°) de una norma
    del BORA. Si no la encuentra, devuelve los primeros párrafos del texto."""
    if not texto:
        return None

    inicio = None
    anclas = list(_ANCLA_RESOLUTIVO.finditer(texto))
    if anclas:
        inicio = anclas[-1].end()
    else:
        match = _ARTICULO_1.search(texto)
        if match:
            inicio = match.start()

    if inicio is not None:
        fragmento = texto[inicio:]
        siguiente = _ARTICULO_2.search(fragmento)
        if siguiente:
            fragmento = fragmento[:siguiente.start()]
        recortado = _recortar(fragmento, max_chars)
        if recortado:
            return recortado

    parrafos = [p.strip() for p in texto.split("\n") if p.strip()]
    return _recortar(" ".join(parrafos[:3]), max_chars)


def _extracto_pendiente(candidato) -> str | None:
    """Extracto automático mostrable sin depender de la API (item 3 de la
    sesión 2): parte resolutiva (Artículo 1° o primeros párrafos) para
    normas del BORA. Las noticias no tienen "parte resolutiva" — su único
    contenido pre-análisis es el titular, que ya se muestra como epígrafe."""
    if getattr(candidato, "tipo", "bora") == "noticia":
        return None
    return _extraer_resolutivo(getattr(candidato, "texto_completo", None))


def _base_ficha(candidato) -> dict:
    """Campos que salen del scraping, sin depender de la API."""
    return {
        "id": _slug(candidato.codigo or candidato.norma_id),
        "tipo": getattr(candidato, "tipo", "bora"),
        "norma_id": candidato.norma_id,
        "emisor": candidato.organismo or "Poder Ejecutivo Nacional",
        "epigrafe": getattr(candidato, "titulo_sumario", None),
        "fecha_bo": candidato.fecha_bo,
        "url_fuente": candidato.url_detalle,
        "codigo": candidato.codigo,
        "rubro": candidato.rubro,
        "extracto": _extracto_pendiente(candidato),
    }


def analizar_candidato(candidato, client, modelo: str, max_tokens: int) -> dict | None:
    """Llama a la API para UNA norma. Devuelve la ficha completa, o None si
    la API decidió descartarla por no ser relevante."""
    base = _base_ficha(candidato)
    texto = candidato.texto_completo or ""
    es_noticia = base["tipo"] == "noticia"

    mensaje = client.messages.create(
        model=modelo,
        max_tokens=max_tokens,
        system=PROMPT_SISTEMA,
        messages=[{
            "role": "user",
            "content": (
                f"Tipo de fuente: {'Noticia (Google News)' if es_noticia else 'Norma del BORA'}\n"
                f"{'Fuente' if es_noticia else 'Emisor'}: {base['emisor']}\n"
                f"Identificador: {base['norma_id']}\n"
                f"Fecha: {base['fecha_bo']}\n\n"
                f"{'Título y resumen' if es_noticia else 'Texto completo'}:\n{texto}"
            ),
        }],
    )
    bruto = mensaje.content[0].text.strip()
    datos = json.loads(bruto)

    if datos.get("descartar"):
        return None

    base.update(datos)
    base["estado"] = "analizado"
    return base


def analizar_lote(candidatos: list, config: dict) -> list[dict]:
    """Analiza todos los candidatos. Si no hay API key, devuelve los ítems
    como "pendiente" (detectados, sin ficha ejecutiva todavía)."""
    if not api_key_disponible():
        return [
            {**_base_ficha(c), "estado": "pendiente"}
            for c in candidatos
        ]

    import anthropic
    client = anthropic.Anthropic()
    cfg_analisis = config["analisis"]

    fichas = []
    for c in candidatos:
        try:
            ficha = analizar_candidato(c, client, cfg_analisis["modelo"], cfg_analisis["max_tokens"])
        except Exception as exc:  # error de red, JSON inválido, etc.
            ficha = {**_base_ficha(c), "estado": "error", "error": str(exc)}
            fichas.append(ficha)
            continue
        if ficha is not None:
            fichas.append(ficha)
        # si ficha es None, la API la descartó por no relevante: no se agrega
    return fichas
