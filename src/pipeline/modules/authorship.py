"""
Módulo 3: Autoría y Complejidad ("Quién Habla y Cómo").
Calcula:
1. Embudo de Responsabilidad (Diagrama de Sankey): Proporción de notas de Redacción/Anónimas vs. Agencias vs. Periodistas firmantes.
2. Diversidad de Género en Firmas: Inferencia mediante gender_guesser (Hombre vs. Mujer vs. No Identificado).
3. Monitor de Legibilidad (Índice INFLESZ y "Barrera de Cristal"): Mapeo a años de escolaridad requerida por medio.
4. Estructura del Discurso (POS Tagging): Distribución de adjetivos, sustantivos y verbos por medio.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any
import numpy as np
import pandas as pd
import pyphen
import gender_guesser.detector as gender
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk import pos_tag
from nltk.corpus import stopwords

from src.pipeline.config import DASHBOARD_DIR
from src.pipeline.db import extract_news
from src.pipeline.state import record_module_run

# Constantes de limpieza y detección heurística
AGENCIAS_SET = {
    "europa press", "reuters", "efe", "afp", "ap", "agencia", "noticias argentinas",
    "getty", "ansalatina", "telam", "bloomberg", "cnn"
}

ANONIMOS_SET = {
    "redaccion", "redacción", "admin", "editor", "staff", "colaborador",
    "diario", "prensa", "tribuna", "mercurio", "portal", "noticias",
    "digital", "comunicaciones", "equipo", "cronica", "crónica"
}

ADJ_TAGS = {"JJ", "JJR", "JJS"}
NOUN_TAGS = {"NN", "NNS", "NNP", "NNPS"}
VERB_TAGS = {"VB", "VBD", "VBG", "VBN", "VBP", "VBZ"}

WORD_PATTERN = re.compile(r"[a-záéíóúñü]+", re.IGNORECASE)


def clean_author_text(author: Any) -> str:
    """Limpia textos de autoría eliminando fragmentos HTML, prefijos y caracteres no alfabéticos."""
    if not isinstance(author, str) or not author.strip():
        return ""
    t = author.lower().strip()
    t = re.sub(r"(\.wp-block-|class|display inline|post\.author|entry-author).*", "", t)
    t = re.sub(r"(escrito por|publicado por|posted by|tema por|por favor ingrese su nombre aqu[íi]|por\s+)", "", t)
    t = re.sub(r"[^a-záéíóúñü\s]", "", t)
    return t.strip()


def categorize_author_type(clean_author: str) -> str:
    """Clasifica el autor en: Agencia, Anónimo o Firmado."""
    if not clean_author:
        return "Anónimo"
    if any(ag in clean_author for ag in AGENCIAS_SET):
        return "Agencia"
    if any(an in clean_author for an in ANONIMOS_SET):
        return "Anónimo"
    return "Firmado"


def infer_gender(clean_author: str, detector: gender.Detector) -> str:
    """Infiere el género a partir del primer nombre de pila."""
    if not clean_author:
        return "No Identificado"
    parts = clean_author.split()
    first_name = parts[0].capitalize()
    guess = detector.get_gender(first_name)
    if guess in ["male", "mostly_male"]:
        return "Hombre"
    elif guess in ["female", "mostly_female"]:
        return "Mujer"
    return "No Identificado"


def calculate_authorship_and_gender(
    df: pd.DataFrame,
    country: str = "chile",
) -> tuple[dict[str, Any], pd.DataFrame, dict[str, Any]]:
    """
    Construye la estructura de Nodos y Enlaces para el Sankey de Plotly,
    las métricas de género globales y el desglose de autoría por medio.
    """
    detector = gender.Detector(case_sensitive=False)

    df_auth = df[["id", "media_name", "author"]].copy()
    df_auth["author_clean"] = df_auth["author"].apply(clean_author_text)
    df_auth["category"] = df_auth["author_clean"].apply(categorize_author_type)

    # Inferencia de género solo a los firmados
    is_signed = df_auth["category"] == "Firmado"
    df_auth["gender"] = "N/A"
    df_auth.loc[is_signed, "gender"] = df_auth.loc[is_signed, "author_clean"].apply(
        lambda name: infer_gender(name, detector)
    )

    total_news = len(df_auth)
    count_agencia = int((df_auth["category"] == "Agencia").sum())
    count_anonimo = int((df_auth["category"] == "Anónimo").sum())
    count_firmado = int((df_auth["category"] == "Firmado").sum())

    firmados = df_auth[is_signed]
    count_hombre = int((firmados["gender"] == "Hombre").sum())
    count_mujer = int((firmados["gender"] == "Mujer").sum())
    count_no_id = int((firmados["gender"] == "No Identificado").sum())

    # Formato compatible con plotly.graph_objects.Sankey
    # Nodos:
    # 0: Total Noticias
    # 1: Agencias, 2: Redacción / Anónimo, 3: Periodista Firmante
    # 4: Hombre, 5: Mujer, 6: No Identificado
    sankey_data = {
        "country": country,
        "nodes": [
            {"id": 0, "label": "Total Noticias", "color": "#1f77b4"},
            {"id": 1, "label": "Agencias", "color": "#ff7f0e"},
            {"id": 2, "label": "Redacción / Anónimo", "color": "#7f7f7f"},
            {"id": 3, "label": "Periodista Firmante", "color": "#2ca02c"},
            {"id": 4, "label": "Hombre", "color": "#3366cc"},
            {"id": 5, "label": "Mujer", "color": "#dc3912"},
            {"id": 6, "label": "No Identificado", "color": "#990099"},
        ],
        "links": [
            {"source": 0, "target": 1, "value": count_agencia, "label": "Cables de agencia"},
            {"source": 0, "target": 2, "value": count_anonimo, "label": "Sin firma explícita"},
            {"source": 0, "target": 3, "value": count_firmado, "label": "Artículos firmados"},
            {"source": 3, "target": 4, "value": count_hombre, "label": "Firmados por hombres"},
            {"source": 3, "target": 5, "value": count_mujer, "label": "Firmados por mujeres"},
            {"source": 3, "target": 6, "value": count_no_id, "label": "Firma no identificable"},
        ],
        "counts": {
            "total": total_news,
            "agencia": count_agencia,
            "anonimo": count_anonimo,
            "firmado": count_firmado,
            "hombre": count_hombre,
            "mujer": count_mujer,
            "no_identificado": count_no_id,
        },
    }

    # KPIs de género
    identifiable_signed = count_hombre + count_mujer
    female_ratio_pct = round(
        (count_mujer / max(identifiable_signed, 1)) * 100.0, 2
    )
    gender_kpis = {
        "total_news": total_news,
        "total_signed": count_firmado,
        "male_count": count_hombre,
        "female_count": count_mujer,
        "unidentified_count": count_no_id,
        "female_ratio_pct": female_ratio_pct,
        "signed_pct": round((count_firmado / max(total_news, 1)) * 100.0, 2),
    }

    # Desglose por medio (Top 25 medios)
    top_media_list = (
        df_auth["media_name"].value_counts().head(25).index.tolist()
    )
    media_stats = []
    for media in top_media_list:
        sub = df_auth[df_auth["media_name"] == media]
        t = len(sub)
        n_anon = int((sub["category"] == "Anónimo").sum())
        n_agen = int((sub["category"] == "Agencia").sum())
        n_firm = int((sub["category"] == "Firmado").sum())
        firm_sub = sub[sub["category"] == "Firmado"]
        n_fem = int((firm_sub["gender"] == "Mujer").sum())
        n_masc = int((firm_sub["gender"] == "Hombre").sum())
        media_stats.append({
            "media_name": media,
            "total_articles": t,
            "anon_pct": round((n_anon / t) * 100.0, 1),
            "agency_pct": round((n_agen / t) * 100.0, 1),
            "signed_pct": round((n_firm / t) * 100.0, 1),
            "female_pct_of_signed": round((n_fem / max(n_fem + n_masc, 1)) * 100.0, 1),
        })

    df_media_stats = pd.DataFrame(media_stats)
    return sankey_data, df_media_stats, gender_kpis


def calculate_schooling_years(puntaje_inflesz: float) -> float:
    """Mapea el puntaje INFLESZ a años de escolaridad requeridos usando interpolación lineal segmentada."""
    if puntaje_inflesz >= 80:
        return 6.0 - ((puntaje_inflesz - 80) / 20.0) * 2.0
    elif puntaje_inflesz >= 65:
        return 8.0 - ((puntaje_inflesz - 65) / 15.0) * 2.0
    elif puntaje_inflesz >= 55:
        return 12.0 - ((puntaje_inflesz - 55) / 10.0) * 4.0
    elif puntaje_inflesz >= 40:
        return 16.0 - ((puntaje_inflesz - 40) / 15.0) * 4.0
    else:
        escolaridad = 16.0 + ((40.0 - puntaje_inflesz) / 40.0) * 4.0
        return min(escolaridad, 20.0)


def calculate_readability(
    df: pd.DataFrame,
    top_n_media: int = 15,
    samples_per_media: int = 100,
) -> pd.DataFrame:
    """
    Calcula el Índice de Legibilidad INFLESZ (Flesch-Szigriszt) y los años de escolaridad requeridos
    para los Top N medios mediante un muestreo representativo por medio.
    """
    df_clean = df.dropna(subset=["body", "media_name"]).copy()
    top_media = df_clean["media_name"].value_counts().head(top_n_media).index.tolist()
    df_top = df_clean[df_clean["media_name"].isin(top_media)]

    dic_silabas = pyphen.Pyphen(lang="es")
    results = []

    for media in top_media:
        media_df = df_top[df_top["media_name"] == media]
        sample = media_df.sample(n=min(samples_per_media, len(media_df)), random_state=42)

        media_inflesz = []
        media_schooling = []
        sample_excerpt = ""

        for _, row in sample.iterrows():
            text = str(row["body"]).strip()
            if len(text) < 50:
                continue

            sents = sent_tokenize(text[:2500])
            if not sents:
                continue

            if not sample_excerpt:
                sample_excerpt = sents[0][:180] + ("..." if len(sents[0]) > 180 else "")

            words = [w for w in word_tokenize(text[:2500]) if WORD_PATTERN.fullmatch(w)]
            if not words or not sents:
                continue

            num_syllables = sum(len(dic_silabas.inserted(w).split("-")) for w in words)
            ratio_sp = num_syllables / len(words)
            ratio_po = len(words) / len(sents)

            # Fórmula Flesch-Szigriszt (INFLESZ)
            inflesz = 206.835 - (62.3 * ratio_sp) - ratio_po
            schooling = calculate_schooling_years(inflesz)

            # Acotar a rango razonable
            if 0 <= inflesz <= 120 and 4 <= schooling <= 22:
                media_inflesz.append(inflesz)
                media_schooling.append(schooling)

        if media_inflesz:
            avg_inflesz = round(float(np.mean(media_inflesz)), 1)
            avg_schooling = round(float(np.mean(media_schooling)), 1)

            if avg_inflesz >= 80:
                cat = "Muy Fácil (Primaria)"
            elif avg_inflesz >= 65:
                cat = "Fácil (Secundaria Básica)"
            elif avg_inflesz >= 55:
                cat = "Normal (Secundaria Superior)"
            elif avg_inflesz >= 40:
                cat = "Algo Difícil (Universitario)"
            else:
                cat = "Muy Difícil (Especializado/Académico)"

            results.append({
                "media_name": media,
                "articles_evaluated": len(media_inflesz),
                "mean_inflesz": avg_inflesz,
                "mean_schooling_years": avg_schooling,
                "readability_category": cat,
                "sample_text": sample_excerpt,
            })

    df_readability = pd.DataFrame(results).sort_values("mean_schooling_years", ascending=False).reset_index(drop=True)
    return df_readability


def calculate_discourse_pos(
    df: pd.DataFrame,
    top_n_media: int = 15,
    samples_per_media: int = 50,
) -> pd.DataFrame:
    """
    Analiza la estructura del discurso mediante POS Tagging:
    - Adjetivos: Refleja opinión, crónica o sensacionalismo.
    - Verbos: Refleja acción, sucesos de última hora o ritmo informativo.
    - Sustantivos: Refleja lenguaje informativo, institucional o fáctico.
    """
    df_clean = df.dropna(subset=["body", "media_name"]).copy()
    top_media = df_clean["media_name"].value_counts().head(top_n_media).index.tolist()
    stop_words_es = set(stopwords.words("spanish"))

    results = []

    for media in top_media:
        media_df = df_clean[df_clean["media_name"] == media]
        sample = media_df.sample(n=min(samples_per_media, len(media_df)), random_state=42)

        adj_counter = Counter()
        noun_counter = Counter()
        verb_counter = Counter()
        total_tokens = 0

        for text in sample["body"]:
            words = [w for w in word_tokenize(str(text)[:1500]) if w.isalpha()]
            if not words:
                continue

            tagged = pos_tag(words)
            for word, tag in tagged:
                w_lower = word.lower()
                total_tokens += 1
                if tag in ADJ_TAGS:
                    if w_lower not in stop_words_es and len(w_lower) > 2:
                        adj_counter[w_lower] += 1
                elif tag in NOUN_TAGS:
                    if w_lower not in stop_words_es and len(w_lower) > 2:
                        noun_counter[w_lower] += 1
                elif tag in VERB_TAGS:
                    if w_lower not in stop_words_es and len(w_lower) > 2:
                        verb_counter[w_lower] += 1

        total_adj = sum(adj_counter.values())
        total_noun = sum(noun_counter.values())
        total_verb = sum(verb_counter.values())
        key_total = max(total_adj + total_noun + total_verb, 1)

        adj_pct = round((total_adj / key_total) * 100.0, 1)
        noun_pct = round((total_noun / key_total) * 100.0, 1)
        verb_pct = round((total_verb / key_total) * 100.0, 1)

        # Perfil dominante
        if adj_pct > 22.0:
            profile = "Opinión / Descriptivo"
        elif verb_pct > 32.0:
            profile = "Acción / Sucesos"
        else:
            profile = "Informativo / Fáctico"

        results.append({
            "media_name": media,
            "articles_analyzed": len(sample),
            "adj_pct": adj_pct,
            "noun_pct": noun_pct,
            "verb_pct": verb_pct,
            "discourse_profile": profile,
            "top_adjectives": ", ".join(w for w, _ in adj_counter.most_common(3)),
            "top_nouns": ", ".join(w for w, _ in noun_counter.most_common(3)),
            "top_verbs": ", ".join(w for w, _ in verb_counter.most_common(3)),
        })

    df_pos = pd.DataFrame(results).sort_values("adj_pct", ascending=False).reset_index(drop=True)
    return df_pos


def process_authorship(
    df: pd.DataFrame | None = None,
    country: str = "chile",
    days: int = 7,
) -> dict[str, Any]:
    """
    Función orquestadora principal del Módulo 3.
    Ejecuta el análisis de autoría, género, legibilidad y POS tagging, exportando a data/dashboard/.
    """
    if df is None:
        df = extract_news(country=country, days=days)

    # 1. Sankey y Diversidad de Género
    sankey_data, df_media_stats, gender_kpis = calculate_authorship_and_gender(df, country=country)

    # 2. Legibilidad INFLESZ
    df_readability = calculate_readability(df)

    # 3. Estructura del Discurso POS
    df_pos = calculate_discourse_pos(df)

    # Exportar a data/dashboard/
    with open(DASHBOARD_DIR / "authorship_sankey.json", "w", encoding="utf-8") as f:
        json.dump(sankey_data, f, ensure_ascii=False, indent=2)

    pd.DataFrame([gender_kpis]).to_parquet(DASHBOARD_DIR / "authorship_gender_kpis.parquet", index=False)
    df_media_stats.to_parquet(DASHBOARD_DIR / "authorship_media_stats.parquet", index=False)
    df_readability.to_parquet(DASHBOARD_DIR / "authorship_readability.parquet", index=False)
    df_pos.to_parquet(DASHBOARD_DIR / "authorship_pos_distribution.parquet", index=False)

    # Registrar checkpoint
    record_module_run(
        country=country,
        module_name="authorship",
        status="success",
        records_processed=len(df),
        metadata={
            "signed_pct": gender_kpis["signed_pct"],
            "female_ratio_pct": gender_kpis["female_ratio_pct"],
            "top_media_evaluated_readability": len(df_readability),
            "top_media_evaluated_pos": len(df_pos),
        },
    )

    return {
        "sankey": sankey_data,
        "gender_kpis": gender_kpis,
        "media_stats": df_media_stats,
        "readability": df_readability,
        "pos": df_pos,
    }
