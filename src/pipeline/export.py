"""
Compilador, validador de integridad y generador de manifiesto para el News Dashboard.
Verifica que los 19 datasets requeridos en data/dashboard/ existan, tengan esquemas válidos
y genera data_manifest.json como contrato de datos para la aplicación Plotly Dash.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd

from src.pipeline.config import DASHBOARD_DIR

# Catálogo oficial de datasets requeridos para el News Dashboard
REQUIRED_DATASETS: dict[str, dict[str, Any]] = {
    # Módulo 1: El Pulso
    "pulse_kpis.parquet": {
        "module": "pulse",
        "description": "KPIs operativos del Top Banner (volumen 24h, deltas, promedio diario, sindicación)",
        "expected_columns": ["recent_24h_volume", "delta_24h_pct", "syndication_rate_pct"],
        "format": "parquet",
    },
    "pulse_hourly_velocity.parquet": {
        "module": "pulse",
        "description": "Serie continua por hora del volumen global con umbrales de alerta temprana (Breaking News)",
        "expected_columns": ["hour_bucket", "news_count", "is_peak"],
        "format": "parquet",
    },
    "pulse_hourly_top_media.parquet": {
        "module": "pulse",
        "description": "Serie continua hora por hora para los Top medios de comunicación",
        "expected_columns": ["hour_bucket", "media_name", "news_count"],
        "format": "parquet",
    },
    "pulse_syndication_by_media.parquet": {
        "module": "pulse",
        "description": "Tasa de noticias duplicadas o cables sindicados agregados por medio",
        "expected_columns": ["media_name", "total_articles", "syndicated_articles", "syndication_rate_pct"],
        "format": "parquet",
    },
    "pulse_length_anomalies.parquet": {
        "module": "pulse",
        "description": "Noticias en los percentiles extremos 1% (cables ultracortos) y 99% (reportajes extensos)",
        "expected_columns": ["id", "media_name", "char_length", "anomaly_type"],
        "format": "parquet",
    },
    # Módulo 5: Calidad de Datos
    "quality_corpus_integrity.parquet": {
        "module": "quality",
        "description": "Porcentaje de nulos y cadenas vacías por columna del corpus",
        "expected_columns": ["column_name", "null_count", "null_pct", "total_rows"],
        "format": "parquet",
    },
    "quality_sources_health.parquet": {
        "module": "quality",
        "description": "Semáforo operativo de fuentes (verde, amarillo, rojo) según antigüedad de publicación",
        "expected_columns": ["media_name", "hours_since_last_seen", "status"],
        "format": "parquet",
    },
    "quality_summary.parquet": {
        "module": "quality",
        "description": "Health Score y métricas agregadas de salud de extracción",
        "expected_columns": ["total_sources_evaluated", "health_score_pct"],
        "format": "parquet",
    },
    # Módulo 3: Autoría y Complejidad
    "authorship_sankey.json": {
        "module": "authorship",
        "description": "Estructura de nodos y enlaces para el diagrama de Sankey de autoría y género",
        "expected_columns": ["nodes", "links", "counts"],
        "format": "json",
    },
    "authorship_gender_kpis.parquet": {
        "module": "authorship",
        "description": "Cuota de participación de mujeres vs. hombres y tasa de artículos firmados",
        "expected_columns": ["total_news", "total_signed", "female_ratio_pct", "signed_pct"],
        "format": "parquet",
    },
    "authorship_media_stats.parquet": {
        "module": "authorship",
        "description": "Distribución porcentual de autoría (anónimo, agencia, firmado, género) por medio",
        "expected_columns": ["media_name", "anon_pct", "agency_pct", "signed_pct"],
        "format": "parquet",
    },
    "authorship_readability.parquet": {
        "module": "authorship",
        "description": "Índice de legibilidad INFLESZ y escolaridad requerida por medio de comunicación",
        "expected_columns": ["media_name", "mean_inflesz", "mean_schooling_years", "readability_category"],
        "format": "parquet",
    },
    "authorship_pos_distribution.parquet": {
        "module": "authorship",
        "description": "Distribución de categorías gramaticales POS (adjetivos, verbos, sustantivos) por medio",
        "expected_columns": ["media_name", "adj_pct", "noun_pct", "verb_pct", "discourse_profile"],
        "format": "parquet",
    },
    # Módulo 2: El Tono
    "tone_emotions_timeseries.parquet": {
        "module": "tone",
        "description": "Evolución temporal suavizada de emociones dominantes (PySentimiento) por medio",
        "expected_columns": ["date_day", "media_name", "emotion", "intensity"],
        "format": "parquet",
    },
    "tone_pendulum_daily.parquet": {
        "module": "tone",
        "description": "Balance semántico diario de orientación al Pasado vs. Futuro (-100 a +100)",
        "expected_columns": ["date_day", "media_name", "daily_pendulum_score"],
        "format": "parquet",
    },
    "tone_sensationalism_ranking.parquet": {
        "module": "tone",
        "description": "Ranking de medios por Índice de Sensacionalismo (cruce de emociones, POS y estilo)",
        "expected_columns": ["media_name", "avg_sensationalism", "rank"],
        "format": "parquet",
    },
    "tone_emerging_ngrams.parquet": {
        "module": "tone",
        "description": "Top de bigramas y trigramas emergentes (Trending Topics) por tasa de crecimiento",
        "expected_columns": ["ngram", "ngram_type", "growth_ratio"],
        "format": "parquet",
    },
    # Módulo 4: Geopolítico
    "geopolitics_protagonists.parquet": {
        "module": "geopolitics",
        "description": "Radar de personas (PER) y organizaciones (ORG) más nombradas en la ventana de tiempo",
        "expected_columns": ["entity", "type", "total_mentions"],
        "format": "parquet",
    },
    "geopolitics_locations.parquet": {
        "module": "geopolitics",
        "description": "Entidades de ubicación (LOC) geolocalizadas con coordenadas y frecuencia de mención",
        "expected_columns": ["city", "latitude", "longitude", "total_mentions"],
        "format": "parquet",
    },
}


def get_dataset_metadata(filepath: Path) -> dict[str, Any]:
    """Extrae el conteo de filas, columnas y tamaño de un archivo Parquet o JSON."""
    if not filepath.exists():
        return {"exists": False, "rows": 0, "size_bytes": 0, "columns": []}

    size_bytes = filepath.stat().st_size
    suffix = filepath.suffix.lower()

    if suffix == ".parquet":
        try:
            df = pd.read_parquet(filepath)
            return {
                "exists": True,
                "rows": len(df),
                "size_bytes": size_bytes,
                "columns": list(df.columns),
            }
        except Exception as e:
            return {"exists": True, "rows": 0, "size_bytes": size_bytes, "columns": [], "error": str(e)}

    elif suffix == ".json":
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                rows = len(data)
                columns = list(data[0].keys()) if rows > 0 and isinstance(data[0], dict) else []
            elif isinstance(data, dict):
                rows = 1
                columns = list(data.keys())
            else:
                rows = 1
                columns = []
            return {
                "exists": True,
                "rows": rows,
                "size_bytes": size_bytes,
                "columns": columns,
            }
        except Exception as e:
            return {"exists": True, "rows": 0, "size_bytes": size_bytes, "columns": [], "error": str(e)}

    return {"exists": True, "rows": 0, "size_bytes": size_bytes, "columns": []}


def verify_dashboard_integrity() -> tuple[bool, list[str]]:
    """
    Verifica que todos los datasets requeridos existan y cumplan con las columnas esperadas.
    Retorna (is_valid, list_of_errors).
    """
    errors = []
    for filename, spec in REQUIRED_DATASETS.items():
        filepath = DASHBOARD_DIR / filename
        if not filepath.exists():
            errors.append(f"Falta archivo requerido: {filename}")
            continue

        meta = get_dataset_metadata(filepath)
        if meta.get("size_bytes", 0) == 0:
            errors.append(f"Archivo vacío (0 bytes): {filename}")
            continue

        if "error" in meta:
            errors.append(f"Error al leer {filename}: {meta['error']}")
            continue

        # Validar columnas mínimas requeridas
        expected = set(spec.get("expected_columns", []))
        found = set(meta.get("columns", []))
        missing_cols = expected - found
        if missing_cols:
            errors.append(
                f"Columnas faltantes en {filename}: {sorted(missing_cols)}"
            )

    return len(errors) == 0, errors


def generate_manifest(country: str = "chile", days: int = 7) -> dict[str, Any]:
    """
    Genera el archivo data_manifest.json en data/dashboard/,
    documentando el catálogo completo de datasets, esquemas y metadatos.
    """
    catalog: dict[str, Any] = {}
    total_bytes = 0

    for filename, spec in REQUIRED_DATASETS.items():
        filepath = DASHBOARD_DIR / filename
        meta = get_dataset_metadata(filepath)
        size = meta.get("size_bytes", 0)
        total_bytes += size

        catalog[filename] = {
            "module": spec["module"],
            "description": spec["description"],
            "format": spec["format"],
            "exists": meta.get("exists", False),
            "rows": meta.get("rows", 0),
            "size_bytes": size,
            "size_kb": round(size / 1024.0, 2),
            "columns": meta.get("columns", []),
        }

    manifest = {
        "version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "country": country,
        "window_days": days,
        "total_datasets": len(catalog),
        "total_size_bytes": total_bytes,
        "total_size_kb": round(total_bytes / 1024.0, 2),
        "status": "complete" if all(d["exists"] for d in catalog.values()) else "incomplete",
        "datasets": catalog,
    }

    manifest_file = DASHBOARD_DIR / "data_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return manifest


def print_dashboard_catalog(manifest: dict[str, Any] | None = None) -> None:
    """Imprime en consola un resumen formateado del catálogo de datasets para el dashboard."""
    data = manifest or generate_manifest()
    print("=" * 80)
    print(f"CATÁLOGO DE DATASETS PARA PLOTLY DASH ({data['country'].upper()} - {data['window_days']} DÍAS)")
    print(f"Generado: {data['generated_at']} | Total archivos: {data['total_datasets']} | Tamaño total: {data['total_size_kb']} KB")
    print("=" * 80)
    print(f"{'Archivo':<36} {'Módulo':<14} {'Filas':<8} {'Tamaño (KB)':<12}")
    print("-" * 80)
    for fname, info in sorted(data["datasets"].items()):
        status = f"{info['size_kb']} KB" if info["exists"] else "NO ENCONTRADO"
        print(f"{fname:<36} {info['module']:<14} {info['rows']:<8} {status:<12}")
    print("=" * 80)
