# RADAR REGULATORIO — Especificación del proyecto

> Brief para construir con Claude Code. Pegar este archivo en la carpeta del proyecto
> junto con `radar-regulatorio-mockup.html` (referencia visual de diseño).

## 1. Qué es

Sistema automatizado de monitoreo regulatorio y legislativo para la industria de
petróleo y gas en Argentina, con foco en YPF. Corre solo todos los días hábiles,
releva fuentes públicas, analiza cada norma/proyecto con la API de Claude, y publica
un dashboard web estático con fichas ejecutivas descargables.

Usuario: analista de asuntos públicos. Uso: lectura matinal (mobile y desktop),
reenvío de informes a su equipo.

## 2. Fuentes de datos

### Fase 1 (MVP)
- **BORA — Primera Sección** (boletinoficial.gob.ar): normas del día. Filtrar por
  emisor (Secretaría de Energía, Subsecretaría de Hidrocarburos, ENARGAS, ANPyN,
  Ministerio de Economía, PEN) y keywords (hidrocarburos, gas, GNL, RIGI, regalías,
  combustibles, refinación, cabotaje, ductos, biocombustibles, GLP, Vaca Muerta).
- **Noticias**: Google News RSS con queries configurables ("YPF", "Vaca Muerta",
  "Secretaría de Energía", "marina mercante cabotaje").

### Fase 2 (Legislaturas)
- **HCDN**: portal de expedientes + datos abiertos (datos.hcdn.gob.ar). Extraer:
  número de expediente, carátula, autor/bloque, fecha de ingreso, giros a comisiones
  con fechas, movimientos, estado.
- **Senado**: sistema de expedientes (senado.gob.ar).
- **Legislaturas provinciales** (en este orden de prioridad): Neuquén, Río Negro,
  Buenos Aires, Córdoba, Mendoza, Entre Ríos. Cada una tiene su propio sistema:
  implementar como scrapers independientes (un módulo por provincia) para que la
  falla de uno no tumbe el resto. Diseñar la interfaz común primero.

### Cobertura temática (todas las fases)
Cubrir los tres segmentos, no solo upstream:
- **Upstream**: exploración, producción, regalías, RIGI, arenas de fractura, servidumbres.
- **Midstream**: transporte por ductos, GNL, terminales, cabotaje y logística naviera,
  practicaje, tarifas de transporte de gas.
- **Downstream**: refinación, biocombustibles (cortes, precios), comercialización,
  impuestos a los combustibles (nacionales y provinciales, ej. IIBB), GLP, estaciones.

## 3. Análisis con la API de Claude

Cada ítem relevado se envía a la API (modelo: claude-sonnet-4-6) con un prompt que
devuelve JSON estricto. Esquema de la ficha:

```json
{
  "id": "res-se-167-2026",
  "tipo": "bora | noticia | expediente",
  "norma_id": "RES SE 167/2026",
  "titulo": "string (una línea, lenguaje ejecutivo)",
  "emisor": "string",
  "fecha_bo": "YYYY-MM-DD",
  "url_fuente": "string",
  "segmento": "upstream | midstream | downstream | transversal",
  "tier": 1 | 2 | 3,
  "sintesis": "2-3 líneas",
  "vigencia_plazo": "string",
  "beneficiarios": "string",
  "afectados": "string",
  "impacto_ypf": {
    "grado": "directo | indirecto | contexto",
    "area": "ej: Comercial Gas, Logística, Trading, AAPP",
    "accion": "qué verificar/hacer concretamente"
  }
}
```

Criterio de tiers:
- **Tier 1**: efecto directo e inmediato sobre operaciones, ingresos o obligaciones
  de la compañía. Va arriba de todo y dispara alerta (fase 3).
- **Tier 2**: efecto indirecto o mediato; seguimiento activo.
- **Tier 3**: contexto sectorial, benchmarking de competidores, patrón regulatorio.

Esquema adicional para expedientes legislativos:

```json
{
  "expediente": "3412-D-2026",
  "camara": "diputados | senado | provincia:<nombre>",
  "etapa": "borrador | ingreso | comisiones | dictamen | media_sancion | sancion | promulgacion",
  "historial": [{"fecha": "YYYY-MM-DD", "evento": "string"}],
  "comisiones": ["string"],
  "actores_clave": "string",
  "lectura_politica": "viabilidad y contexto en 2-3 líneas"
}
```

Reglas del prompt de análisis:
- Responder SOLO JSON válido, sin backticks ni preámbulo.
- Si el ítem no es relevante para el sector, devolver `{"descartar": true}`.
- No inventar datos: si un campo no surge de la fuente, usar null.
- La síntesis parafrasea, nunca copia texto de la fuente.

## 4. Salida

- **Dashboard web estático** regenerado en cada corrida. Referencia visual:
  `radar-regulatorio-mockup.html` (respetar paleta azul vibrante, tipografías
  Archivo + IBM Plex Sans/Mono, fichas con espina de color por tier, timeline
  legislativa). Pestañas: Hoy · Legislaturas · Histórico · Descargas.
- **Informe diario descargable**: Markdown siempre; Word/PDF en fase 2
  (generación server-side en la corrida, no en el navegador).
- **Export Excel (.xlsx)** — fase 2: (a) informe del día como planilla y
  (b) base histórica completa con todas las fichas como filas (fecha, norma_id,
  emisor, tier, segmento, síntesis, vigencia, beneficiarios, afectados,
  impacto_ypf.area, impacto_ypf.accion, url_fuente), pensada para tablas
  dinámicas y filtros. Disponible en la pestaña Descargas, regenerada en cada
  corrida. Usar openpyxl con encabezados congelados y autofiltro activado.
