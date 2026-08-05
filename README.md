# Radar Regulatorio

Monitoreo automatizado de normativa y noticias con impacto en la industria de
petróleo y gas en Argentina (foco YPF). Ver `PROYECTO.md` para la especificación
completa y `MAPA-MAESTRO-AAPP.md` para el mapa de organismos y keywords del sector.

**Estado actual: Fase 1 (MVP), sesión 2.** BORA — Primera Sección + noticias
por Google News RSS, corrida automática con GitHub Actions y publicación en
GitHub Pages. La pestaña Legislaturas queda para las próximas sesiones (ver
`GUIA-CLAUDE-CODE.md`).

## Qué hace esta corrida

1. **Releva el BORA** del día (`src/fuentes/bora.py`): descarga el sumario de
   Primera Sección, filtra por emisor (Secretaría de Energía, Subsecretaría de
   Hidrocarburos, ENARGAS, ANPyN) y por keywords del sector en los decretos
   (que no traen emisor en el sumario), y trae el texto completo de cada norma
   candidata. Cuando el sumario trae un epígrafe oficial (los decretos lo
   traen en vez del organismo, ej. "COMBUSTIBLES"), queda guardado y se
   muestra junto al número de la norma.
2. **Releva noticias** (`src/fuentes/noticias.py`): Google News RSS con las
   queries configurables de `config.yaml` (`noticias.queries`), dentro de una
   ventana de días para no reprocesar la misma noticia en corridas sucesivas.
3. **Analiza cada ítem con la API de Claude** (`src/analisis.py`): genera la
   ficha ejecutiva (título, síntesis, tier, segmento, impacto YPF) según el
   esquema de `PROYECTO.md` sección 3, tanto para normas del BORA como para
   noticias. **Si no hay `ANTHROPIC_API_KEY` configurada, este paso se omite**
   y los ítems detectados se publican igual en el dashboard como "pendientes
   de análisis" — el pipeline nunca se cae por falta de la key. Para que sean
   útiles aun sin key, cada ficha pendiente de una norma del BORA trae un
   **extracto automático de la parte resolutiva** (Artículo 1° o, si no se
   encuentra, los primeros párrafos).
4. **Genera el sitio** (`src/sitio.py`): `docs/index.html` con las pestañas
   Hoy / Histórico / Descargas — separando normas del BORA y noticias en
   secciones propias —, guarda la corrida en `data/YYYY-MM-DD.json` (base
   histórica) y el informe del día en
   `docs/descargas/radar-regulatorio-YYYY-MM-DD.md`.

## Automatización y publicación

- **GitHub Actions** (`.github/workflows/diario.yml`): corre de lunes a
  viernes 08:00 ART (11:00 UTC) — o manualmente desde la pestaña *Actions* del
  repo, botón *Run workflow* —, ejecuta la corrida y commitea `data/` y
  `docs/` a `main` si hubo cambios. No falla si el secret
  `ANTHROPIC_API_KEY` todavía no está configurado en el repo (Settings →
  Secrets and variables → Actions): en ese caso publica igual las fichas
  "pendientes de análisis".
- **GitHub Pages**: servido desde `/docs` en `main` (Settings → Pages).

## Resiliencia por fuente

Cada fuente (BORA, noticias) corre en su propio `try/except` en `src/main.py`:
si una falla (red, DNS, WAF, cambio de formato del sitio), la corrida no se
cae — sigue con las demás fuentes y publica igual, marcando la fuente caída
con un aviso en el dashboard ("⚠ BORA: fuente caída hoy"), en el informe
Markdown y en `data/YYYY-MM-DD.json` (`fuentes_estado`). Las requests de
scraping (`src/fuentes/http.py`) llevan headers de navegador y reintentos con
backoff exponencial (`urllib3.Retry`, 3 intentos), pensado para fallas
transitorias de DNS/red del runner de Actions — el workflow además fuerza
resolvers DNS públicos (1.1.1.1, 8.8.8.8) antes de correr como mitigación
extra.

### Si el BORA sigue cayendo desde Actions (bloqueo por WAF, no DNS)

Las respuestas del BORA traen una cookie `TSxxxxxxxx=...`, firma de un WAF F5
BIG-IP ASM — este tipo de WAF suele aplicar bloqueo/rate-limit por
reputación de IP más agresivo contra rangos de datacenter/cloud (donde
corren los runners de Actions) que contra conexiones residenciales, lo que
explica que funcione desde una máquina normal y falle desde la corrida
automática aun con DNS y reintentos resueltos.

Mitigación disponible: `config.yaml` → `bora.proxy_url_template` acepta una
URL de relay propia (con `{url}` como placeholder) que el scraper usa como
segundo intento si el acceso directo falla — sin tocar código. Se probaron
proxies públicos gratuitos (allorigins, codetabs, corsproxy) y no son
confiables para esto (caídos o dados de baja al momento de evaluarlos), así
que la opción recomendada es desplegar un relay propio y gratis en
Cloudflare Workers: `scripts/proxy-bora-cloudflare-worker.js` trae el script
listo (allowlist al dominio del BORA, sin abrir un proxy genérico) y las
instrucciones de deploy en el encabezado del archivo — no requiere tarjeta
ni expone ningún secret (la URL del worker no es sensible, el Boletín
Oficial es información pública).

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
y las noticias, pero sin ficha ejecutiva (tier, síntesis, impacto YPF) —
quedan marcadas como "pendientes de análisis" tanto en el sitio como en el
informe Markdown, con el extracto automático (normas) o el titular (noticias)
como referencia. En cuanto se carga la key en `.env` (local) o como secret del
repo (GitHub Actions), las próximas corridas ya generan la ficha completa.

## Estructura

```
config.yaml           # emisores, keywords, queries de noticias, límite de ítems/corrida, modelo de la API
src/main.py            # orquestador de la corrida
src/fuentes/bora.py     # scraper del BORA
src/fuentes/noticias.py # Google News RSS
src/fuentes/http.py     # sesión HTTP compartida: headers de navegador + reintentos con backoff + fallback vía proxy
src/analisis.py         # prompt + llamada a la API de Claude (normas y noticias) + extracto sin API
src/sitio.py             # genera docs/index.html, informe MD e histórico
templates/index.html     # template Jinja2 (derivado de radar-regulatorio-mockup.html)
data/YYYY-MM-DD.json      # base histórica, un archivo por corrida (Git como base de datos)
docs/                     # sitio publicado (GitHub Pages, servido desde /docs en main)
scripts/proxy-bora-cloudflare-worker.js # relay opcional (Cloudflare Workers) si el BORA bloquea al runner
.github/workflows/diario.yml # corrida automática lunes a viernes 08:00 ART
```

## Presupuesto y límites

`config.yaml` define `analisis.limite_items_por_corrida: 50` como protección
de costo (ver `PROYECTO.md` sección 5).

## Próximas sesiones

- **Sesiones 3-4**: Legislaturas (HCDN, Senado, Neuquén, Río Negro, luego el
  resto de las provincias).
- Ver `PROYECTO.md` sección 7 para el resto del roadmap.
