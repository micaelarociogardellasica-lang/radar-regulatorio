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
integrada en Argentina (YPF). Analizás normas del Boletín Oficial para un \
dashboard ejecutivo de lectura matinal.

Te paso el texto completo de UNA norma del BORA. Devolvé SOLO un objeto JSON \
válido, sin backticks ni preámbulo ni texto fuera del JSON, con este esquema \
exacto:

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


def _base_ficha(candidato) -> dict:
    """Campos que salen del scraping, sin depender de la API."""
    return {
        "id": _slug(candidato.codigo or candidato.norma_id),
        "tipo": "bora",
        "norma_id": candidato.norma_id,
        "emisor": candidato.organismo or "Poder Ejecutivo Nacional",
        "fecha_bo": candidato.fecha_bo,
        "url_fuente": candidato.url_detalle,
        "codigo": candidato.codigo,
        "rubro": candidato.rubro,
    }


def analizar_candidato(candidato, client, modelo: str, max_tokens: int) -> dict | None:
    """Llama a la API para UNA norma. Devuelve la ficha completa, o None si
    la API decidió descartarla por no ser relevante."""
    base = _base_ficha(candidato)
    texto = candidato.texto_completo or ""

    mensaje = client.messages.create(
        model=modelo,
        max_tokens=max_tokens,
        system=PROMPT_SISTEMA,
        messages=[{
            "role": "user",
            "content": (
                f"Emisor: {base['emisor']}\n"
                f"Norma: {base['norma_id']}\n"
                f"Fecha BO: {base['fecha_bo']}\n\n"
                f"Texto completo:\n{texto}"
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
