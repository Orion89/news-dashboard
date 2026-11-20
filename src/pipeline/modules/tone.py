"""
Módulo 2: Contenido y Encuadre ("El Tono" - Análisis Semántico).
Calcula:
1. Termómetro de Emociones: Inferencia con PySentimiento (RoBERTuito) con caché persistente por body_hash.
2. El Péndulo Temporal: Balance semántico entre orientación al Pasado vs. Futuro (Gauge / Balanza).
3. Índice de Sensacionalismo: Cruce de intensidad emocional (ira/miedo), adjetivación morfológica (POS) y signos/mayúsculas.
4. N-gramas Emergentes: Bigramas y trigramas más dinámicos comparando ventana reciente vs. ventana base.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timedelta
from typing import Any
import numpy as np
import pandas as pd
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

from src.pipeline.config import CACHE_DIR, DASHBOARD_DIR
from src.pipeline.db import extract_news
from src.pipeline.state import record_module_run

EMOTIONS_CACHE_FILE = CACHE_DIR / "emotions_cache.parquet"

# Diccionarios semánticos para el Péndulo Temporal (Pasado vs. Futuro)
TERMINOS_PASADO_RE = re.compile(
    r"\b("
    r"historia|histórico|histórica|históricos|históricas|memoria|recuerdo|recordar|"
    r"antaño|nostalgia|tradición|tradicional|legado|orígenes|patrimonio|conmemoración|"
    r"aniversario|homenaje|retrospectiva|ayer|anoche|antier|anteayer|pasado|pasada|"
    r"pasados|pasadas|anterior|anteriores|antiguo|antigua|antiguos|antiguas|décadas|"
    r"siglo|época|antiguamente|previamente|ocurrió|sucedió|pasó|fue|fueron|estuvo|"
    r"estuvieron|hizo|hicieron|hubo|dijo|afirmó|señaló"
    r")\b",
    re.IGNORECASE,
)

TERMINOS_FUTURO_RE = re.compile(
    r"\b("
    r"futuro|futura|futuros|futuras|proyecto|proyectos|promesa|promesas|meta|metas|"
    r"plan|planes|proyección|proyecciones|desafío|desafíos|expectativa|expectativas|"
    r"innovación|innovaciones|modernización|transformación|mañana|próximo|próxima|"
    r"próximos|próximas|adelante|posterior|posteriormente|pronto|eventual|eventualmente|"
    r"será|serán|habrá|hará|harán|estará|estarán|deberá|deberán|podría|podrían|"
    r"espera|esperan|prevé|prevén|proyecta|proyectan"
    r")\b",
    re.IGNORECASE,
)

WORD_CLEAN_RE = re.compile(r"^[a-záéíóúñü]+$", re.IGNORECASE)


def extract_emotions_with_cache(
    df: pd.DataFrame,
    max_chars: int = 400,
    batch_size: int = 256,
    limit: int | None = None,
) -> pd.DataFrame:
    """
    Infiere emociones (miedo, ira, tristeza, alegría, sorpresa, asco, otros)
    utilizando PySentimiento con caché permanente indexada por body_hash.
    """
    if df.empty:
        return pd.DataFrame()

    df_target = df.copy()
    if limit is not None and limit > 0:
        df_target = df_target.head(limit).copy()

    # Cargar caché existente si está disponible
    df_cached = pd.DataFrame()
    cached_hashes = set()
    if EMOTIONS_CACHE_FILE.exists():
        try:
            df_cached = pd.read_parquet(EMOTIONS_CACHE_FILE)
            cached_hashes = set(df_cached["body_hash"].dropna())
        except Exception:
            df_cached = pd.DataFrame()
            cached_hashes = set()

    # Identificar registros pendientes
    df_pending = df_target[~df_target["body_hash"].isin(cached_hashes)].copy()

    new_records = []
    if not df_pending.empty:
        # Carga perezosa del modelo para optimizar memoria
        from pysentimiento import create_analyzer

        analyzer = create_analyzer(task="emotion", lang="es")
        pending_texts = df_pending["body"].astype(str).str.slice(0, max_chars).tolist()
        pending_hashes = df_pending["body_hash"].tolist()
        pending_ids = df_pending["id"].tolist()

        n_batches = math.ceil(len(pending_texts) / batch_size)
        for i in range(n_batches):
            batch_slice = slice(i * batch_size, (i + 1) * batch_size)
            b_texts = pending_texts[batch_slice]
            b_hashes = pending_hashes[batch_slice]
            b_ids = pending_ids[batch_slice]

            outputs = analyzer.predict(b_texts)
            for out, h, item_id in zip(outputs, b_hashes, b_ids):
                p = out.probas
                new_records.append({
                    "id": item_id,
                    "body_hash": h,
                    "miedo": float(p.get("fear", 0.0)),
                    "ira": float(p.get("anger", 0.0)),
                    "tristeza": float(p.get("sadness", 0.0)),
                    "alegria": float(p.get("joy", 0.0)),
                    "sorpresa": float(p.get("surprise", 0.0)),
                    "asco": float(p.get("disgust", 0.0)),
                    "otros": float(p.get("others", 0.0)),
                })

        # Actualizar archivo de caché persistente de forma atómica
        df_new = pd.DataFrame(new_records)
        if not df_cached.empty:
            df_combined = pd.concat([df_cached, df_new], ignore_index=True)
            df_combined = df_combined.drop_duplicates(subset=["body_hash"]).reset_index(drop=True)
        else:
            df_combined = df_new

        df_combined.to_parquet(EMOTIONS_CACHE_FILE, index=False, engine="pyarrow")
        df_cached = df_combined

    # Unir resultados al dataframe objetivo
    df_merged = df_target.merge(df_cached, on="body_hash", how="left", suffixes=("", "_cache"))
    if "id_cache" in df_merged.columns:
        df_merged = df_merged.drop(columns=["id_cache"])

    return df_merged


def calculate_temporal_pendulum(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Calcula la orientación temporal de las noticias (Pasado vs. Futuro):
    Balance = (Futuro - Pasado) / (Futuro + Pasado) * 100 (-100 a +100)
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    bodies = df["body"].astype(str).tolist()
    past_counts = [len(TERMINOS_PASADO_RE.findall(t)) for t in bodies]
    future_counts = [len(TERMINOS_FUTURO_RE.findall(t)) for t in bodies]

    df_pen = df[["id", "media_name", "date"]].copy()
    df_pen["past_mentions"] = past_counts
    df_pen["future_mentions"] = future_counts

    total_menc = df_pen["past_mentions"] + df_pen["future_mentions"]
    df_pen["pendulum_score"] = np.where(
        total_menc > 0,
        ((df_pen["future_mentions"] - df_pen["past_mentions"]) / total_menc) * 100.0,
        0.0,
    )
    df_pen["pendulum_score"] = df_pen["pendulum_score"].round(2)

    # Agregado diario por medio
    df_pen["date_day"] = pd.to_datetime(df_pen["date"]).dt.floor("D")
    daily_summary = (
        df_pen.groupby(["date_day", "media_name"])
        .agg(
            total_past=("past_mentions", "sum"),
            total_future=("future_mentions", "sum"),
            articles_count=("id", "count"),
        )
        .reset_index()
    )
    total_daily_menc = daily_summary["total_past"] + daily_summary["total_future"]
    daily_summary["daily_pendulum_score"] = np.where(
        total_daily_menc > 0,
        ((daily_summary["total_future"] - daily_summary["total_past"]) / total_daily_menc) * 100.0,
        0.0,
    ).round(2)

    return df_pen, daily_summary


def calculate_sensationalism_index(
    df_with_emotions: pd.DataFrame,
    top_n_media: int = 20,
) -> pd.DataFrame:
    """
    Calcula el Índice de Sensacionalismo cruzando:
    1. Intensidad Emocional: Peso de la indignación y el pánico (ira + miedo).
    2. Densidad Morfológica: Proporción de adjetivos en el texto.
    3. Estilo / Formato: Proporción de mayúsculas y uso de signos de exclamación.
    """
    if df_with_emotions.empty:
        return pd.DataFrame()

    df_calc = df_with_emotions.copy()
    texts = df_calc["body"].astype(str)

    # 1. Dimensión Estilo y Formato
    # Exclamaciones e interrogaciones
    punct_count = texts.apply(lambda t: t.count("!") + t.count("?") + t.count("¡") + t.count("¿"))
    upper_ratios = texts.apply(
        lambda t: (sum(1 for c in t if c.isupper()) / max(len(t), 1))
    )

    # 2. Dimensión Morfológica Rápida (Heurística o POS)
    # Proporción de palabras adjetivadas comunes o sufijos (-oso, -ivo, -al, etc.)
    adj_re = re.compile(r"\b[a-záéíóúñü]+(oso|osa|ible|able|ivo|iva|ado|ada|ante|ente|ual|ial)\b", re.IGNORECASE)
    adj_counts = texts.apply(lambda t: len(adj_re.findall(t[:1500])))
    word_counts = texts.apply(lambda t: max(len(t[:1500].split()), 1))
    adj_density = (adj_counts / word_counts).clip(0.0, 0.5)

    # 3. Dimensión Emocional (Ira + Miedo)
    ira = df_calc.get("ira", pd.Series(0.0, index=df_calc.index)).fillna(0.0)
    miedo = df_calc.get("miedo", pd.Series(0.0, index=df_calc.index)).fillna(0.0)
    emotion_intensity = ((ira * 0.55) + (miedo * 0.45)).clip(0.0, 1.0)

    # Normalización Min-Max por componente (0 a 100)
    style_score = ((upper_ratios * 300.0) + (punct_count * 2.0)).clip(0.0, 100.0)
    morph_score = (adj_density * 300.0).clip(0.0, 100.0)
    emo_score = (emotion_intensity * 100.0).clip(0.0, 100.0)

    # Fórmula ponderada del Índice de Sensacionalismo
    sensationalism = (0.45 * emo_score) + (0.30 * morph_score) + (0.25 * style_score)
    df_calc["sensationalism_score"] = sensationalism.round(2)
    df_calc["emotion_intensity"] = emo_score.round(2)
    df_calc["morph_intensity"] = morph_score.round(2)
    df_calc["style_intensity"] = style_score.round(2)

    # Ranking por medio
    media_ranking = (
        df_calc.groupby("media_name")
        .agg(
            articles_count=("id", "count"),
            avg_sensationalism=("sensationalism_score", "mean"),
            avg_emotion=("emotion_intensity", "mean"),
            avg_adjectives=("morph_intensity", "mean"),
            avg_style=("style_intensity", "mean"),
        )
        .reset_index()
    )

    # Filtrar medios con mínimo 10 artículos para evitar sesgo de muestras diminutas
    media_ranking = media_ranking[media_ranking["articles_count"] >= 10].copy()
    media_ranking["avg_sensationalism"] = media_ranking["avg_sensationalism"].round(2)
    media_ranking = media_ranking.sort_values("avg_sensationalism", ascending=False).head(top_n_media).reset_index(drop=True)
    media_ranking["rank"] = media_ranking.index + 1

    return media_ranking


def calculate_emerging_ngrams(
    df: pd.DataFrame,
    recent_hours: int = 36,
    top_k: int = 30,
) -> pd.DataFrame:
    """
    Detecta Trending Topics y N-gramas emergentes comparando
    la frecuencia en las últimas horas contra la frecuencia en la ventana previa.
    """
    if df.empty:
        return pd.DataFrame()

    latest_date = df["date"].max()
    threshold_t = latest_date - timedelta(hours=recent_hours)

    recent_df = df[df["date"] >= threshold_t]
    baseline_df = df[df["date"] < threshold_t]

    stop_words_es = set(stopwords.words("spanish"))

    def get_ngrams_counter(df_subset: pd.DataFrame) -> Counter:
        counts = Counter()
        for body in df_subset["body"].dropna():
            words = [
                w.lower() for w in word_tokenize(str(body)[:1200])
                if WORD_CLEAN_RE.match(w) and w.lower() not in stop_words_es and len(w) > 2
            ]
            # Bigramas
            for i in range(len(words) - 1):
                counts[" ".join(words[i : i + 2])] += 1
            # Trigramas
            for i in range(len(words) - 2):
                counts[" ".join(words[i : i + 3])] += 1
        return counts

    recent_counts = get_ngrams_counter(recent_df)
    base_counts = get_ngrams_counter(baseline_df)

    recent_total = max(sum(recent_counts.values()), 1)
    base_total = max(sum(base_counts.values()), 1)

    records = []
    for ngram, r_freq in recent_counts.most_common(top_k * 3):
        if r_freq < 5:
            continue
        b_freq = base_counts.get(ngram, 0)
        r_rate = (r_freq / recent_total) * 10000.0
        b_rate = (b_freq / base_total) * 10000.0

        growth = round((r_rate / max(b_rate, 0.1)), 2)
        records.append({
            "ngram": ngram,
            "ngram_type": "bigrama" if len(ngram.split()) == 2 else "trigrama",
            "recent_count": r_freq,
            "baseline_count": b_freq,
            "growth_ratio": growth,
        })

    df_ngrams = pd.DataFrame(records).sort_values(["growth_ratio", "recent_count"], ascending=[False, False]).head(top_k).reset_index(drop=True)
    return df_ngrams


def process_tone(
    df: pd.DataFrame | None = None,
    country: str = "chile",
    days: int = 7,
    limit_emotions: int | None = None,
) -> dict[str, Any]:
    """
    Función orquestadora principal del Módulo 2.
    Ejecuta el análisis de emociones, péndulo temporal, sensacionalismo y n-gramas,
    exportando los datasets consolidados a data/dashboard/.
    """
    if df is None:
        df = extract_news(country=country, days=days)

    # 1. Inferencia de Emociones con Caché Incremental
    df_with_emotions = extract_emotions_with_cache(df, limit=limit_emotions)

    # Serie temporal agregada de emociones
    df_clean_dates = df_with_emotions.dropna(subset=["date", "media_name"]).copy()
    df_clean_dates["date_day"] = pd.to_datetime(df_clean_dates["date"]).dt.floor("D")

    emotion_cols = ["miedo", "ira", "tristeza", "alegria", "sorpresa", "asco"]
    available_emotions = [c for c in emotion_cols if c in df_clean_dates.columns]

    daily_emotions = (
        df_clean_dates.groupby(["date_day", "media_name"])[available_emotions]
        .mean()
        .reset_index()
    )
    daily_emotions_tidy = daily_emotions.melt(
        id_vars=["date_day", "media_name"],
        value_vars=available_emotions,
        var_name="emotion",
        value_name="intensity",
    ).sort_values(["media_name", "date_day", "emotion"]).reset_index(drop=True)

    # 2. Péndulo Temporal
    df_pendulum_articles, df_pendulum_daily = calculate_temporal_pendulum(df)

    # 3. Índice de Sensacionalismo
    df_sensationalism_ranking = calculate_sensationalism_index(df_with_emotions)

    # 4. N-gramas Emergentes
    df_emerging_ngrams = calculate_emerging_ngrams(df)

    # Exportar a data/dashboard/
    daily_emotions_tidy.to_parquet(DASHBOARD_DIR / "tone_emotions_timeseries.parquet", index=False)
    df_pendulum_daily.to_parquet(DASHBOARD_DIR / "tone_pendulum_daily.parquet", index=False)
    df_sensationalism_ranking.to_parquet(DASHBOARD_DIR / "tone_sensationalism_ranking.parquet", index=False)
    df_emerging_ngrams.to_parquet(DASHBOARD_DIR / "tone_emerging_ngrams.parquet", index=False)

    # Registrar checkpoint
    record_module_run(
        country=country,
        module_name="tone",
        status="success",
        records_processed=len(df),
        metadata={
            "emotions_processed": len(df_with_emotions),
            "media_ranked_sensationalism": len(df_sensationalism_ranking),
            "emerging_ngrams_count": len(df_emerging_ngrams),
        },
    )

    return {
        "emotions_timeseries": daily_emotions_tidy,
        "pendulum_daily": df_pendulum_daily,
        "sensationalism_ranking": df_sensationalism_ranking,
        "emerging_ngrams": df_emerging_ngrams,
    }
