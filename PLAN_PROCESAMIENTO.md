# Plan Técnico Exhaustivo: Pipeline de Procesamiento de Datos y Métricas para News Dashboard

Este documento establece la arquitectura, diseño técnico y hoja de ruta paso a paso para construir el motor de procesamiento de datos y cálculo de métricas para el **News Dashboard**. 

---

## 1. Contexto, Decisiones Clave y Preguntas Abiertas

### 1.1. ¿Jupyter Notebooks o Scripts para el Procesamiento de Datos?
**Decisión recomendada: Scripts modulares en Python (`src/pipeline/`) complementados con notebooks de prototipado.**

* **Por qué no solo Notebooks:**
  * El volumen de datos es considerable (~390.000 noticias solo en la tabla de Chile, multiplicadas por 20 países).
  * Los cálculos de NLP (Transformers RoBERTuito con `pysentimiento`, análisis morfocintáctico POS y NER con `spaCy`, cálculo de MinHash LSH para detección de noticias sindicadas) son intensivos y pueden tardar varias horas.
  * Si una notebook se interrumpe (por error, reinicio de kernel o límite de memoria), se corre el riesgo de perder el estado y tener que reiniciar todo.
  * Una notebook no se presta para ejecución automatizada periódica (ej. 1 o 2 veces por semana) ni para pasar parámetros por línea de comando (`--country chile --days 7`).
* **Por qué un pipeline de Scripts Modulares es la mejor práctica de aprendizaje y calidad:**
  * **Ingeniería de Software sólida:** Separación de responsabilidades (`extract`, `metrics`, `checkpoints`, `export`).
  * **Sistema de Checkpointing y Resiliencia:** Cada noticia procesada se cachea por su `body_hash`. Si el proceso se pausa o se alcanzan límites, se reanuda de inmediato sin recalcular nada.
  * **CLI Ergonómico:** Permite ejecutar todo el pipeline o módulos individuales (`python -m src.pipeline.run --module pulse --country chile`).
* **Rol de las Notebooks:**
  * Se mantendrán notebooks ligeras en la carpeta `notebooks/` exclusivamente como laboratorio exploratorio: probar nuevas consultas, graficar distribuciones con muestras pequeñas (100 filas) y validar algoritmos antes de integrarlos al pipeline.

---

### 1.2. Desacoplamiento de Arquitectura y Despliegue en Railway
* **Realidad de la infraestructura:**
  * La base de datos PostgreSQL (`192.168.1.85:5432`) es local (LAN privada). Railway no tiene acceso a esta red.
  * Alojar modelos pesados de Deep Learning (PyTorch, spaCy `lg`) en un contenedor web de Railway causaría problemas de memoria (OOM) y sobrecostos.
* **Estrategia Data Mart / Pre-Agregación:**
  1. El procesamiento pesado se ejecuta **localmente** en la máquina que tiene acceso a PostgreSQL y aceleración de hardware.
  2. El pipeline exporta tablas agregadas, limpias y comprimidas a la carpeta `data/dashboard/` en formatos ultraligeros: **Parquet y JSON** (ej. series de tiempo de emociones suavizadas por día y medio, rankings de sensacionalismo, grafos de autoría Sankey, coordenadas geográficas de eventos).
  3. El tamaño combinado de todos los datasets pre-agregados rondará entre **10 MB y 25 MB** (en contraste con los gigabytes de la base cruda).
  4. Para Railway, estos archivos se versionan o sincronizan con el repositorio (o mediante un bucket gratuito como Cloudflare R2 / Supabase Storage).
  5. La aplicación **Plotly Dash en Railway** simplemente lee los archivos Parquet en memoria con DuckDB o Polars/Pandas en menos de 100 ms, ofreciendo una experiencia de usuario instantánea y costos de alojamiento mínimos.

---

### 1.3. Diagnóstico del MCP `antigravity-nb` en Windows
Al analizar las notebooks con la herramienta MCP `antigravity-nb`, se identificó una discrepancia de resolución de rutas en el entorno Windows: el argumento `--workspace-root ${workspaceFolder}` se interpretó de forma literal, sumado a una inconsistencia de codificación en el nombre de la carpeta `visualización de datos`. 

Para cumplir estrictamente las directrices de seguridad (no manipular procesos del sistema ni eludir chequeos de permisos), se realizó un análisis de bajo nivel mediante scripts de inspección dedicados, extrayendo y catalogando con precisión matemática el 100% del código, celdas y lógica de `exploracion_inicial.ipynb` y `eda_news.ipynb`.

