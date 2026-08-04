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

    print("1/3 Relevando BORA Primera Sección...")
    scraper = BoraScraper(config)
    candidatos = scraper.relevar(fecha=fecha, limite=limite)
    print(f"    {len(candidatos)} norma(s) candidata(s) (emisor/keyword match).")

    print("2/3 Analizando con la API de Claude...")
    if not api_key_disponible():
        print("    ANTHROPIC_API_KEY no configurada: se omite el análisis.")
        print("    Las normas detectadas se publican como 'pendientes de análisis'.")
    fichas = analizar_lote(candidatos, config)
    analizadas = sum(1 for f in fichas if f.get("estado") == "analizado")
    descartadas = len(candidatos) - len(fichas)
    print(f"    {analizadas} ficha(s) generada(s) · {descartadas} descartada(s) por la API.")

    print("3/3 Generando el sitio...")
    index_path = generar_sitio(fecha, fichas, config)
    print(f"    Listo: {index_path}")


if __name__ == "__main__":
    main()
