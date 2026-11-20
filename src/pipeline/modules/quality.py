"""
Módulo 5: Salud y Calidad de Datos (Data Quality & Health).
Calcula:
1. Integridad del corpus: Porcentaje de nulos por columna, textos vacíos o anormalmente cortos.
2. Semáforo de actividad de medios (Scraper Connection Health):
   - Verde (activo): Última publicación hace <= 24 horas.
   - Amarillo (retrasado): Última publicación hace entre 24 y 72 horas.
   - Rojo (alerta / posible fallo o bloqueo): Última publicación hace > 72 horas.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
import pandas as pd

from src.pipeline.config import DASHBOARD_DIR
from src.pipeline.db import extract_news
from src.pipeline.state import record_module_run


def calculate_corpus_integrity(df: pd.DataFrame) -> pd.DataFrame:
    """
    Evalúa la tasa de completitud y valores nulos por columna en el corpus.
    """
    total_rows = len(df)
    if total_rows == 0:
        return pd.DataFrame()

    columns_to_audit = ["id", "media_name", "url", "date", "author", "body", "body_hash"]
    records = []

    for col in columns_to_audit:
        if col in df.columns:
            null_count = int(df[col].isna().sum())
            null_pct = round((null_count / total_rows) * 100.0, 2)
            # Conteo de cadenas vacías o compuestas solo por espacios
            if df[col].dtype == "object":
                empty_str = int((df[col].fillna("").astype(str).str.strip() == "").sum())
            else:
                empty_str = 0
            records.append({
                "column_name": col,
                "null_count": null_count,
                "null_pct": null_pct,
                "empty_string_count": empty_str,
                "total_rows": total_rows,
            })

    # Verificación de cuerpos de texto anormalmente cortos (< 100 caracteres)
    if "body" in df.columns:
        short_texts = int((df["body"].astype(str).str.len() < 100).sum())
        records.append({
            "column_name": "body_below_100_chars",
            "null_count": short_texts,
            "null_pct": round((short_texts / total_rows) * 100.0, 2),
            "empty_string_count": 0,
            "total_rows": total_rows,
        })

    return pd.DataFrame(records)


def calculate_source_health(
    df: pd.DataFrame,
    anchor_date: datetime | None = None,
) -> pd.DataFrame:
    """
    Calcula el estado operativo (semáforo) de cada medio de comunicación
    en función de la antigüedad de su última publicación.
    """
    if df.empty:
        return pd.DataFrame()

    latest_date = anchor_date or df["date"].max()

    source_stats = (
        df.groupby("media_name")
        .agg(
            total_articles=("id", "count"),
            first_seen=("date", "min"),
            last_seen=("date", "max"),
        )
        .reset_index()
    )

    # Calcular horas transcurridas desde la última publicación
    source_stats["hours_since_last_seen"] = round(
        (latest_date - source_stats["last_seen"]).dt.total_seconds() / 3600.0, 1
    )

    # Reglas del semáforo
    # Verde: <= 24h | Amarillo: 24h a 72h | Rojo: > 72h
    def assign_status(hours: float) -> str:
        if hours <= 24.0:
            return "verde"
        elif hours <= 72.0:
            return "amarillo"
        else:
            return "rojo"

    source_stats["status"] = source_stats["hours_since_last_seen"].apply(assign_status)
    source_stats = source_stats.sort_values(
        ["status", "total_articles"], ascending=[True, False]
    ).reset_index(drop=True)

    return source_stats


def process_quality(
    df: pd.DataFrame | None = None,
    country: str = "chile",
    days: int = 7,
) -> dict[str, Any]:
    """
    Función orquestadora principal del Módulo 5.
    Ejecuta auditoría de integridad y salud de fuentes y exporta los datasets.
    """
    if df is None:
        df = extract_news(country=country, days=days)

    df_integrity = calculate_corpus_integrity(df)
    df_sources_health = calculate_source_health(df)

    # Métricas agregadas de resumen
    total_sources = len(df_sources_health)
    status_counts = df_sources_health["status"].value_counts().to_dict()
    green_count = status_counts.get("verde", 0)
    yellow_count = status_counts.get("amarillo", 0)
    red_count = status_counts.get("rojo", 0)

    health_summary = {
        "total_sources_evaluated": total_sources,
        "sources_green": green_count,
        "sources_yellow": yellow_count,
        "sources_red": red_count,
        "health_score_pct": round((green_count / max(total_sources, 1)) * 100.0, 1),
    }

    # Exportar a data/dashboard/
    df_integrity.to_parquet(DASHBOARD_DIR / "quality_corpus_integrity.parquet", index=False)
    df_sources_health.to_parquet(DASHBOARD_DIR / "quality_sources_health.parquet", index=False)
    pd.DataFrame([health_summary]).to_parquet(
        DASHBOARD_DIR / "quality_summary.parquet", index=False
    )

    # Registrar checkpoint
    record_module_run(
        country=country,
        module_name="quality",
        status="success",
        records_processed=len(df),
        metadata=health_summary,
    )

    return {
        "integrity": df_integrity,
        "sources_health": df_sources_health,
        "summary": health_summary,
    }
