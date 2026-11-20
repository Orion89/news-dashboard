"""
Módulo 4: Geopolítico ("De Quién y Dónde se Habla").
Calcula:
1. Extracción de Entidades Nombradas (NER: PER, ORG, LOC) mediante spaCy (es_core_news_lg) con caché por body_hash.
2. Mapa de Calor Geográfico: Geolocalización de entidades LOC con catálogo regional y caché persistente.
3. Radar de Protagonistas: Figuras públicas (PER) y organizaciones (ORG) más mencionadas.
"""
from __future__ import annotations

import json
from collections import Counter
from typing import Any
import numpy as np
import pandas as pd
import spacy

from src.pipeline.config import CACHE_DIR, DASHBOARD_DIR
from src.pipeline.db import extract_news
from src.pipeline.state import record_module_run

NER_CACHE_FILE = CACHE_DIR / "ner_cache.parquet"
GEO_CACHE_FILE = CACHE_DIR / "geo_cache.json"

STOP_ENTITIES = {
    "El", "La", "Los", "Las", "Un", "Una", "Unos", "Unas", "Este", "Esta",
    "Gobierno", "Estado", "País", "Año", "Hoy", "Ayer", "Mañana", "Semana",
    "Mes", "Mundo", "Nacional", "Internacional", "Región", "Ciudad", "Noticias",
    "Chile", "Santiago De Chile", "Twitter", "Facebook", "Instagram", "Youtube"
}

# Coordenadas de referencia de las principales ciudades y regiones de Chile
CHILE_LOC_COORDINATES: dict[str, tuple[float, float, str]] = {
    "Santiago": (-33.4489, -70.6693, "Región Metropolitana"),
    "Valparaíso": (-33.0472, -71.6127, "Región de Valparaíso"),
    "Viña Del Mar": (-33.0245, -71.5518, "Región de Valparaíso"),
    "Concepción": (-36.8270, -73.0503, "Región del Biobío"),
    "Antofagasta": (-23.6509, -70.3975, "Región de Antofagasta"),
    "Temuco": (-38.7359, -72.5904, "Región de La Araucanía"),
    "La Serena": (-29.9027, -71.2519, "Región de Coquimbo"),
    "Coquimbo": (-29.9533, -71.3436, "Región de Coquimbo"),
    "Iquique": (-20.2307, -70.1357, "Región de Tarapacá"),
    "Arica": (-18.4783, -70.3126, "Región de Arica y Parinacota"),
    "Rancagua": (-34.1708, -70.7444, "Región de O'Higgins"),
    "Talca": (-35.4264, -71.6554, "Región del Maule"),
    "Chillán": (-36.6066, -72.1034, "Región de Ñuble"),
    "Puerto Montt": (-41.4693, -72.9424, "Región de Los Lagos"),
    "Valdivia": (-39.8142, -73.2459, "Región de Los Ríos"),
    "Osorno": (-40.5739, -73.1335, "Región de Los Lagos"),
    "Coyhaique": (-45.5752, -72.0662, "Región de Aysén"),
    "Punta Arenas": (-53.1638, -70.9171, "Región de Magallanes"),
    "Calama": (-22.4544, -68.9294, "Región de Antofagasta"),
    "Copiapó": (-27.3668, -70.3323, "Región de Atacama"),
    "Quilpué": (-33.0489, -71.4428, "Región de Valparaíso"),
    "Curicó": (-34.9828, -71.2394, "Región del Maule"),
    "Los Ángeles": (-37.4697, -72.3537, "Región del Biobío"),
}


def extract_ner_with_cache(
    df: pd.DataFrame,
    max_chars: int = 1000,
    batch_size: int = 256,
    limit: int | None = None,
) -> pd.DataFrame:
    """
    Extrae entidades nombradas (PER, ORG, LOC) de los leads de noticias utilizando spaCy
    con persistencia incremental por body_hash en Parquet.
    """
    if df.empty:
        return pd.DataFrame()

    df_target = df.copy()
    if limit is not None and limit > 0:
        df_target = df_target.head(limit).copy()

    # Cargar caché existente
    df_cached = pd.DataFrame()
    cached_hashes = set()
    if NER_CACHE_FILE.exists():
        try:
            df_cached = pd.read_parquet(NER_CACHE_FILE)
            cached_hashes = set(df_cached["body_hash"].dropna())
        except Exception:
            df_cached = pd.DataFrame()
            cached_hashes = set()

    df_pending = df_target[~df_target["body_hash"].isin(cached_hashes)].copy()

    new_records = []
    if not df_pending.empty:
        # Cargar modelo de spaCy
        try:
            nlp = spacy.load("es_core_news_lg", disable=["parser"])
        except Exception:
            nlp = spacy.load("es_core_news_sm", disable=["parser"])

        pending_texts = df_pending["body"].astype(str).str.slice(0, max_chars).tolist()
        pending_hashes = df_pending["body_hash"].tolist()
        pending_ids = df_pending["id"].tolist()
        pending_media = df_pending["media_name"].tolist()
        pending_dates = df_pending["date"].tolist()

        docs = nlp.pipe(pending_texts, batch_size=batch_size, n_process=1)

        for doc, h, item_id, media, d in zip(docs, pending_hashes, pending_ids, pending_media, pending_dates):
            ents_found = []
            for ent in doc.ents:
                ent_clean = ent.text.strip().title()
                if (
                    len(ent_clean) > 2
                    and ent_clean not in STOP_ENTITIES
                    and ent.label_ in ["PER", "ORG", "LOC"]
                ):
                    ents_found.append((ent_clean, ent.label_))

            # Serializar lista de entidades como JSON string para el DataFrame relacional
            new_records.append({
                "id": item_id,
                "body_hash": h,
                "media_name": media,
                "date": d,
                "entities_json": json.dumps(ents_found, ensure_ascii=False),
            })

        df_new = pd.DataFrame(new_records)
        if not df_cached.empty:
            df_combined = pd.concat([df_cached, df_new], ignore_index=True)
            df_combined = df_combined.drop_duplicates(subset=["body_hash"]).reset_index(drop=True)
        else:
            df_combined = df_new

        df_combined.to_parquet(NER_CACHE_FILE, index=False, engine="pyarrow")
        df_cached = df_combined

    # Unir resultados
    df_merged = df_target.merge(df_cached[["body_hash", "entities_json"]], on="body_hash", how="left")
    return df_merged


