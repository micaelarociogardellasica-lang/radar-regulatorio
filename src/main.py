"""Orquestador de la corrida diaria del Radar Regulatorio — Fase 1 (MVP).

Uso:
    python src/main.py                  # corrida de hoy
    python src/main.py --fecha 2026-08-03  # corrida contra una edición pasada del BORA
"""
from __future__ import annotations

import argparse
from datetime import date

import yaml
from dotenv import load_dotenv

from analisis import analizar_lote, api_key_disponible
from fuentes.bora import BoraScraper
from fuentes.noticias import NoticiasScraper
from sitio import generar_sitio


def cargar_config(ruta: str = "config.yaml") -> dict:
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="Corrida diaria del Radar Regulatorio")
    parser.add_argument("--fecha", type=str, default=None, help="YYYY-MM-DD (default: hoy)")
    parser.add_argument("--config", type=str, default="config.yaml")
    args = parser.parse_args()

    load_dotenv()
    config = cargar_config(args.config)
    fecha = date.fromisoformat(args.fecha) if args.fecha else date.today()
    limite = config["analisis"]["limite_items_por_corrida"]

    print(f"== Radar Regulatorio — corrida {fecha.isoformat()} ==")

    print("1/4 Relevando BORA Primera Sección...")
    fuentes_estado = {"bora": "ok", "noticias": "ok"}
    try:
        candidatos_bora = BoraScraper(config).relevar(fecha=fecha, limite=limite)
        print(f"    {len(candidatos_bora)} norma(s) candidata(s) (emisor/keyword match).")
    except Exception as exc:  # el BORA puede fallar (red, DNS, cambio de formato) sin tumbar la corrida
        candidatos_bora = []
        fuentes_estado["bora"] = "error"
        fuentes_estado["bora_error"] = str(exc)
        print(f"    [AVISO] no se pudo relevar el BORA — se publica como 'fuente caída hoy': {exc}")

    print("2/4 Relevando noticias (Google News RSS)...")
    try:
        candidatos_noticias = NoticiasScraper(config).relevar(fecha=fecha)
        print(f"    {len(candidatos_noticias)} noticia(s) candidata(s).")
    except Exception as exc:  # el RSS de Google News puede fallar sin tumbar la corrida
        candidatos_noticias = []
        fuentes_estado["noticias"] = "error"
        fuentes_estado["noticias_error"] = str(exc)
        print(f"    [AVISO] no se pudieron relevar noticias: {exc}")

    candidatos = (candidatos_bora + candidatos_noticias)[:limite]

    print("3/4 Analizando con la API de Claude...")
    if not api_key_disponible():
        print("    ANTHROPIC_API_KEY no configurada: se omite el análisis.")
        print("    Los ítems detectados se publican como 'pendientes de análisis'.")
    fichas = analizar_lote(candidatos, config)
    analizadas = sum(1 for f in fichas if f.get("estado") == "analizado")
    descartadas = len(candidatos) - len(fichas)
    print(f"    {analizadas} ficha(s) generada(s) · {descartadas} descartada(s) por la API.")

    print("4/4 Generando el sitio...")
    index_path = generar_sitio(fecha, fichas, config, fuentes_estado)
    print(f"    Listo: {index_path}")


if __name__ == "__main__":
    main()