- **Base histórica**: un JSON por día en `data/YYYY-MM-DD.json` + un índice
  agregado para el buscador del histórico. Git como base de datos (versionado gratis).

## 5. Infraestructura

- **Lenguaje**: Python 3.11+ (requests, beautifulsoup4, feedparser, anthropic, jinja2).
- **Automatización**: GitHub Actions, cron lunes a viernes 08:00 ART (11:00 UTC).
- **Hosting**: GitHub Pages (rama `gh-pages` o carpeta `/docs`).
- **Secretos**: `ANTHROPIC_API_KEY` como secret del repo. Nunca en el código.
- **Presupuesto API**: volumen esperado 5-30 ítems/día → costo estimado en centavos
  de USD por día. Poner un límite de 50 ítems por corrida como protección.

## 6. Estructura de archivos propuesta

```
radar-regulatorio/
├── PROYECTO.md                  # este archivo
├── radar-regulatorio-mockup.html
├── requirements.txt
├── config.yaml                  # keywords, emisores, provincias, queries de noticias
├── src/
│   ├── main.py                  # orquestador de la corrida diaria
│   ├── fuentes/
│   │   ├── bora.py
│   │   ├── noticias.py
│   │   ├── hcdn.py              # fase 2
│   │   ├── senado.py            # fase 2
│   │   └── provincias/          # fase 2: un módulo por provincia
│   ├── analisis.py              # llamadas a la API de Claude + validación del JSON
│   └── sitio.py                 # genera el HTML desde templates Jinja2
├── templates/                   # derivados del mockup
├── data/                        # JSON diarios (base histórica)
├── docs/                        # sitio publicado (GitHub Pages)
└── .github/workflows/diario.yml
```

## 7. Plan de fases

1. **Fase 1 — MVP (primera sesión de Claude Code)**: scraper BORA + análisis API +
   dashboard con pestañas Hoy/Histórico/Descargas (solo Markdown) + Action diaria.
   Criterio de éxito: una corrida manual produce el sitio con las normas reales del día.
2. **Fase 2 — Legislaturas**: HCDN + Senado + Neuquén y Río Negro primero (las de
   mayor impacto operativo), luego BA, Córdoba, Mendoza, Entre Ríos. Timeline por
   expediente. Export Word/PDF.
2.5. **Fase 2.5 — Inteligencia regulatoria avanzada** (prioridad: a y b):
   a. **Ventanas de incidencia**: consultas públicas abiertas, audiencias públicas
      convocadas (ENARGAS/SE), plazos de comentarios a proyectos normativos.
      Sección propia con fecha de cierre y countdown.
   b. **Designaciones y renuncias**: decretos/resoluciones de nombramientos en
      SE, SSH, ENARGAS, ANPyN, entes descentralizados. Misma fuente BORA,
      sección "Mapa de interlocutores".
   c. **Deuda reglamentaria**: leyes sin decreto reglamentario y decretos sin
      resolución de aplicación, con días transcurridos.
   d. **Enforcement**: multas y sanciones de ENARGAS/SE a operadoras (serie
      temporal por tema).
   e. **Radar de competidores**: adhesiones RIGI, permisos de exportación,
      concesiones otorgadas a otras empresas.
   f. **Tendencias**: conteo de normas por emisor/tema/segmento, mes a mes.
3. **Fase 3 — Alertas y extensión**: notificación (mail o Telegram) ante tier 1,
   dossiers temáticos, tracking de otras empresas (campo "empresa" en la ficha),
   resto de las provincias.
4. **Fase 3.5 — Pestaña "Proyectos"**: seguimiento de proyectos de infraestructura
   en curso, con card por proyecto: timeline de hitos (anuncio → RIGI/FID →
   construcción → puesta en marcha), historial de normas vinculadas (cada ficha
   del Radar puede referenciar un `proyecto_id`), y estado actual.
   Lista inicial (curada por la usuaria, el sistema la mantiene viva):
   - VMOS / terminal Punta Colorada
   - Argentina LNG y proyectos FLNG (Golfo San Matías)
   - Ampliaciones de ductos: Gasoducto Perito Moreno, Reversión Norte,
     Duplicar (Oldelval)
   - Ruta/tren de las arenas (logística de insumos)
   - Proyectos del hub norte con adhesión RIGI en trámite
   - Otros que la usuaria agregue desde config
5. **Proyecto separado — "Atlas" (repo aparte, post-estabilización del Radar)**:
   mapa de players de la industria. Modelo de datos por entidades:
   empresa → bloques/áreas → % de participación → operador → cuenca; refinerías,
   ductos y terminales. Actualización por eventos (M&A, cesiones, farm-outs)
   detectados por el Radar en boletines nacionales y provinciales.
   Fuente georreferenciada: datos abiertos de la Secretaría de Energía (áreas de
   concesión y producción por área). Visualización: mapa interactivo (Leaflet)
   + fichas por empresa y por bloque. Uso: consulta y visión de stakeholders.

## 8. Decisiones ya tomadas (no re-debatir)

- Diseño congelado según mockup v0.1 (azul vibrante estilo YPF).
- Sin "acción sugerida" como campo separado: va dentro de impacto_ypf.accion.
- Sitio público en GitHub Pages es aceptable (toda la información es pública);
  evaluar acceso privado solo si el uso se institucionaliza.
- El logo oficial NO va en el repo público; el HTML tiene un slot `logo-ypf.png`
  que se resuelve localmente.
