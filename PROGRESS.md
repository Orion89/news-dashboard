# Bitácora de Avance del Proyecto (Progress Log)

Este documento registra de forma granular el estado de avance del pipeline de procesamiento y métricas del News Dashboard. Permite reanudar el trabajo sin perder contexto tras límites de sesión o cortes de cuota.

---

## Estado Global
* **Fase Actual**: 100% Completado (Pipeline de Datos + Dashboard Web en Plotly Dash listo para Railway).
* **País de Referencia Inicial**: Chile (`news_chile`).
* **Ventana Temporal Activa**: 7 días (`--days 7`).
* **Última Actualización**: 2026-11-22.

---

## Checklist Detallado por Fases

### Fase 1: Cimientos, Sanitización de Datos y Sistema de Checkpoints
- [x] **Paso 1.1**: Estructura modular de carpetas creada (`src/pipeline/modules/`, `data/raw_cache/`, `data/cache/`, `data/dashboard/`, `tests/`).
- [x] **Paso 1.2**: Implementar `src/pipeline/config.py` con resolución de rutas, `.env` y parámetros por defecto.
- [x] **Paso 1.3**: Implementar `src/pipeline/state.py` para control de checkpoints y resiliencia (`pipeline_state.json`).
- [x] **Paso 1.4**: Implementar `src/pipeline/db.py` con DuckDB, sanitización de fechas atípicas (descarte de años 1 y 2036) y extracción cacheada en Parquet (`5.603` noticias).
- [x] **Paso 1.5**: Implementar y ejecutar pruebas automatizadas en `tests/test_pipeline.py`.

---

### Fase 2: Módulos Operativos y Calidad (Rápidos)
- [x] **Paso 2.1**: Implementar `src/pipeline/modules/pulse.py`:
  - [x] Volumen diario/24h y deltas porcentuales (+X% vs ventana anterior).
  - [x] Velocidad informativa horaria (`generate_series` continuo) para volumen global y Top 10 medios.
  - [x] Detección de picos ("Breaking News alert" basada en media + 2*desviación estándar).
  - [x] MinHash LSH optimizado para duplicación/sindicación entre medios.
  - [x] Detección de anomalías de longitud (percentiles p01 y p99).
- [x] **Paso 2.2**: Implementar `src/pipeline/modules/quality.py`:
  - [x] Integridad del corpus (% de nulos y cadenas vacías por columna, textos cortos).
  - [x] Semáforo de actividad de medios (verde <=24h, amarillo 24-72h, rojo >72h).
  - [x] Resumen y Health Score global del scraping.
- [x] **Paso 2.3**: Pruebas unitarias de Fase 2 pasadas exitosamente (100% de cobertura funcional).

---

### Fase 3: Módulos de Autoría y Complejidad
- [x] **Paso 3.1**: Implementar `src/pipeline/modules/authorship.py`:
  - [x] Limpieza de firmas y categorización para Sankey (Redacción/Anónimos vs. Agencias vs. Periodistas firmantes).
  - [x] Inferencia de diversidad de género en firmas con `gender_guesser` (Hombre vs. Mujer vs. No Identificado).
  - [x] Monitor de legibilidad INFLESZ (Flesch-Szigriszt) y escala de escolaridad requerida por medio.
  - [x] Distribución de categorías gramaticales POS (adjetivos, verbos, sustantivos) y perfil dominante de discurso por medio.
- [x] **Paso 3.2**: Pruebas unitarias de Fase 3 integradas y validadas al 100%.

---

### Fase 4: Módulos Semánticos y Geopolíticos (Pesados con Checkpointing)
- [x] **Paso 4.1**: Implementar `src/pipeline/modules/tone.py`:
  - [x] Inferencia de emociones con `pysentimiento` por batches en GPU (CUDA) con caché por `body_hash` (`emotions_cache.parquet`).
  - [x] El Péndulo Temporal (balance semántico pasado vs. futuro en escala -100 a +100).
  - [x] Cálculo del Índice de Sensacionalismo (cruce ponderado de emociones extremas, adjetivación y estilo/mayúsculas).
  - [x] Detección de N-gramas emergentes (growth ratio ventana reciente vs. baseline).
- [x] **Paso 4.2**: Implementar `src/pipeline/modules/geopolitics.py`:
  - [x] Extracción NER con `spaCy` (`es_core_news_lg`) sobre leads con caché persistente por `body_hash` (`ner_cache.parquet`).
  - [x] Mapa de Calor Geográfico con catálogo de coordenadas regionales y localidades de Chile.
  - [x] Radar de Protagonistas (Top figuras públicas PER y organizaciones ORG).
  - [ ] *(Pausado por solicitud del usuario)* Consenso Cultural con modelos ajustados de 4 países.
- [x] **Paso 4.3**: Pruebas unitarias de Fase 4 integradas y validadas al 100%.

---

### Fase 5: Consolidación, Exportación para Dash y CLI
- [x] **Paso 5.1**: Implementar `src/pipeline/export.py` para compilar tablas en `data/dashboard/*.parquet`, `*.json` y generar `data_manifest.json`.
- [x] **Paso 5.2**: Implementar `src/pipeline/run.py` con soporte CLI completo (`--country`, `--days`, `--module`, `--force-refresh`, `--limit-nlp`).
- [x] **Paso 5.3**: Verificación integral (11 pruebas automatizadas aprobadas al 100%) y preparación para el frontend en Plotly Dash y Railway.

