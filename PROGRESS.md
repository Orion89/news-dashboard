# Bitácora de Avance del Proyecto (Progress Log)

Este documento registra de forma granular el estado de avance del pipeline de procesamiento y métricas del News Dashboard. Permite reanudar el trabajo sin perder contexto tras límites de sesión o cortes de cuota.

---

## Estado Global
* **Fase Actual**: Fase 1: Cimientos, Sanitización de Datos y Sistema de Checkpoints.
* **País de Referencia Inicial**: Chile (`news_chile`).
* **Ventana Temporal Activa**: 7 días (`--days 7`).
* **Última Actualización**: 2026-11-20.

---

## Checklist Detallado por Fases

### Fase 1: Cimientos, Sanitización de Datos y Sistema de Checkpoints
- [x] **Paso 1.1**: Estructura modular de carpetas creada (`src/pipeline/modules/`, `data/raw_cache/`, `data/cache/`, `data/dashboard/`, `tests/`).
- [x] **Paso 1.2**: Implementar `src/pipeline/config.py` con resolución de rutas, `.env` y parámetros por defecto.
- [x] **Paso 1.3**: Implementar `src/pipeline/state.py` para control de checkpoints y resiliencia (`pipeline_state.json`).
- [x] **Paso 1.4**: Implementar `src/pipeline/db.py` con DuckDB, sanitización de fechas atípicas (descarte de años 1 y 2036) y extracción cacheada en Parquet.
- [x] **Paso 1.5**: Implementar y ejecutar pruebas automatizadas en `tests/test_pipeline.py`.

---

### Fase 2: Módulos Operativos y Calidad (Rápidos)
- [ ] **Paso 2.1**: Implementar `src/pipeline/modules/pulse.py`:
  - [ ] Volumen diario y deltas porcentuales.
  - [ ] Velocidad informativa horaria (`generate_series` continuo).
  - [ ] MinHash LSH para detección de noticias sindicadas/duplicadas.
  - [ ] Detección de anomalías de longitud (percentiles p01 y p99).
- [ ] **Paso 2.2**: Implementar `src/pipeline/modules/quality.py`:
  - [ ] Integridad del corpus (% de nulos por columna).
  - [ ] Semáforo de actividad de fuentes (tiempo desde última noticia).
- [ ] **Paso 2.3**: Pruebas unitarias de Fase 2.

---

### Fase 3: Módulos de Autoría y Complejidad
- [ ] **Paso 3.1**: Implementar `src/pipeline/modules/authorship.py`:
  - [ ] Limpieza de firmas y categorización para Sankey (Redacción vs. Autor vs. Agencia).
  - [ ] Detección de diversidad de género en firmas con `gender_guesser`.
  - [ ] Monitor de legibilidad INFLESZ y escala de escolaridad.
  - [ ] Distribución de categorías gramaticales POS (adjetivos, verbos, sustantivos).
- [ ] **Paso 3.2**: Pruebas unitarias de Fase 3.

---

### Fase 4: Módulos Semánticos y Geopolíticos (Pesados con Checkpointing)
- [ ] **Paso 4.1**: Implementar `src/pipeline/modules/tone.py`:
  - [ ] Inferencia de emociones con `pysentimiento` por batches e indexado por `body_hash`.
  - [ ] El Péndulo Temporal (balance semántico pasado vs. futuro).
  - [ ] Cálculo del Índice de Sensacionalismo (POS + Mayúsculas/Signos + Emociones).
  - [ ] Detección de N-gramas emergentes.
- [ ] **Paso 4.2**: Implementar `src/pipeline/modules/geopolitics.py`:
  - [ ] Extracción NER con `spacy.pipe` sobre lead periodístico con caché por `body_hash`.
  - [ ] Georreferenciación de entidades LOC con caché local.
  - [ ] Radar de Protagonistas (Top PER y ORG).
  - [ ] *(Pausado por solicitud del usuario)* Consenso Cultural con modelos ajustados de 4 países.
- [ ] **Paso 4.3**: Pruebas unitarias de Fase 4.

---

### Fase 5: Consolidación, Exportación para Dash y CLI
- [ ] **Paso 5.1**: Implementar `src/pipeline/export.py` para compilar tablas en `data/dashboard/*.parquet` y `*.json`.
- [ ] **Paso 5.2**: Implementar `src/pipeline/run.py` con soporte CLI completo (`--country`, `--days`, `--module`, `--force-refresh`).
- [ ] **Paso 5.3**: Verificación integral y documentación de despliegue en Railway.
