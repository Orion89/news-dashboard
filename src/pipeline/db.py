"""
Conector DuckDB a PostgreSQL y funciones de extracción sanitizada y cacheada.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import duckdb
import pandas as pd

from .config import (
    AVAILABLE_COUNTRIES,
    MIN_VALID_YEAR,
    POSTGRES_URI,
    RAW_CACHE_DIR,
)
from .state import record_module_run


def get_duckdb_connection(uri: str | None = None) -> duckdb.DuckDBPyConnection:
    """
    Inicializa una conexión de DuckDB y acopla la base de datos PostgreSQL en modo READ_ONLY.
    """
    target_uri = uri or POSTGRES_URI
    con = duckdb.connect()
    con.sql("INSTALL postgres;")
    con.sql("LOAD postgres;")
    con.sql(f"ATTACH '{target_uri}' AS news_db (TYPE postgres, READ_ONLY);")
    return con


def get_latest_valid_date(con: duckdb.DuckDBPyConnection, table_name: str) -> str:
    """
    Obtiene la fecha más reciente válida de la tabla (descartando fechas anómalas en el futuro).
    """
    query = f"""
        SELECT MAX(date) AS max_date
        FROM news_db.{table_name}
        WHERE date <= CURRENT_TIMESTAMP
          AND date >= '{MIN_VALID_YEAR}-01-01'
    """
    res = con.sql(query).fetchone()
    if not res or res[0] is None:
        raise ValueError(f"No se encontraron fechas válidas en la tabla {table_name}")
    
    # Formatear como ISO string
    val = res[0]
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M:%S")
    return str(val)


def extract_news(
    country: str = "chile",
    days: int = 7,
    force_refresh: bool = False,
    anchor_date: str | None = None,
) -> pd.DataFrame:
    """
    Extrae noticias sanitizadas de la base de datos para un país y ventana de días dada.
    Usa caché en Parquet en data/raw_cache/ para evitar re-consultar la base local en cada ejecución.
    """
    country_key = country.lower().strip()
    if country_key not in AVAILABLE_COUNTRIES:
        raise KeyError(
            f"País '{country}' no reconocido. Opciones: {list(AVAILABLE_COUNTRIES.keys())}"
        )

    table_name = AVAILABLE_COUNTRIES[country_key]
    cache_file = RAW_CACHE_DIR / f"{country_key}_{days}d.parquet"

    # Retornar caché si existe y no se solicita refresco forzado
    if cache_file.exists() and not force_refresh:
        df_cached = pd.read_parquet(cache_file)
        return df_cached

    # Conectar y extraer
    con = get_duckdb_connection()
    try:
        effective_anchor = anchor_date or get_latest_valid_date(con, table_name)

        query = f"""
            SELECT 
                id,
                media_name,
                url,
                date,
                author,
                body,
                body_hash
            FROM news_db.{table_name}
            WHERE date <= '{effective_anchor}'::TIMESTAMP
              AND date >= '{effective_anchor}'::TIMESTAMP - INTERVAL '{days} days'
              AND date >= '{MIN_VALID_YEAR}-01-01'::TIMESTAMP
              AND body IS NOT NULL
              AND length(trim(body)) > 0
              AND body_hash IS NOT NULL
            ORDER BY date ASC
        """
        df = con.sql(query).fetchdf()

        # Deduplicar por body_hash por consistencia estricta
        df = df.drop_duplicates(subset=["body_hash"]).reset_index(drop=True)

        # Normalizar nombres de columnas y formatos de texto
        df["media_name"] = df["media_name"].fillna("Desconocido").str.strip()
        df["date"] = pd.to_datetime(df["date"])

        # Guardar en caché Parquet
        df.to_parquet(cache_file, index=False, engine="pyarrow", compression="snappy")

        # Registrar estado de extracción
        record_module_run(
            country=country_key,
            module_name="raw_extraction",
            status="success",
            records_processed=len(df),
            metadata={
                "days": days,
                "anchor_date": effective_anchor,
                "cache_file": str(cache_file.name),
                "columns": list(df.columns),
            },
        )

        return df
    finally:
        con.close()