---

### Fase 6: Cimientos y Fundamentos Visuales (Tokens, CSS, Loader, Componentes Base)
- [x] **Paso 6.1**: Implementar `src/dashboard/config.py` con tokens Dark Slate (`#0B0F19`, `#1E293B`, `#334155`) y template Plotly `news_dark`.
- [x] **Paso 6.2**: Implementar hoja de estilos central en `assets/styles.css` con grilla de 12 columnas, `tabular-nums`, estilos de tarjeta KPI y pestañas.
- [x] **Paso 6.3**: Implementar proveedor de datos y caché en memoria en `src/dashboard/data_loader.py` para los 19 datasets.
- [x] **Paso 6.4**: Implementar componentes base (`kpi_card.py`, `header.py`, `empty_state.py`).
- [x] **Paso 6.5**: Pruebas unitarias de cimientos aprobadas al 100%.

---

### Fase 7: Vistas Operacionales ("El Pulso" y "Calidad de Datos")
- [x] **Paso 7.1**: Implementar `src/dashboard/views/pulse_view.py`:
  - [x] Banner de 4 BANs (Volumen 24h con delta %, Promedio Diario, Pico récord horario, Tasa de sindicación).
  - [x] Curva continua de velocidad horaria con área y umbral de alerta Breaking News (μ + 2σ).
  - [x] Gráfico horizontal de medios con mayor tasa de sindicación (cables duplicados con MinHash LSH).
  - [x] Monitor de anomalías de extensión (p01 micro-notas y p99 manifiestos).
- [x] **Paso 7.2**: Implementar `src/dashboard/views/quality_view.py`:
  - [x] Tarjetas de salud del scraper (fuentes verdes ≤12h, amarillas 12-48h, rojas >48h y score global).
  - [x] Gráfico de barras horizontales de integridad del corpus (% de completitud por columna).
  - [x] Directorio interactivo de fuentes con DataTable (paginación, ordenamiento y filtrado nativo).
- [x] **Paso 7.3**: Pruebas unitarias operacionales validadas al 100%.

---

### Fase 8: Vistas de Contenido y Análisis Semántico ("El Tono", "Autoría", "Geopolítica")
- [x] **Paso 8.1**: Implementar `src/dashboard/views/tone_view.py`:
  - [x] Multilínea de evolución temporal de emociones (RoBERTuito fine-tuned).
  - [x] Ranking de sensacionalismo editorial por medio con desglose de componentes.
  - [x] Indicador tipo velocímetro del péndulo temporal (-100 a +100 pasado vs futuro).
  - [x] Píldoras de términos y n-gramas emergentes (Trending Topics).
- [x] **Paso 8.2**: Implementar `src/dashboard/views/authorship_view.py`:
  - [x] Diagrama interactivo Sankey de trazabilidad (Corpus → Agencias/Anónimos/Firmados → Género).
  - [x] Scorecard de diversidad de género en periodismo de opinión e investigación.
  - [x] Índice de legibilidad INFLESZ por medio con umbral de estándar prensa (55 pts).
  - [x] Barras apiladas de perfil gramatical POS (sustantivos, verbos, adjetivos).
- [x] **Paso 8.3**: Implementar `src/dashboard/views/geopolitics_view.py`:
  - [x] Mapa de burbujas de Chile con `scatter_geo` centrado en territorio nacional.
  - [x] Radar de protagonistas: Top 10 figuras públicas (PER) y Top 10 organizaciones (ORG).
- [x] **Paso 8.4**: Pruebas unitarias semánticas validadas al 100%.

---

### Fase 9: Callbacks, Ensamblado de `app.py` y Empaquetado para Railway
- [x] **Paso 9.1**: Implementar `src/dashboard/callbacks.py` con cambio dinámico de pestañas y filtro global de medios.
- [x] **Paso 9.2**: Implementar `app.py` como punto de entrada central, exportando `server = app.server`.
- [x] **Paso 9.3**: Crear `requirements-web.txt` y `Procfile` para despliegue liviano en Railway (< 150 MB RAM, sin dependencias pesadas).
- [x] **Paso 9.4**: Verificación con 10 pruebas unitarias automatizadas (`tests/test_dashboard.py`) y test client WSGI (HTTP 200).

---

## Guía de Uso del Orquestador CLI

```powershell
# 1. Ejecutar todo el pipeline completo para Chile (7 días):
$env:PYTHONPATH="."; C:\Users\leomo\anaconda3\envs\data\python.exe -m src.pipeline.run --country chile --days 7 --module all

# 2. Ejecutar un módulo individual (ej. El Pulso):
$env:PYTHONPATH="."; C:\Users\leomo\anaconda3\envs\data\python.exe -m src.pipeline.run --country chile --module pulse

# 3. Forzar re-extracción de noticias desde PostgreSQL ignorando caché:
$env:PYTHONPATH="."; C:\Users\leomo\anaconda3\envs\data\python.exe -m src.pipeline.run --country chile --force-refresh

# 4. Validar e imprimir el catálogo y manifiesto de datasets del dashboard:
$env:PYTHONPATH="."; C:\Users\leomo\anaconda3\envs\data\python.exe -m src.pipeline.run --module export
```
