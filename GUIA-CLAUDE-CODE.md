# GUÍA — Tu primera vez con Claude Code

Cero experiencia requerida. Seguí en orden.

## 1. Preparación (una sola vez, ~20 min)

1. **Instalar Claude Code**: la forma más simple es la app de escritorio de Claude
   (o desde la terminal si preferís). Las instrucciones actualizadas están en
   https://docs.claude.com — buscá "Claude Code installation". Si te trabás en
   este paso, preguntame en el chat y te guío con tu sistema operativo.
2. **API key**: crear cuenta en https://console.anthropic.com, cargar un mínimo de
   crédito (USD 5 sobra para meses de este proyecto) y generar una key.
   Guardala en un lugar seguro — se muestra una sola vez.
3. **Cuenta de GitHub**: si no tenés, crearla en github.com (gratis). La vas a
   necesitar para la automatización diaria y el hosting.
4. **Carpeta del proyecto**: crear una carpeta `radar-regulatorio` y poner adentro
   `PROYECTO.md` y `radar-regulatorio-mockup.html`.

## 2. Primera sesión (el MVP)

Abrí Claude Code parada en la carpeta del proyecto y pegá esto como primer mensaje:

> Leé PROYECTO.md completo. Es la especificación de un sistema de monitoreo
> regulatorio. Quiero construir la Fase 1 (MVP) exactamente como está descripta.
> El archivo radar-regulatorio-mockup.html es la referencia visual del dashboard.
> Antes de escribir código, contame tu plan en 5-6 pasos y esperá mi ok.

Pedirle el plan primero es clave: te deja ver qué va a hacer y corregir el rumbo
antes de que escriba nada.

Después del plan, el flujo típico es:
- Le decís "dale" y construye por partes.
- Cuando necesite la API key, te va a decir dónde ponerla (un archivo `.env` local).
  Nunca la pegues dentro del código.
- Pedile siempre: "corré una prueba con el BORA de hoy y mostrame el resultado".
  Ver output real > confiar en que funciona.

## 3. Frases útiles durante la sesión

- "Explicame qué hace este archivo en criollo antes de seguir."
- "Probá la corrida completa de punta a punta y mostrame el HTML generado."
- "Eso no es lo que pedí: releé la sección X de PROYECTO.md."
- "Commiteá lo que tenemos hasta acá con un mensaje descriptivo."
- "¿Qué falta para dar por cerrada la Fase 1 según el criterio de éxito?"

## 4. Qué esperar (expectativas realistas)

- La Fase 1 puede salir en una sesión larga o dos cortas. Los scrapers a veces
  necesitan iteración (los sitios oficiales tienen sus mañas) — es normal.
- Todo error se pega en el chat de Claude Code tal cual aparece: lo diagnostica solo.
- No necesitás entender el código, pero pedir explicaciones te sirve doble:
  controlás el proyecto y aprendés. Con tu perfil, en dos sesiones vas a estar
  leyendo los archivos de configuración sin ayuda.

## 5. Hoja de ruta de sesiones (el paso a paso completo)

Con todo el alcance ya definido, este es el orden de sesiones recomendado.
Regla de oro: **una fase por sesión, y no se avanza a la siguiente hasta que la
anterior corre sola sin errores.** El scope creep es el enemigo N°1 de este tipo
de proyectos.

**Sesión 1 — MVP (Fase 1)**
Mensaje inicial: el de la sección 2 de esta guía.
Resultado esperado: corrida manual que scrapea el BORA de hoy, analiza con la API
y genera el dashboard con pestañas Hoy/Histórico/Descargas.
Cierre de sesión: "commiteá todo y armá el README con cómo correr el sistema".

**Sesión 2 — Automatización + publicación**
> Leé PROYECTO.md. El MVP ya funciona. Ahora: (1) configurá GitHub Actions para
> la corrida diaria de lunes a viernes 08:00 ART, (2) publicá el sitio en GitHub
> Pages, (3) agregá las noticias por RSS según la spec. Plan primero.
Tarea manual tuya: cargar el secret ANTHROPIC_API_KEY en GitHub y activar Pages
(Claude Code te dice exactamente dónde clickear).
Resultado: el dashboard tiene URL y se actualiza solo. **Acá ya tenés producto usable.**

**Sesiones 3-4 — Legislaturas (Fase 2)**
> Leé PROYECTO.md, vamos por la Fase 2. Empezá solo con HCDN y Senado (nacional).
> Plan primero.
Y en la sesión siguiente: Neuquén y Río Negro. Después, de a una o dos provincias
por sesión. No intentes las seis de una: cada legislatura tiene su sistema y sus mañas.

**Sesión 5 — Inteligencia avanzada (Fase 2.5 a y b)**
Ventanas de incidencia + designaciones. Misma fuente que ya scrapeás (BORA),
así que es más liviana de lo que parece.

**Sesión 6 — Alertas (Fase 3)**
Notificación por mail o Telegram cuando aparece un tier 1. A esta altura el
sistema trabaja para vos aunque no lo abras.

**Sesión 7+ — Pestaña Proyectos (Fase 3.5)**
Antes de la sesión, armá vos la lista curada de proyectos con lo que sabés
(VMOS, Argentina LNG, ductos, arenas, hub norte) en un archivo `proyectos.yaml`
simple — Claude Code te da el formato en la sesión y vos lo completás.

**Más adelante — Atlas (repo aparte)**
Recién cuando el Radar esté estable y corriendo hace semanas. Sesión nueva,
carpeta nueva, y una spec propia (pedímela en el chat cuando llegue el momento).

**Si una sesión sale mal**: no pasa nada. Git guarda todo — podés pedirle
"volvé al último commit que funcionaba" y arrancar de nuevo. Nada se rompe
de forma permanente.

## 6. Después del MVP

- Configurar GitHub Actions (Claude Code lo hace; vos solo cargás el secret
  `ANTHROPIC_API_KEY` en la web de GitHub → Settings → Secrets).
- Activar GitHub Pages para tener la URL del dashboard.
- Recién ahí encarar la Fase 2 (Legislaturas), en una sesión nueva, con el mismo
  método: "leé PROYECTO.md, vamos por la Fase 2, plan primero".

## 7. Seguridad y costos, en corto

- La API key es como una tarjeta: no se comparte, no se sube a GitHub. El `.env`
  queda fuera del repo (Claude Code lo configura así por defecto con `.gitignore`).
- Podés ponerle un límite de gasto mensual a la cuenta en la consola de Anthropic.
  Poné USD 5-10 y dormí tranquila.
- Si algo se rompe un día (el BORA cambió el formato, por ejemplo), no pasa nada:
  el sitio queda con el último relevamiento bueno y lo arreglás en la siguiente sesión.
