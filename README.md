# Radar Regulatorio

Monitoreo automatizado de normativa y noticias con impacto en la industria de
petróleo y gas en Argentina (foco YPF). Ver `PROYECTO.md` para la especificación
completa y `MAPA-MAESTRO-AAPP.md` para el mapa de organismos y keywords del sector.

**Estado actual: Fase 1 (MVP), sesión 1.** Cubre solo BORA — Primera Sección.
Noticias (Google News RSS), la pestaña Legislaturas y la corrida automática por
GitHub Actions quedan para las próximas sesiones (ver `GUIA-CLAUDE-CODE.md`).

## Qué hace esta corrida

1. **Releva el BORA** del día (`src/fuentes/bora.py`): descarga el sumario de
   Primera Sección, filtra por emisor (Secretaría de Energía, Subsecretaría de
   Hidrocarburos, ENARGAS, ANPyN) y por keywords del sector en los decretos
   (que no traen emisor en el sumario), y trae el texto completo de cada norma
   candidata.
2. **Analiza cada norma con la API de Claude** (`src/analisis.py`): genera la
   ficha ejecutiva (título, síntesis, tier, segmento, impacto YPF) según el
   esquema de `PROYECTO.md` sección 3. **Si no hay `ANTHROPIC_API_KEY`
   configurada, este paso se omite** y las normas detectadas se publican igual
   en el dashboard como "pendientes de análisis" — el pipeline nunca se cae por
   falta de la key.
3. **Genera el sitio** (`src/sitio.py`): `docs/index.html` con las pestañas
   Hoy / Histórico / Descargas, guarda la corrida en `data/YYYY-MM-DD.json`
   (base histórica) y el informe del día en
   `docs/descargas/radar-regulatorio-YYYY-MM-DD.md`.

## Instalación

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # completar ANTHROPIC_API_KEY cuando la tengas
```

## Uso

```bash
# Corrida de hoy
python src/main.py

# Corrida contra una edición pasada del BORA (útil para probar)
python src/main.py --fecha 2026-08-03
```

Al terminar, abrí `docs/index.html` en el navegador para ver el dashboard.

Sin `ANTHROPIC_API_KEY`, la corrida igual detecta y lista las normas del BORA
que matchean emisor/keywords, pero sin ficha ejecutiva (tier, síntesis,
impacto YPF) — quedan marcadas como "pendientes de análisis" tanto en el sitio
como en el informe Markdown. En cuanto se carga la key en `.env`, las próximas
corridas ya generan la ficha completa.

## Estructura

```
config.yaml       # emisores, keywords, límite de ítems/corrida, modelo de la API
src/main.py        # orquestador de la corrida
src/fuentes/bora.py # scraper del BORA
src/analisis.py     # prompt + llamada a la API de Claude
src/sitio.py         # genera docs/index.html, informe MD e histórico
templates/index.html # template Jinja2 (derivado de radar-regulatorio-mockup.html)
data/YYYY-MM-DD.json  # base histórica, un archivo por corrida (Git como base de datos)
docs/                 # sitio publicado (pensado para GitHub Pages, fase 2)
```

## Presupuesto y límites

`config.yaml` define `analisis.limite_items_por_corrida: 50` como protección
de costo (ver `PROYECTO.md` sección 5).

## Próximas sesiones

- **Sesión 2**: GitHub Actions (corrida diaria o botón manual), publicación en
  GitHub Pages, noticias por Google News RSS en su propia sección del dashboard.
- **Sesiones 3-4**: Legislaturas (HCDN, Senado, Neuquén, Río Negro, luego el
  resto de las provincias).
- Ver `PROYECTO.md` sección 7 para el resto del roadmap.
