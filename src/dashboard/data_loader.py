"""
Cargador de datos y proveedor en memoria para el frontend en Plotly Dash.
Carga los 19 datasets precalculados en data/dashboard/ y expone funciones de filtrado rápido.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import pandas as pd

from src.dashboard.config import DASHBOARD_DATA_DIR

# Caché en memoria para evitar lecturas de disco redundantes en cada callback
_DATA_CACHE: dict[str, Any] = {}


def _read_parquet_safe(filename: str) -> pd.DataFrame:
    """Lee un archivo parquet desde DASHBOARD_DATA_DIR o retorna DataFrame vacío si no existe."""
    if filename in _DATA_CACHE:
        return _DATA_CACHE[filename].copy()

    filepath = DASHBOARD_DATA_DIR / filename
    if not filepath.exists():
        return pd.DataFrame()

    try:
        df = pd.read_parquet(filepath)
        _DATA_CACHE[filename] = df
        return df.copy()
    except Exception:
        return pd.DataFrame()


def _read_json_safe(filename: str) -> dict[str, Any]:
    """Lee un archivo JSON desde DASHBOARD_DATA_DIR o retorna dict vacío si no existe."""
    if filename in _DATA_CACHE:
        return _DATA_CACHE[filename]

    filepath = DASHBOARD_DATA_DIR / filename
    if not filepath.exists():
        return {}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        _DATA_CACHE[filename] = data
        return data
    except Exception:
        return {}


def clear_cache() -> None:
    """Limpia la caché en memoria (útil tras refrescar el pipeline de datos)."""
    _DATA_CACHE.clear()


# ==============================================================================
# 0. Manifiesto y Metadatos
# ==============================================================================
def load_manifest() -> dict[str, Any]:
    return _read_json_safe("data_manifest.json")


def get_available_media_list() -> list[str]:
    """Retorna la lista ordenada de medios de comunicación disponibles en los datasets."""
    df_sources = _read_parquet_safe("quality_sources_health.parquet")
    if not df_sources.empty and "media_name" in df_sources.columns:
        valid_media = (
            df_sources["media_name"]
            .dropna()
            .loc[lambda m: m != "Desconocido"]
            .unique()
            .tolist()
        )
        return sorted(valid_media)
    return []


# ==============================================================================
# 1. Datasets de Módulo 1: El Pulso
# ==============================================================================
def load_pulse_kpis() -> dict[str, Any]:
    df = _read_parquet_safe("pulse_kpis.parquet")
    if not df.empty:
        return df.iloc[0].to_dict()
    return {}


def load_hourly_velocity() -> pd.DataFrame:
    return _read_parquet_safe("pulse_hourly_velocity.parquet")


def load_hourly_top_media() -> pd.DataFrame:
    return _read_parquet_safe("pulse_hourly_top_media.parquet")


def load_syndication_media() -> pd.DataFrame:
    return _read_parquet_safe("pulse_syndication_by_media.parquet")


def load_length_anomalies() -> pd.DataFrame:
    return _read_parquet_safe("pulse_length_anomalies.parquet")


# ==============================================================================
# 2. Datasets de Módulo 5: Calidad de Datos
# ==============================================================================
def load_quality_corpus_integrity() -> pd.DataFrame:
    return _read_parquet_safe("quality_corpus_integrity.parquet")


def load_quality_sources_health() -> pd.DataFrame:
    return _read_parquet_safe("quality_sources_health.parquet")


def load_quality_summary() -> dict[str, Any]:
    df = _read_parquet_safe("quality_summary.parquet")
    if not df.empty:
        return df.iloc[0].to_dict()
    return {}


# ==============================================================================
# 3. Datasets de Módulo 3: Autoría y Complejidad
# ==============================================================================
def load_authorship_sankey() -> dict[str, Any]:
    return _read_json_safe("authorship_sankey.json")


def load_authorship_gender_kpis() -> dict[str, Any]:
    df = _read_parquet_safe("authorship_gender_kpis.parquet")
    if not df.empty:
        return df.iloc[0].to_dict()
    return {}


def load_authorship_media_stats() -> pd.DataFrame:
    return _read_parquet_safe("authorship_media_stats.parquet")


def load_authorship_readability() -> pd.DataFrame:
    return _read_parquet_safe("authorship_readability.parquet")


def load_authorship_pos_distribution() -> pd.DataFrame:
    return _read_parquet_safe("authorship_pos_distribution.parquet")


# ==============================================================================
# 4. Datasets de Módulo 2: El Tono
# ==============================================================================
def load_tone_emotions_timeseries() -> pd.DataFrame:
    return _read_parquet_safe("tone_emotions_timeseries.parquet")


def load_tone_pendulum_daily() -> pd.DataFrame:
    return _read_parquet_safe("tone_pendulum_daily.parquet")


def load_tone_sensationalism_ranking() -> pd.DataFrame:
    return _read_parquet_safe("tone_sensationalism_ranking.parquet")


def load_tone_emerging_ngrams() -> pd.DataFrame:
    return _read_parquet_safe("tone_emerging_ngrams.parquet")


# ==============================================================================
# 5. Datasets de Módulo 4: Geopolítico
# ==============================================================================
def load_geopolitics_protagonists() -> pd.DataFrame:
    return _read_parquet_safe("geopolitics_protagonists.parquet")


def load_geopolitics_locations() -> pd.DataFrame:
    return _read_parquet_safe("geopolitics_locations.parquet")


# ==============================================================================
# Helper de filtrado por medio
# ==============================================================================
def filter_by_media(df: pd.DataFrame, media_name: str | None) -> pd.DataFrame:
    """Filtra un DataFrame por media_name si se especifica un medio puntual."""
    if df.empty or not media_name or media_name == "ALL" or "media_name" not in df.columns:
        return df
    return df[df["media_name"] == media_name].copy()
