/**
 * Relay para el BORA — Cloudflare Worker (plan gratuito).
 *
 * Por qué existe: el WAF del Boletín Oficial (F5 BIG-IP ASM, se lo ve por la
 * cookie "TSxxxxxxxx=..." en las respuestas) aplica bloqueo/rate-limit por
 * reputación de IP mucho más agresivo contra rangos de datacenter/cloud
 * (AWS/Azure/GCP — donde corren los runners de GitHub Actions) que contra
 * conexiones residenciales. Este worker sale a internet desde la red de
 * Cloudflare, así que actúa como una vía de acceso alternativa cuando el
 * pedido directo desde Actions queda bloqueado. Ver src/fuentes/http.py
 * para el detalle del fallback (se usa solo si el acceso directo falla).
 *
 * Deploy (gratis, ~5 minutos, sin tarjeta):
 *   1. https://dash.cloudflare.com → Workers & Pages → Create → Create Worker.
 *   2. Pegar este archivo entero en el editor, reemplazando el template.
 *   3. Deploy. Cloudflare te da una URL tipo https://<nombre>.<tu-cuenta>.workers.dev
 *   4. En config.yaml, campo bora.proxy_url_template, poner:
 *        "https://<tu-worker>.workers.dev/?url={url}"
 *      (el "{url}" queda literal — Python lo reemplaza en runtime).
 *
 * No hace falta ninguna API key ni secret: la URL del worker no es sensible
 * (el Boletín Oficial es información pública) y solo reenvía pedidos GET
 * hacia boletinoficial.gob.ar — el allowlist de abajo evita que quede
 * expuesto como proxy abierto para cualquier otro sitio.
 */

const DOMINIOS_PERMITIDOS = ["www.boletinoficial.gob.ar", "boletinoficial.gob.ar"];

export default {
  async fetch(request) {
    const params = new URL(request.url).searchParams;
    const destino = params.get("url");

    if (!destino) {
      return new Response("Falta el parámetro ?url=", { status: 400 });
    }

    let destinoUrl;
    try {
      destinoUrl = new URL(destino);
    } catch {
      return new Response("URL inválida", { status: 400 });
    }

    if (!DOMINIOS_PERMITIDOS.includes(destinoUrl.hostname)) {
      return new Response("Dominio no permitido", { status: 403 });
    }

    const upstream = await fetch(destinoUrl.toString(), {
      headers: {
        "User-Agent": "Mozilla/5.0 (compatible; RadarRegulatorioYPF/1.0)",
        "Accept-Language": "es-AR,es;q=0.9",
      },
    });

    return new Response(await upstream.text(), {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") || "text/html; charset=utf-8",
      },
    });
  },
};
