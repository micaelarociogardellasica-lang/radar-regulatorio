# ATLAS — Especificación del proyecto (repo aparte, post-Radar)

> Mapa vivo de los players de la industria de petróleo y gas en Argentina.
> Origen: profiling manual de empresas del upstream (hecho una vez a pedido de
> dirección); el Atlas lo automatiza, lo mantiene actualizado y lo extiende a
> midstream, downstream y cadenas comerciales.
> Prerequisito: Radar Regulatorio corriendo estable (comparte scrapers y eventos).

## 1. Qué responde el Atlas

- ¿Quién opera qué bloque, con qué socios y qué porcentajes? (upstream)
- ¿Quién es dueño/operador de cada ducto, terminal, planta y refinería? (mid/down)
- ¿Cuánto produce cada área y cada empresa? (mensual)
- ¿Cómo fluyen los hidrocarburos? — cadenas comerciales: crudo a refinerías,
  exportaciones por destino, importaciones (crudo liviano, gasoil, GNL)
- ¿Quién entra, quién sale, qué se vendió? — historial de M&A, cesiones, farm-outs

## 2. Modelo de datos (entidades)

```
Empresa {id, nombre, tipo: operadora|no-operadora|midstream|refinadora|comercializadora,
         cotiza: [BYMA|NYSE|—], grupo_controlante}
Bloque  {id, nombre, cuenca, provincia, tipo: convencional|CENCH|offshore,
         operador_id, socios: [{empresa_id, pct}], vencimiento_concesion,
         historial_cesiones: [{fecha, de, a, pct, norma, fuente}]}
Activo  {id, tipo: ducto|terminal|refineria|planta_separadora|licuefaccion,
         nombre, capacidad, operador_id, socios, ubicacion}
Produccion {bloque_id, mes, petroleo_m3d, gas_km3d, fuente: SE-CapIV}
FlujoComercial {origen, destino, producto, volumen, periodo, tipo: interno|expo|impo}
```

## 3. Fuentes de datos

### Estáticas / de carga inicial
- Profiling manual existente del upstream (base de arranque — la usuaria lo aporta).
- Datos abiertos Secretaría de Energía: áreas de concesión georreferenciadas
  (shapefiles), listado de operadores. ⚠️ Puede estar desactualizado: usar como
  base y corregir con el flujo de eventos.

### Dinámicas / actualización automática
- **Producción**: datos abiertos SE — declaraciones Capítulo IV (producción mensual
  por pozo/área/empresa), regalías, reservas anuales. Es la fuente más confiable
  del sistema; actualización mensual.
- **Cambios de titularidad (el punto crítico)**: NO hay fuente única. Circuito:
  1. **Boletines oficiales provinciales (Ejecutivo)**: los decretos de cesión de
     concesiones los dicta cada provincia como concedente (Ley 26.197). Fuente
     primaria. Prioridad: Neuquén, Río Negro, Chubut, Santa Cruz, Mendoza.
  2. **BORA**: áreas de jurisdicción nacional y offshore; autorizaciones de
     transporte y exportación.
  3. **CNV — hechos relevantes** (+ SEC filings para las que cotizan en NY):
     las cotizantes anuncian farm-outs/ventas antes del decreto. Señal temprana.
  4. **Prensa especializada** (RSS): capta operaciones en negociación.
  → El Radar ya scrapea varias de estas fuentes: el Atlas se suscribe a sus
    eventos en vez de duplicar scrapers.
- **Downstream**: SESCO (ventas de combustibles por empresa y producto),
  procesamiento por refinería (datos SE), precios en surtidor (datos abiertos).
- **Comercio exterior**: despachos de exportación por destino y posiciones de
  importación (crudo, gasoil, naftas, GNL) — INDEC/estadísticas aduaneras.

## 4. Visualización

- **Mapa interactivo** (Leaflet + shapefiles SE): bloques coloreados por operador,
  capas de ductos, refinerías, terminales y plantas. Click → ficha del activo.
- **Ficha por empresa**: bloques operados y participados, producción agregada,
  activos mid/down, historial de operaciones, participación en cámaras.
- **Ficha por bloque**: socios y %, producción histórica (gráfico), vencimientos,
  historial de cesiones con norma y link.
- **Vista de flujos**: diagrama de cadenas comerciales (crudo → refinerías →
  mercado interno/expo; importaciones → refinerías/mercado).
- **Ranking**: top productores por cuenca y por producto, cuota downstream por
  empresa (SESCO), evolución mensual.
- **Export Excel (.xlsx)**: tablas de empresas, bloques (con socios y %),
  activos y producción mensual como hojas separadas de un mismo archivo,
  regenerado con cada actualización — para análisis propio y para compartir
  internamente sin depender del dashboard.

## 5. Casos de uso

- Responder en minutos el pedido de profiling que antes llevó semanas.
- Detectar entradas/salidas de players apenas se publica el decreto o el hecho
  relevante (alerta del Radar → actualización del Atlas).
- Material de stakeholder mapping para AAPP: quién está en qué cámara, con quién
  comparte bloques, dónde hay intereses cruzados.
- Vencimientos de concesiones próximos = agenda regulatoria anticipada.

## 6. Fases del Atlas

1. **Carga inicial**: modelo de datos + import del profiling manual + shapefiles SE
   + producción mensual automática. Mapa básico + fichas de empresa y bloque.
2. **Flujo de eventos**: conexión con el Radar (cesiones detectadas en boletines
   provinciales y CNV actualizan el grafo con revisión manual de un click).
3. **Downstream + flujos comerciales**: SESCO, refinación, comercio exterior,
   vista de cadenas.
4. **Stakeholders**: cámaras, autoridades por jurisdicción, cruce con el mapa
   de actores del MAPA-MAESTRO.

## 7. Notas de diseño

- Misma identidad visual que el Radar (paleta azul vibrante, Archivo + IBM Plex).
- Toda cifra lleva fuente y fecha del dato; los % de participación llevan la norma
  que los respalda (trazabilidad = credibilidad frente a dirección).
- La revisión humana es parte del diseño: los cambios de titularidad detectados
  entran como "pendientes de confirmar" hasta que la usuaria los valida.
