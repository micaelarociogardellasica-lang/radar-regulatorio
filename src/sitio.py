"""Genera el dashboard estático (docs/index.html) y el informe diario en
Markdown a partir de las fichas de la corrida, más la base histórica en
data/YYYY-MM-DD.json.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

MESES_LARGO = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
DIAS_LARGO = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _fecha_corta(f: date) -> str:
    return f.strftime("%d.%m.%y")


def _fecha_larga(f: date) -> str:
    return f"{DIAS_LARGO[f.weekday()].upper()} {f.strftime('%d.%m.%Y')}"


def guardar_corrida(fichas: list[dict], fecha: date, config: dict) -> tuple[int, Path]:
    """Guarda data/YYYY-MM-DD.json y devuelve el número de relevamiento
    (cuántos días de corrida hay en total, incluido este)."""
    data_dir = Path(config["salida"]["data_dir"])
    data_dir.mkdir(parents=True, exist_ok=True)

    archivo = data_dir / f"{fecha.isoformat()}.json"
    archivo.write_text(json.dumps({
        "fecha": fecha.isoformat(),
        "generado_ts": datetime.now().isoformat(timespec="seconds"),
        "fichas": fichas,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    dias = sorted(p for p in data_dir.glob("*.json") if _es_fecha_valida(p.stem))
    numero_relevamiento = len(dias)
    return numero_relevamiento, archivo


def _es_fecha_valida(nombre: str) -> bool:
    try:
        date.fromisoformat(nombre)
        return True
    except ValueError:
        return False


def cargar_historico(config: dict) -> list[dict]:
    """Lee todos los data/YYYY-MM-DD.json y arma las filas para la tabla
    de histórico, más recientes primero."""
    data_dir = Path(config["salida"]["data_dir"])
    filas = []
    for archivo in sorted(data_dir.glob("*.json"), reverse=True):
        if not _es_fecha_valida(archivo.stem):
            continue
        corrida = json.loads(archivo.read_text(encoding="utf-8"))
        f = date.fromisoformat(corrida["fecha"])
        for ficha in corrida.get("fichas", []):
            filas.append({
                "fecha": corrida["fecha"],
                "fecha_corta": _fecha_corta(f),
                "tipo": ficha.get("tipo", "bora"),
                "norma_id": ficha.get("norma_id", ""),
                "titulo": ficha.get("titulo"),
                "emisor": ficha.get("emisor", ""),
                "tier": ficha.get("tier"),
            })
    return filas


def generar_informe_md(fichas: list[dict], pendientes: list[dict], fecha: date, numero: int) -> str:
    lineas = [
        "# RADAR REGULATORIO — Relevamiento diario",
        f"**{_fecha_larga(fecha).capitalize()} · N° {numero:03d}**",
        "",
    ]
    if not fichas and not pendientes:
        lineas.append("Sin novedades del sector en el BORA de hoy.")
        return "\n".join(lineas) + "\n"

    for tier in (1, 2, 3):
        del_tier = [f for f in fichas if f.get("tier") == tier]
        if not del_tier:
            continue
        lineas.append(f"## TIER {tier}")
        for f in del_tier:
            lineas.append(f"### {f['norma_id']} — {f['titulo']}")
            if f.get("epigrafe"):
                lineas.append(f"_{f['epigrafe']}_")
            lineas.append(f"Emisor: {f['emisor']} · Impacto YPF: {f['impacto_ypf']['grado']}")
            lineas.append(f["sintesis"])
            if f.get("impacto_ypf", {}).get("accion"):
                lineas.append(f"Acción: {f['impacto_ypf']['accion']}")
            lineas.append(f"Fuente: {f['url_fuente']}")
            lineas.append("")

    if pendientes:
        lineas.append("## PENDIENTES DE ANÁLISIS")
        lineas.append("(Detectadas por el scraper, sin ficha ejecutiva — falta configurar ANTHROPIC_API_KEY)")
        for p in pendientes:
            epigrafe = f" — {p['epigrafe']}" if p.get("epigrafe") else ""
            lineas.append(f"- {p['norma_id']}{epigrafe} — {p['emisor']} — {p['url_fuente']}")
            if p.get("extracto"):
                lineas.append(f"  > {p['extracto']}")
        lineas.append("")

    return "\n".join(lineas) + "\n"


def generar_sitio(fecha: date, fichas: list[dict], config: dict) -> Path:
    """Orquesta: guarda la corrida, genera el informe MD del día, arma el
    histórico y renderiza docs/index.html. Devuelve la ruta del index."""
    analizadas = [f for f in fichas if f.get("estado") == "analizado"]
    pendientes = [f for f in fichas if f.get("estado") == "pendiente"]
    con_error = [f for f in fichas if f.get("estado") == "error"]

    analizadas.sort(key=lambda f: f.get("tier", 9))

    analizadas_bora = [f for f in analizadas if f.get("tipo") != "noticia"]
    analizadas_noticias = [f for f in analizadas if f.get("tipo") == "noticia"]
    pendientes_bora = [f for f in pendientes if f.get("tipo") != "noticia"]
    pendientes_noticias = [f for f in pendientes if f.get("tipo") == "noticia"]

    numero, _ = guardar_corrida(fichas, fecha, config)

    docs_dir = Path(config["salida"]["docs_dir"])
    descargas_dir = docs_dir / "descargas"
    descargas_dir.mkdir(parents=True, exist_ok=True)

    informe_md = generar_informe_md(analizadas, pendientes, fecha, numero)
    nombre_informe = f"radar-regulatorio-{fecha.isoformat()}.md"
    (descargas_dir / nombre_informe).write_text(informe_md, encoding="utf-8")

    descargas = []
    for archivo in sorted(descargas_dir.glob("radar-regulatorio-*.md"), reverse=True):
        f_str = archivo.stem.replace("radar-regulatorio-", "")
        try:
            f_date = date.fromisoformat(f_str)
        except ValueError:
            continue
        descargas.append({
            "fecha_corta": _fecha_corta(f_date),
            "href": f"descargas/{archivo.name}",
            "resumen": f"Generado {f_date.isoformat()}",
        })

    contadores = {
        "t1": sum(1 for f in analizadas if f.get("tier") == 1),
        "t2": sum(1 for f in analizadas if f.get("tier") == 2),
        "t3": sum(1 for f in analizadas if f.get("tier") == 3),
        "pendientes": len(pendientes),
        "noticias": len(analizadas_noticias) + len(pendientes_noticias),
    }
    emisores_hoy = " · ".join(sorted({f["emisor"] for f in (analizadas + pendientes) if f.get("emisor")}))

    env = Environment(loader=FileSystemLoader(config["salida"]["templates_dir"]), autoescape=True)
    template = env.get_template("index.html")
    html = template.render(
        fecha_larga=_fecha_larga(fecha),
        fecha_corta=_fecha_corta(fecha),
        numero_relevamiento=numero,
        contadores=contadores,
        emisores_hoy=emisores_hoy,
        fichas=analizadas_bora,
        fichas_noticias=analizadas_noticias,
        pendientes=pendientes_bora,
        pendientes_noticias=pendientes_noticias,
        informe_hoy_href=f"descargas/{nombre_informe}" if (analizadas or pendientes) else None,
        historico=cargar_historico(config),
        descargas=descargas,
        generado_ts=datetime.now().strftime("%d.%m.%Y %H:%M"),
        atlas_url=config.get("atlas_url") or None,
    )

    index_path = docs_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")

    if con_error:
        print(f"[AVISO] {len(con_error)} ítem(s) fallaron durante el análisis con la API:")
        for f in con_error:
            print(f"  - {f['norma_id']}: {f.get('error')}")

    return index_path
