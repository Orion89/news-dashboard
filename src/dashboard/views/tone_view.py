"""
Vista de Análisis Semántico y Editorial: El Tono de la Cobertura.
Presenta la evolución temporal de emociones (RoBERTuito), el ranking de sensacionalismo,
el péndulo temporal Pasado vs Futuro y los n-gramas emergentes (trending topics).
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from dash import html, dcc

from src.dashboard.config import THEME_COLORS, apply_theme_to_figure
from src.dashboard.data_loader import (
    load_tone_emotions_timeseries,
    load_tone_pendulum_daily,
    load_tone_sensationalism_ranking,
    load_tone_emerging_ngrams,
    filter_by_media,
)
from src.dashboard.components.kpi_card import create_kpi_card
from src.dashboard.components.empty_state import create_empty_state


# Paleta semántica fija para emociones (Miller's Law)
EMOTION_COLORS = {
    "alegria": "#10B981",    # Esmeralda
    "tristeza": "#3B82F6",   # Azul clásico
    "ira": "#EF4444",        # Rojo alerta
    "miedo": "#8B5CF6",      # Violeta
    "sorpresa": "#06B6D4",   # Turquesa
    "asco": "#F59E0B",       # Ámbar
    "otros": "#64748B",      # Pizarra / Neutro
}


def build_emotions_timeseries_figure(df_emotions: pd.DataFrame) -> go.Figure:
    """Construye un gráfico multilínea con la intensidad media diaria de emociones."""
    if df_emotions.empty or "emotion" not in df_emotions.columns:
        return apply_theme_to_figure(go.Figure(), title="Evolución Temporal de Emociones (RoBERTuito)")

    # Agrupar por fecha y emoción calculando la intensidad media
    df_agg = (
        df_emotions.groupby(["date_day", "emotion"], as_index=False)["intensity"]
        .mean()
        .sort_values(by="date_day")
    )

    fig = go.Figure()
    for emotion_name, df_group in df_agg.groupby("emotion"):
        color = EMOTION_COLORS.get(emotion_name.lower(), "#94A3B8")
        label = emotion_name.capitalize()
        fig.add_trace(
            go.Scatter(
                x=df_group["date_day"],
                y=df_group["intensity"] * 100.0,
                mode="lines+markers",
                name=label,
                line=dict(color=color, width=2),
                marker=dict(size=5),
                hovertemplate=f"<b>{label}</b>: %{{y:.2f}}%<extra></extra>",
            )
        )

    fig = apply_theme_to_figure(fig, title="Evolución Temporal de Emociones en Titulares y Leads")
    fig.update_layout(
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
        ),
        yaxis=dict(
            rangemode="tozero",
            title="Intensidad Promedio (%)",
            ticksuffix="%",
            gridcolor=THEME_COLORS["border"],
        ),
        xaxis=dict(title="", showgrid=False),
        margin=dict(l=40, r=24, t=40, b=30),
    )
    return fig


def build_sensationalism_ranking_figure(df_sensationalism: pd.DataFrame) -> go.Figure:
    """Construye un gráfico de barras horizontales con el ranking de sensacionalismo por medio."""
    if df_sensationalism.empty or "avg_sensationalism" not in df_sensationalism.columns:
        return apply_theme_to_figure(go.Figure(), title="Índice de Sensacionalismo por Medio")

    # Tomar top 10 medios ordenados ascendentemente para que el mayor quede arriba
    df_top = df_sensationalism.sort_values(by="avg_sensationalism", ascending=True).tail(10)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df_top["avg_sensationalism"],
            y=df_top["media_name"],
            orientation="h",
            marker=dict(
                color=THEME_COLORS["accent_secondary"],
                line=dict(color="rgba(255,255,255,0.15)", width=1),
            ),
            customdata=list(zip(df_top["avg_emotion"], df_top["avg_adjectives"], df_top["articles_count"])),
            hovertemplate="<b>%{y}</b><br>Sensacionalismo: <b>%{x:.1f} pts</b><br>Carga emocional: %{customdata[0]:.1f} | Adjetivación: %{customdata[1]:.1f}<br>Noticias analizadas: %{customdata[2]}<extra></extra>",
        )
    )

    fig = apply_theme_to_figure(fig, title="Ranking de Sensacionalismo Editorial (Top Medios)")
    fig.update_layout(
        xaxis=dict(
            rangemode="tozero",
            title="Índice Ponderado (0-100)",
            gridcolor=THEME_COLORS["border"],
        ),
        yaxis=dict(title="", showgrid=False, automargin=True),
        margin=dict(l=20, r=24, t=40, b=30),
    )
    return fig


def build_pendulum_gauge_figure(df_pendulum: pd.DataFrame) -> go.Figure:
    """Construye un velocímetro o indicador del péndulo temporal Pasado (-100) vs Futuro (+100)."""
    if df_pendulum.empty or "daily_pendulum_score" not in df_pendulum.columns:
        score = 0.0
    else:
        # Puntuación media del periodo
        score = float(df_pendulum["daily_pendulum_score"].mean())

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=score,
            number={"suffix": " pts", "font": {"color": THEME_COLORS["text_primary"], "size": 32}},
            gauge={
                "axis": {"range": [-100, 100], "tickwidth": 1, "tickcolor": THEME_COLORS["text_muted"]},
                "bar": {"color": THEME_COLORS["accent_cyan"], "thickness": 0.25},
                "bgcolor": "#0F172A",
                "borderwidth": 1,
                "bordercolor": THEME_COLORS["border"],
                "steps": [
                    {"range": [-100, -20], "color": "rgba(239, 68, 68, 0.2)"},   # Pasado / Forense
                    {"range": [-20, 20], "color": "rgba(100, 116, 139, 0.2)"},   # Equilibrado / Presente
                    {"range": [20, 100], "color": "rgba(16, 185, 129, 0.2)"},    # Futuro / Prospectivo
                ],
                "threshold": {
                    "line": {"color": "#FFFFFF", "width": 3},
                    "thickness": 0.75,
                    "value": score,
                },
            },
        )
    )

    fig = apply_theme_to_figure(fig, title="Péndulo Temporal: Pasado vs. Futuro")
    fig.update_layout(
        margin=dict(l=30, r=30, t=50, b=20),
        height=220,
    )
    return fig


def create_emerging_ngrams_component(df_ngrams: pd.DataFrame) -> html.Div:
    """Construye una grilla de etiquetas con los términos emergentes (Trending Topics)."""
    if df_ngrams.empty:
        return create_empty_state("Sin tendencias", "No se identificaron n-gramas con aceleración.")

    # Tomar top 12 n-gramas por ratio de crecimiento
    sample = df_ngrams.head(12).to_dict("records")

    badges = []
    for item in sample:
        term = item.get("ngram", "")
        growth = item.get("growth_ratio", 0.0)
        recent_cnt = item.get("recent_count", 0)

        badge = html.Div(
            style={
                "display": "inline-flex",
                "alignItems": "center",
                "gap": "6px",
                "padding": "6px 12px",
                "borderRadius": "16px",
                "backgroundColor": "#0F172A",
                "border": f"1px solid {THEME_COLORS['border']}",
                "margin": "4px",
                "fontSize": "12px",
            },
            children=[
                html.Span(term, style={"color": THEME_COLORS["text_primary"], "fontWeight": "600"}),
                html.Span(
                    f"+{growth:.0f}%" if growth > 0 else f"{growth:.0f}%",
                    style={"color": THEME_COLORS["status_success"], "fontWeight": "700", "fontSize": "11px"},
                ),
                html.Span(
                    f"({recent_cnt})",
                    style={"color": THEME_COLORS["text_muted"], "fontSize": "10px"},
                ),
            ],
        )
        badges.append(badge)

    return html.Div(
        className="card",
        style={"padding": "18px", "height": "100%"},
        children=[
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "12px"},
                children=[
                    html.H4("Términos y N-Gramas Emergentes", style={"margin": "0", "fontSize": "14px", "fontWeight": "600"}),
                    html.Span("Aceleración 24-48h", style={"fontSize": "11px", "color": THEME_COLORS["text_muted"]}),
                ],
            ),
            html.Div(
                style={"display": "flex", "flexWrap": "wrap", "maxHeight": "200px", "overflowY": "auto"},
                children=badges,
            ),
        ],
    )


def create_tone_view(selected_media: str | None = None) -> html.Div:
    """
    Ensambla la vista analítica de 'El Tono'.
    Contiene BANs, evolución de emociones RoBERTuito, ranking de sensacionalismo,
    indicador del péndulo temporal y trending terms.
    """
    df_emotions = load_tone_emotions_timeseries()
    df_pendulum = load_tone_pendulum_daily()
    df_sensationalism = load_tone_sensationalism_ranking()
    df_ngrams = load_tone_emerging_ngrams()

    if selected_media and selected_media != "ALL":
        df_emotions = filter_by_media(df_emotions, selected_media)
        df_pendulum = filter_by_media(df_pendulum, selected_media)
        df_sensationalism = filter_by_media(df_sensationalism, selected_media)

    # 1. BANs Strip
    dominant_emotion = "Neutro / Mixto"
    if not df_emotions.empty and "emotion" in df_emotions.columns:
        dom_series = df_emotions.groupby("emotion")["intensity"].mean()
        if not dom_series.empty:
            dominant_emotion = dom_series.idxmax().capitalize()

    avg_sens = float(df_sensationalism["avg_sensationalism"].mean()) if not df_sensationalism.empty else 0.0
    pendulum_score = float(df_pendulum["daily_pendulum_score"].mean()) if not df_pendulum.empty else 0.0
    total_ngrams = len(df_ngrams)

    pendulum_label = "Equilibrado"
    if pendulum_score > 15:
        pendulum_label = "Prospectivo (Futuro)"
    elif pendulum_score < -15:
        pendulum_label = "Forense (Pasado)"

    ban_strip = html.Div(
        className="grid grid-cols-4",
        style={"marginBottom": "20px"},
        children=[
            create_kpi_card(
                label="Emoción Dominante",
                value=dominant_emotion,
                note="RoBERTuito fine-tuned GPU",
                icon="🎭",
            ),
            create_kpi_card(
                label="Sensacionalismo Medio",
                value=f"{avg_sens:.1f} pts",
                note="Escala ponderada 0-100",
                icon="🔥",
            ),
            create_kpi_card(
                label="Péndulo Temporal",
                value=f"{pendulum_score:+.1f}",
                note=f"Sesgo: {pendulum_label}",
                icon="⏳",
            ),
            create_kpi_card(
                label="Términos Emergentes",
                value=total_ngrams,
                note="Spike de cobertura 24-48h",
                icon="⚡",
            ),
        ],
    )

    # 2. Main Emotions Timeline
    fig_emotions = build_emotions_timeseries_figure(df_emotions)
    emotions_card = html.Div(
        className="card",
        style={"marginBottom": "20px", "padding": "16px"},
        children=[
            dcc.Graph(
                id="tone-emotions-graph",
                figure=fig_emotions,
                config={"displayModeBar": False, "responsive": True},
            )
        ],
    )

    # 3. Bottom Row: Sensationalism Ranking + Pendulum & Emerging N-Grams
    fig_sens = build_sensationalism_ranking_figure(df_sensationalism)
    sens_card = html.Div(
        className="card",
        style={"padding": "16px"},
        children=[
            dcc.Graph(
                id="tone-sensationalism-graph",
                figure=fig_sens,
                config={"displayModeBar": False, "responsive": True},
            )
        ],
    )

    fig_gauge = build_pendulum_gauge_figure(df_pendulum)
    gauge_card = html.Div(
        className="card",
        style={"padding": "16px", "marginBottom": "16px"},
        children=[
            dcc.Graph(
                id="tone-pendulum-gauge",
                figure=fig_gauge,
                config={"displayModeBar": False, "responsive": True},
            )
        ],
    )

    ngrams_comp = create_emerging_ngrams_component(df_ngrams)

    right_col = html.Div(
        children=[
            gauge_card,
            ngrams_comp,
        ]
    )

    bottom_row = html.Div(
        className="grid grid-cols-12",
        children=[
            html.Div(className="col-7", children=[sens_card]),
            html.Div(className="col-5", children=[right_col]),
        ],
    )

    return html.Div(
        className="view-container",
        children=[
            ban_strip,
            emotions_card,
            bottom_row,
        ],
    )