---

## 2. Auditoría Exhaustiva: Qué se Tiene Hecho vs. Qué Falta por Hacer

| Módulo / Métrica en `PLAN.md` | Estado Actual | Ubicación del Código | Brechas y Trabajo Faltante |
|---|---|---|---|
| **1.1 Volumen de Publicación & Deltas** | Parcial | `exploracion_inicial.ipynb` (c. 19, 25) | Consultas DuckDB listas. Falta implementar cálculo de deltas (`% vs ayer / ventana anterior`) y filtro de fechas atípicas (fechas corruptas como año 1 o 2036). |
| **1.2 Velocidad Informativa (Noticias/hora)** | Avanzado | `exploracion_inicial.ipynb` (c. 19, 23, 25) | Implementada serie horaria continua con `generate_series`. Falta parametrizar y definir el disparador de alerta temprana ("Breaking News"). |
| **1.3 Tasa de Duplicación (Syndication Tracker)** | Prototipado | `exploracion_inicial.ipynb` (c. 30-36) | Implementado con `MinHashLSH` y trigramas de spaCy. Falta optimizar el extractor de trigramas (usar regex/NLTK para acelerar 50x) y almacenar pares sindicados. |
| **1.4 Anomalías de Longitud** | Prototipado | `exploracion_inicial.ipynb` (c. 40) | Consulta `length(body)` en DuckDB. Falta cálculo de percentiles 1% y 99% por medio y clasificación booleana de anomalías. |
| **2.1 Termómetro de Emociones** | Avanzado | `exploracion_inicial.ipynb` (c. 46-51), `eda_news.ipynb` (c. 157) | Usa `pysentimiento` (RoBERTuito). Falta implementar caché persistente por `body_hash` (para procesar solo noticias no vistas) y exportar series suavizadas. |
| **2.2 El Péndulo Temporal (Pasado vs Futuro)** | Listo en EDA | `eda_news.ipynb` (c. 163) | Diccionario de patrones regex muy completo. Falta migrar a script modular y calcular el índice normalizado (-100 a +100). |
| **2.3 N-gramas Emergentes (Trending Topics)** | Prototipado | `exploracion_inicial.ipynb` (c. 70-82), `eda_news.ipynb` (c. 101-108) | Extrae n-gramas con textacy y NLTK. Falta algoritmo de "emergencia" (comparar frecuencia en ventana reciente vs. ventana histórica base). |
| **2.4 Índice de Sensacionalismo** | Avanzado | `exploracion_inicial.ipynb` (c. 57-62) | Excelente fórmula híbrida: Densidad de adjetivos (POS) + Signos/Mayúsculas + Intensidad emocional. Falta estandarizar escala 0-100 y optimizar POS tagging. |
| **3.1 Embudo de Responsabilidad (Sankey)** | Listo en EDA | `eda_news.ipynb` (c. 57) | Limpieza de autor y clasificación para Sankey. Falta estructurar los nodos y enlaces en formato compatible con `plotly.graph_objects.Sankey`. |
| **3.2 Diversidad de Género en Firmas** | Listo en EDA | `eda_news.ipynb` (c. 57) | Integrado con `gender_guesser`. Falta agregación por medio y evolución en el tiempo. |
| **3.3 Monitor de Legibilidad (INFLESZ / Escolaridad)** | Listo en EDA | `eda_news.ipynb` (c. 88-90) | Fórmula INFLESZ y función de escolaridad listas. Falta integrar en el pipeline modular. |
| **3.4 Estructura del Discurso (POS por medio)** | Hecho en EDA | `eda_news.ipynb` (c. 110-126) | Conteo de POS tags por medio. Falta integrar en script y optimizar procesamiento en masa. |
| **4.1 Extracción NER (PER, ORG, LOC)** | Hecho en EDA | `eda_news.ipynb` (c. 136-143) | `spacy.pipe` con `es_core_news_lg` sobre lead (primeros 1.000 caracteres). Falta estructurar tabla de menciones indexada por fecha y medio. |
| **4.2 Mapa de Calor Geográfico** | Hecho en EDA | `eda_news.ipynb` (c. 146-153) | Geocodificación con OpenStreetMap (Nominatim) y caché en `geo_cache.json`. Falta preparar dataset de centroides y frecuencias para mapas de Plotly. |
| **4.3 Radar de Protagonistas (PER y ORG)** | Pendiente | Derivable de NER | No tiene función dedicada; se calcula agregando las entidades PER y ORG en ventanas de tiempo. |
| **4.4 Matriz de Consenso Cultural (Word2Vec)** | **Pendiente** | No implementado | Concepto teórico en `PLAN.md`. Requiere entrenar Word2Vec con Gensim o cargar embeddings pre-entrenados para calcular similitud coseno de conceptos entre países. |
| **5.1 Integridad del Corpus** | Parcial | `eda_news.ipynb` (c. 52) | Falta pipeline automático que calcule porcentaje de nulos por columna, fechas inválidas y volumen diario. |
| **5.2 Semáforo de Actividad de Medios** | Pendiente | No implementado | Falta consulta que calcule `MAX(date)` por medio vs `NOW()` para marcar Verde (<24h), Amarillo (24-72h) y Rojo (>72h). |

