# Bitácora de Avance del Proyecto (Progress Log)

Este documento registra de forma granular el estado de avance del pipeline de procesamiento y métricas del News Dashboard. Permite reanudar el trabajo sin perder contexto tras límites de sesión o cortes de cuota.

---

## Estado Global
* **Fase Actual**: Fase 4 Completada (El Tono y Geopolítico).
* **País de Referencia Inicial**: Chile (`news_chile`).
* **Ventana Temporal Activa**: 7 días (`--days 7`).
* **Última Actualización**: 2026-11-20.

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
- [ ] **Paso 5.1**: Implementar `src/pipeline/export.py` para compilar tablas en `data/dashboard/*.parquet` y `*.json`.
- [ ] **Paso 5.2**: Implementar `src/pipeline/run.py` con soporte CLI completo (`--country`, `--days`, `--module`, `--force-refresh`).
- [ ] **Paso 5.3**: Verificación integral y documentación de despliegue en Railway.
