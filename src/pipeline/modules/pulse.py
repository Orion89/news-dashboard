"""
Módulo 1: El Pulso (KPIs Operativos en Tiempo Real).
Calcula:
1. Volumen de publicación reciente y Deltas porcentuales (últimas 24h vs 24h previas).
2. Velocidad informativa horaria continua (serie temporal sin vacíos) y detección de picos (Breaking News).
3. Tasa de duplicación / sindicación de noticias mediante MinHash LSH optimizado.
4. Detección de anomalías de longitud (percentiles p01 y p99).
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any
import duckdb
import numpy as np
import pandas as pd
from datasketch import MinHash, MinHashLSH

from src.pipeline.config import DASHBOARD_DIR
from src.pipeline.db import extract_news
from src.pipeline.state import record_module_run

WORD_RE = re.compile(r"\b[a-záéíóúüñ]{3,}\b")


def _extract_trigrams(text: str, max_chars: int = 3000) -> list[str]:
    """Extrae trigramas de palabras normalizadas rápidamente usando expresiones regulares."""
    if not isinstance(text, str) or not text.strip():
        return []
    words = WORD_RE.findall(text.lower()[:max_chars])
    if len(words) < 3:
        return words
    return [" ".join(words[i:i + 3]) for i in range(len(words) - 2)]


def calculate_volume_and_deltas(
    df: pd.DataFrame,
    anchor_date: datetime | None = None,
) -> dict[str, Any]:
    """
    Calcula el volumen de publicaciones en las últimas 24 horas y su variación porcentual (delta)
    respecto a las 24 horas inmediatamente anteriores, además de estadísticas de la ventana total.
    """
    if df.empty:
        return {
            "recent_24h_volume": 0,
            "prev_24h_volume": 0,
            "delta_24h_pct": 0.0,
            "total_window_volume": 0,
            "daily_avg_volume": 0.0,
            "anchor_date": None,
        }

    latest = anchor_date or df["date"].max()
    t_24h_ago = latest - timedelta(hours=24)
    t_48h_ago = latest - timedelta(hours=48)

    vol_24h = int(((df["date"] > t_24h_ago) & (df["date"] <= latest)).sum())
    vol_prev_24h = int(((df["date"] > t_48h_ago) & (df["date"] <= t_24h_ago)).sum())

    if vol_prev_24h > 0:
        delta_pct = round(((vol_24h - vol_prev_24h) / vol_prev_24h) * 100.0, 2)
    else:
        delta_pct = 100.0 if vol_24h > 0 else 0.0

    total_vol = len(df)
    min_date = df["date"].min()
    days_span = max((latest - min_date).total_seconds() / 86400.0, 1.0)
    daily_avg = round(total_vol / days_span, 1)

    return {
        "recent_24h_volume": vol_24h,
        "prev_24h_volume": vol_prev_24h,
        "delta_24h_pct": delta_pct,
        "total_window_volume": total_vol,
        "daily_avg_volume": daily_avg,
        "anchor_date": latest.strftime("%Y-%m-%d %H:%M:%S"),
    }


def calculate_hourly_velocity(
    df: pd.DataFrame,
    top_n_media: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Construye una serie de tiempo continua por hora para:
    1. El volumen global hora a hora con cálculo de umbral de picos ("Breaking News").
    2. La distribución hora a hora para los Top N medios.
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    con = duckdb.connect()
    try:
        con.register("df_raw", df)

        # 1. Serie global por hora
        query_global = """
        WITH Bounds AS (
            SELECT MIN(date) AS min_d, MAX(date) AS max_d
            FROM df_raw
        ),
        TimeSeries AS (
            SELECT generate_series AS hour_bucket
            FROM generate_series(
                (SELECT date_trunc('hour', min_d) FROM Bounds),
                (SELECT date_trunc('hour', max_d) FROM Bounds),
                INTERVAL '1 hour'
            )
        ),
        HourlyCounts AS (
            SELECT 
                date_trunc('hour', date) AS hour_bucket,
                COUNT(id) AS news_count
            FROM df_raw
            GROUP BY hour_bucket
        )
        SELECT 
            t.hour_bucket,
            COALESCE(h.news_count, 0) AS news_count
        FROM TimeSeries t
        LEFT JOIN HourlyCounts h ON t.hour_bucket = h.hour_bucket
        ORDER BY t.hour_bucket ASC;
        """
        df_hourly_overall = con.sql(query_global).fetchdf()

        # Detección de picos (alerta temprana)
        mean_vel = df_hourly_overall["news_count"].mean()
        std_vel = df_hourly_overall["news_count"].std()
        peak_threshold = max(mean_vel + (2.0 * std_vel), 10.0)

        df_hourly_overall["is_peak"] = df_hourly_overall["news_count"] >= peak_threshold
        df_hourly_overall["peak_threshold"] = round(peak_threshold, 1)

        # 2. Serie para los Top N medios
        query_top_media = f"""
        WITH Bounds AS (
            SELECT MIN(date) AS min_d, MAX(date) AS max_d
            FROM df_raw
        ),
        TimeSeries AS (
            SELECT generate_series AS hour_bucket
            FROM generate_series(
                (SELECT date_trunc('hour', min_d) FROM Bounds),
                (SELECT date_trunc('hour', max_d) FROM Bounds),
                INTERVAL '1 hour'
            )
        ),
        TopMedia AS (
            SELECT media_name, COUNT(*) AS total_news
            FROM df_raw
            WHERE media_name IS NOT NULL AND media_name != 'Desconocido'
            GROUP BY media_name
            ORDER BY total_news DESC
            LIMIT {top_n_media}
        ),
        BaseGrid AS (
            SELECT t.hour_bucket, m.media_name
            FROM TimeSeries t
            CROSS JOIN TopMedia m
        ),
        ActualCounts AS (
            SELECT 
                date_trunc('hour', date) AS hour_bucket,
                media_name,
                COUNT(id) AS news_count
            FROM df_raw
            GROUP BY hour_bucket, media_name
        )
        SELECT 
            g.hour_bucket,
            g.media_name,
            COALESCE(a.news_count, 0) AS news_count
        FROM BaseGrid g
        LEFT JOIN ActualCounts a 
               ON g.hour_bucket = a.hour_bucket 
              AND g.media_name = a.media_name
        ORDER BY 
            g.media_name, 
            g.hour_bucket ASC;
        """
        df_hourly_top = con.sql(query_top_media).fetchdf()

        return df_hourly_overall, df_hourly_top
    finally:
        con.close()


def calculate_syndication(
    df: pd.DataFrame,
    threshold: float = 0.85,
    num_perm: int = 64,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Rastrea noticias duplicadas o sindicadas (cables de agencia reproducidos entre medios)
    utilizando MinHash y MinHashLSH sobre trigramas de texto.
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    df_sorted = df.sort_values("date").reset_index(drop=True)
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)

    is_syndicated = []
    matched_sources = []

    for _, row in df_sorted.iterrows():
        trigrams = _extract_trigrams(row.get("body", ""))
        m = MinHash(num_perm=num_perm)
        for tg in trigrams:
            m.update(tg.encode("utf-8"))

        matches = lsh.query(m)
        if matches:
            is_syndicated.append(True)
            matched_sources.append(matches[0])
        else:
            is_syndicated.append(False)
            matched_sources.append(None)
            lsh.insert(f"{row['id']}|{row['media_name']}", m)

    df_articles = df_sorted[["id", "media_name", "date", "url"]].copy()
    df_articles["is_syndicated"] = is_syndicated
    df_articles["original_source"] = matched_sources

    # Agrupación por medio
    media_agg = (
        df_articles.groupby("media_name")
        .agg(
            total_articles=("id", "count"),
            syndicated_articles=("is_syndicated", "sum"),
        )
        .reset_index()
    )
    media_agg["syndication_rate_pct"] = round(
        (media_agg["syndicated_articles"] / media_agg["total_articles"]) * 100.0, 2
    )
    media_agg = media_agg.sort_values("total_articles", ascending=False).reset_index(drop=True)

    return df_articles, media_agg


def calculate_length_anomalies(
    df: pd.DataFrame,
    p_low: float = 0.01,
    p_high: float = 0.99,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """
    Identifica anomalías en la extensión de las noticias:
    - Percentil 1%: Cables ultracortos o posibles errores de scraping.
    - Percentil 99%: Reportajes de investigación exhaustivos o compilaciones.
    """
    if df.empty:
        return pd.DataFrame(), {"p_low": 0.0, "p_high": 0.0}

    lengths = df["body"].astype(str).str.len()
    p_low_val = float(lengths.quantile(p_low))
    p_high_val = float(lengths.quantile(p_high))

    is_short = lengths <= p_low_val
    is_long = lengths >= p_high_val

    df_anom = df.loc[is_short | is_long, ["id", "media_name", "date", "url"]].copy()
    df_anom["char_length"] = lengths.loc[is_short | is_long]
    df_anom["anomaly_type"] = np.where(
        df_anom["char_length"] <= p_low_val, "ultra_short", "ultra_long"
    )
    df_anom = df_anom.sort_values("char_length", ascending=True).reset_index(drop=True)

    return df_anom, {"p_low_threshold": p_low_val, "p_high_threshold": p_high_val}


def process_pulse(
    df: pd.DataFrame | None = None,
    country: str = "chile",
    days: int = 7,
) -> dict[str, Any]:
    """
    Función orquestadora principal del Módulo 1.
    Ejecuta todos los cálculos y exporta los datasets a data/dashboard/.
    """
    if df is None:
        df = extract_news(country=country, days=days)

    # 1. Volumen y Deltas
    kpis = calculate_volume_and_deltas(df)

    # 2. Velocidad Informativa Horaria
    df_hourly_overall, df_hourly_top = calculate_hourly_velocity(df)

    # 3. MinHash Syndication Tracker
    df_syndicated_articles, df_syndication_media = calculate_syndication(df)
    kpis["syndication_rate_pct"] = round(
        (df_syndicated_articles["is_syndicated"].mean() * 100.0), 2
    )
    kpis["syndicated_articles_count"] = int(df_syndicated_articles["is_syndicated"].sum())

    # 4. Anomalías de Longitud
    df_anomalies, length_thresholds = calculate_length_anomalies(df)
    kpis["short_anomalies_count"] = int((df_anomalies["anomaly_type"] == "ultra_short").sum())
    kpis["long_anomalies_count"] = int((df_anomalies["anomaly_type"] == "ultra_long").sum())
    kpis["p01_char_threshold"] = length_thresholds["p_low_threshold"]
    kpis["p99_char_threshold"] = length_thresholds["p_high_threshold"]

    # Exportar a data/dashboard/
    df_kpis = pd.DataFrame([kpis])
    df_kpis.to_parquet(DASHBOARD_DIR / "pulse_kpis.parquet", index=False)
    df_hourly_overall.to_parquet(DASHBOARD_DIR / "pulse_hourly_velocity.parquet", index=False)
    df_hourly_top.to_parquet(DASHBOARD_DIR / "pulse_hourly_top_media.parquet", index=False)
    df_syndication_media.to_parquet(DASHBOARD_DIR / "pulse_syndication_by_media.parquet", index=False)
    df_anomalies.to_parquet(DASHBOARD_DIR / "pulse_length_anomalies.parquet", index=False)

    # Registrar checkpoint
    record_module_run(
        country=country,
        module_name="pulse",
        status="success",
        records_processed=len(df),
        metadata={
            "recent_24h_volume": kpis["recent_24h_volume"],
            "delta_24h_pct": kpis["delta_24h_pct"],
            "syndication_rate_pct": kpis["syndication_rate_pct"],
            "peak_hours_detected": int(df_hourly_overall["is_peak"].sum()),
        },
    )

    return {
        "kpis": kpis,
        "hourly_overall": df_hourly_overall,
        "hourly_top_media": df_hourly_top,
        "syndication_media": df_syndication_media,
        "anomalies": df_anomalies,
    }