---

## 3. Arquitectura del Pipeline y Protocolo Anti-Pérdida por Cuotas

```
                                      [PostgreSQL Local (192.168.1.85)]
                                                      │
                                                      ▼ (DuckDB ATTACH)
                                           [Extractor & Sanitizer]
                                                      │
                                                      ▼
                                           data/raw_cache/*.parquet
                                                      │
            ┌─────────────────────┬───────────────────┼────────────────────┬─────────────────────┐
            ▼                     ▼                   ▼                    ▼                     ▼
     [Módulo 1: Pulso]    [Módulo 3: Autoría]  [Módulo 5: Calidad]   [Módulo 2: Tono]    [Módulo 4: Geopolítica]
     - Volumen/Deltas     - Sankey Autores     - Nulls por columna   - PySentimiento*    - spaCy NER*
     - Velocidad (h)      - Género             - Fechas corruptas    - Foco Temporal     - Geolocalización
     - MinHash LSH        - INFLESZ Legibil.   - Semáforo Fuentes    - Sensacionalismo   - Protagonistas
     - Anomalías Long.    - POS Discurso                             - N-gramas Emerg.   - Consenso Cultural
            │                     │                   │                    │                     │
            │                     │                   │            *Caché body_hash      *Caché body_hash
            │                     │                   │            (Checkpoints)         (Checkpoints)
            └─────────────────────┴───────────────────┼────────────────────┴─────────────────────┘
                                                      │
                                                      ▼
                                            [Exportador Agregado]
                                                      │
                                                      ▼
                                            data/dashboard/*.parquet  (~15 MB)
                                                      │
                                                      ▼
                                       [Plotly Dash App en Railway]
```

### Protocolo de Resiliencia ante Cuotas y Tiempos Largos:
1. **Idempotencia por Hash**: Los cálculos de inferencia pesada (Emociones y NER) se almacenan en `data/cache/nlp_features.parquet` usando `body_hash` como clave primaria. Al ejecutarse el pipeline, se hace un `LEFT ANTI JOIN` con la caché y **solo se procesan los registros nuevos**.
2. **Batching Gradual y Límites Configurables**: El orquestador soporta el argumento `--limit N` y `--batch-size B`. Esto permite procesar lotes controlados (ej. 2.000 noticias por sesión) sin riesgo de sobrepasar cuotas de memoria ni tiempo.
3. **Archivo de Estado `PIPELINE_STATE.json`**: Guarda un registro JSON con:
   * Último timestamp de ejecución.
   * Cantidad de filas procesadas por país.
   * Tasa de éxito y errores capturados.
   * Checklist de módulos completados.

---

## 4. Estructura de Archivos a Crear