def calculate_protagonists_and_locations(
    df_with_ner: pd.DataFrame,
    country: str = "chile",
    top_k: int = 30,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Desglosa el campo entities_json para generar:
    1. Radar de Protagonistas (Top Personas y Top Organizaciones más mencionadas).
    2. Mapa de Calor Geográfico (Localidades mapeadas con latitud y longitud).
    """
    if df_with_ner.empty or "entities_json" not in df_with_ner.columns:
        return pd.DataFrame(), pd.DataFrame()

    per_counter = Counter()
    org_counter = Counter()
    loc_counter = Counter()
    media_mentions: dict[tuple[str, str], Counter] = {
        "PER": Counter(),
        "ORG": Counter(),
        "LOC": Counter(),
    }

    for _, row in df_with_ner.iterrows():
        raw_json = row.get("entities_json")
        if not raw_json or not isinstance(raw_json, str):
            continue
        try:
            ents = json.loads(raw_json)
        except Exception:
            continue

        media = row.get("media_name", "Desconocido")
        for ent_name, label in ents:
            if label == "PER":
                per_counter[ent_name] += 1
                media_mentions["PER"][(ent_name, media)] += 1
            elif label == "ORG":
                org_counter[ent_name] += 1
                media_mentions["ORG"][(ent_name, media)] += 1
            elif label == "LOC":
                loc_counter[ent_name] += 1
                media_mentions["LOC"][(ent_name, media)] += 1

    # 1. Radar de Protagonistas (PER y ORG)
    protagonists_records = []
    for ent, count in per_counter.most_common(top_k):
        protagonists_records.append({
            "entity": ent,
            "type": "Persona (PER)",
            "total_mentions": count,
            "dominant_category": "Líder / Político / Figura Pública",
        })
    for ent, count in org_counter.most_common(top_k):
        protagonists_records.append({
            "entity": ent,
            "type": "Organización (ORG)",
            "total_mentions": count,
            "dominant_category": "Institución / Empresa / Colectivo",
        })
    df_protagonists = pd.DataFrame(protagonists_records)

    # 2. Mapa de Calor Geográfico (LOC)
    loc_records = []
    for loc_name, count in loc_counter.most_common(50):
        # Búsqueda en catálogo chileno o variantes
        matched_geo = None
        for known_city, (lat, lon, region) in CHILE_LOC_COORDINATES.items():
            if known_city.lower() in loc_name.lower() or loc_name.lower() in known_city.lower():
                matched_geo = (lat, lon, region, known_city)
                break

        if matched_geo:
            lat, lon, region, standard_name = matched_geo
            loc_records.append({
                "city": standard_name,
                "raw_entity": loc_name,
                "region": region,
                "latitude": lat,
                "longitude": lon,
                "mentions": count,
                "country": country,
            })

    df_locations = (
        pd.DataFrame(loc_records)
        .groupby(["city", "region", "latitude", "longitude", "country"])
        .agg(total_mentions=("mentions", "sum"))
        .reset_index()
        .sort_values("total_mentions", ascending=False)
        .reset_index(drop=True)
    )

    return df_protagonists, df_locations


def process_geopolitics(
    df: pd.DataFrame | None = None,
    country: str = "chile",
    days: int = 7,
    limit_ner: int | None = None,
) -> dict[str, Any]:
    """
    Función orquestadora principal del Módulo 4.
    Ejecuta el pipeline NER y genera los datasets de protagonistas y geolocalización.
    """
    if df is None:
        df = extract_news(country=country, days=days)

    # 1. Extracción NER con Caché por body_hash
    df_with_ner = extract_ner_with_cache(df, limit=limit_ner)

    # 2. Protagonistas y Localidades
    df_protagonists, df_locations = calculate_protagonists_and_locations(df_with_ner, country=country)

    # Exportar a data/dashboard/
    df_protagonists.to_parquet(DASHBOARD_DIR / "geopolitics_protagonists.parquet", index=False)
    df_locations.to_parquet(DASHBOARD_DIR / "geopolitics_locations.parquet", index=False)

    # Registrar checkpoint
    record_module_run(
        country=country,
        module_name="geopolitics",
        status="success",
        records_processed=len(df),
        metadata={
            "protagonists_count": len(df_protagonists),
            "locations_mapped": len(df_locations),
        },
    )

    return {
        "protagonists": df_protagonists,
        "locations": df_locations,
    }