```
news-dashboard/
├── PLAN.md                               # Plan general original
├── PLAN_PROCESAMIENTO.md                 # Este documento
├── PROGRESS.md                           # Bitácora viva de ejecución
├── .env                                  # POSTGRES_URI
├── data/
│   ├── raw_cache/                        # Extracciones intermedias locales (ignorado en git)
│   ├── cache/                            # Features NLP precalculadas (ignorado en git)
│   └── dashboard/                        # Datasets agregados para Dash (sincronizados)
│       ├── kpis_pulse.parquet
│       ├── emotions_timeseries.parquet
│       ├── sensacionalismo_ranking.parquet
│       ├── authorship_sankey.json
│       ├── readability_inflesz.parquet
│       ├── pos_distribution.parquet
│       ├── geo_locations.parquet
│       ├── top_entities.parquet
│       └── data_health.parquet
├── notebooks/                            # Prototipado y experimentación
│   ├── exploracion_inicial.ipynb
│   └── eda_news.ipynb
├── src/
│   ├── __init__.py
│   └── pipeline/
│       ├── __init__.py
│       ├── config.py                     # Constantes, rutas y credenciales
│       ├── db.py                         # Extracción y sanitización con DuckDB
│       ├── state.py                      # Control de checkpoints y resiliencia
│       ├── modules/
│       │   ├── __init__.py
│       │   ├── pulse.py                  # Módulo 1: Pulso operativo
│       │   ├── tone.py                   # Módulo 2: Emociones, péndulo, sensacionalismo
│       │   ├── authorship.py             # Módulo 3: Sankey, género, legibilidad, POS
│       │   ├── geopolitics.py            # Módulo 4: NER, mapas, protagonistas
│       │   └── quality.py                # Módulo 5: Integridad y semáforo
│       ├── export.py                     # Compilador de datasets para el dashboard
│       └── run.py                        # CLI principal
└── tests/
    └── test_pipeline.py                  # Pruebas automatizadas de consistencia
```

---

## 5. Plan de Ejecución Paso a Paso

### Fase 1: Cimientos, Sanitización y Control de Estado
* [ ] **Paso 1.1**: Crear estructura de carpetas (`src/pipeline/`, `src/pipeline/modules/`, `data/dashboard/`, `tests/`).
* [ ] **Paso 1.2**: Implementar `src/pipeline/config.py` y `src/pipeline/state.py` con soporte para tracking de lotes y `PIPELINE_STATE.json`.
* [ ] **Paso 1.3**: Implementar `src/pipeline/db.py` para extraer de PostgreSQL con DuckDB, aplicando reglas de sanitización de fechas (`date BETWEEN '2020-01-01' AND NOW() + INTERVAL '1 day'`) y guardando en `data/raw_cache/news_chile.parquet`.
* [ ] **Paso 1.4**: Crear `PROGRESS.md` para documentar cada avance.

### Fase 2: Módulos Operativos y Calidad (Rápidos)
* [ ] **Paso 2.1**: Implementar `src/pipeline/modules/pulse.py`:
  * Volumen y deltas porcentuales.
  * Velocidad informativa continua (`generate_series`).
  * MinHash LSH optimizado para duplicación/sindicación.
  * Anomalías de longitud (percentiles p01 y p99).
* [ ] **Paso 2.2**: Implementar `src/pipeline/modules/quality.py`:
  * Porcentaje de valores nulos e integridad del corpus.
  * Semáforo de conectividad de fuentes (tiempo transcurrido desde la última noticia).

### Fase 3: Módulos de Autoría y Complejidad
* [ ] **Paso 3.1**: Implementar `src/pipeline/modules/authorship.py`:
  * Limpieza y categorización de autor para diagrama Sankey.
  * Inferencia de género de firmas con `gender_guesser`.
  * Monitor de legibilidad (índice INFLESZ e interpolación de escolaridad).
  * Distribución de categorías gramaticales POS (adjetivos, verbos, sustantivos).

### Fase 4: Módulos Semánticos y Geopolíticos (Pesados con Checkpointing)
* [ ] **Paso 4.1**: Implementar `src/pipeline/modules/tone.py`:
  * Extracción de emociones con `pysentimiento` por batches e indexado por `body_hash`.
  * El Péndulo Temporal (balance pasado vs. futuro con regex semánticas).
  * Índice de Sensacionalismo (cruce de emociones, morfología y estilo).
  * N-gramas emergentes (comparativa temporal de frecuencias).
* [ ] **Paso 4.2**: Implementar `src/pipeline/modules/geopolitics.py`:
  * Extracción NER con `spacy.pipe` sobre leads periodísticos (con checkpointing).
  * Georreferenciación de entidades LOC utilizando la base caché existente y fallback local.
  * Radar de Protagonistas (Top PER y ORG en ventanas móviles).
  * Módulo de Consenso Cultural (Word2Vec / Distancias de Coseno).

### Fase 5: Consolidación, Exportación y Pruebas
* [ ] **Paso 5.1**: Implementar `src/pipeline/export.py` para generar todos los archivos finales en `data/dashboard/`.
* [ ] **Paso 5.2**: Implementar `src/pipeline/run.py` con la interfaz de comandos CLI (`--country`, `--days`, `--module`, `--limit`, `--resume`).
* [ ] **Paso 5.3**: Escribir y ejecutar suite de pruebas automatizadas en `tests/test_pipeline.py`.
