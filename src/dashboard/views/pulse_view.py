"""
Vista de Monitoreo Operacional: El Pulso de las Noticias.
Presenta velocidad de publicación continua, detección de breaking news,
análisis de sindicación (cables duplicados) y anomalías de extensión.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from dash import html, dcc

from src.dashboard.config import THEME_COLORS, apply_theme_to_figure
from src.dashboard.data_loader import (
    load_pulse_kpis,
    load_hourly_velocity,
    load_syndication_media,
    load_length_anomalies,
    filter_by_media,
)
from src.dashboard.components.kpi_card import create_kpi_card
from src.dashboard.components.empty_state import create_empty_state


def build_pulse_velocity_figure(df_velocity: pd.DataFrame) -> go.Figure:
    """Construye la figura de velocidad horaria continua con área y umbral μ + 2σ."""
    if df_velocity.empty or "hour_bucket" not in df_velocity.columns:
        return apply_theme_to_figure(go.Figure(), title="Velocidad Continua de Publicación")

    fig = go.Figure()

    # Serie temporal continua (área sutil + línea principal)
    fig.add_trace(
        go.Scatter(
            x=df_velocity["hour_bucket"],
            y=df_velocity["news_count"],
            mode="lines",
            name="Velocidad (noticias/h)",
            line=dict(color=THEME_COLORS["accent_cyan"], width=2.2),
            fill="tozeroy",
            fillcolor="rgba(6, 182, 212, 0.12)",
            hovertemplate="<b>%{x|%d %b %H:00 hrs}</b><br>Noticias: <b>%{y:,}</b> arts<extra></extra>",
        )
    )

    # Umbral de alerta μ + 2σ si existe
    if "peak_threshold" in df_velocity.columns and not df_velocity["peak_threshold"].isna().all():
        threshold_val = float(df_velocity["peak_threshold"].iloc[0])
        fig.add_hline(
            y=threshold_val,
            line_dash="dash",
            line_color=THEME_COLORS["status_warning"],
            line_width=1.5,
            annotation_text=f"Umbral Alerta ({threshold_val:.1f} arts/h)",
            annotation_position="top right",
            annotation_font=dict(color=THEME_COLORS["status_warning"], size=11),
        )

    # Marcadores de Breaking News (picos)
    if "is_peak" in df_velocity.columns:
        df_peaks = df_velocity[df_velocity["is_peak"]]
        if not df_peaks.empty:
            fig.add_trace(
                go.Scatter(
                    x=df_peaks["hour_bucket"],
                    y=df_peaks["news_count"],
                    mode="markers",
                    name="Pico Breaking News",
                    marker=dict(
                        symbol="circle",
                        size=9,
                        color=THEME_COLORS["status_danger"],
                        line=dict(color="#FFFFFF", width=1.5),
                    ),
                    hovertemplate="<b>ALERTA BREAKING NEWS</b><br>%{x|%d %b %H:00 hrs}<br>Volumen: <b>%{y:,}</b> arts<extra></extra>",
                )
            )

    fig = apply_theme_to_figure(fig, title="Velocidad Continua de Publicación (Noticias por Hora)")
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
            title="Noticias / hora",
            gridcolor=THEME_COLORS["border"],
            zerolinecolor=THEME_COLORS["border"],
        ),
        xaxis=dict(
            title="",
            showgrid=False,
        ),
        margin=dict(l=40, r=24, t=40, b=30),
    )
    return fig


def build_pulse_syndication_figure(df_syndication: pd.DataFrame) -> go.Figure:
    """Construye gráfico de barras horizontales ordenadas por tasa de sindicación."""
    if df_syndication.empty or "syndication_rate_pct" not in df_syndication.columns:
        return apply_theme_to_figure(go.Figure(), title="Sindicación de Cables por Medio")

    # Filtrar medios con volumen representativo (mínimo 5 artículos) para evitar 1/1 = 100%
    df_valid = df_syndication[df_syndication["total_articles"] >= 5].copy()
    if df_valid.empty:
        df_valid = df_syndication.copy()

    # Tomar top 10 medios con mayor tasa y ordenar ascendente para que el mayor quede arriba
    df_top = df_valid.sort_values(by="syndication_rate_pct", ascending=True).tail(10)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df_top["syndication_rate_pct"],
            y=df_top["media_name"],
            orientation="h",
            marker=dict(
                color=THEME_COLORS["accent_cyan"],
                line=dict(color=THEME_COLORS["accent_blue"], width=1),
            ),
            customdata=list(zip(df_top["syndicated_articles"], df_top["total_articles"])),
            hovertemplate="<b>%{y}</b><br>Tasa Sindicación: <b>%{x:.1f}%</b><br>Cables repetidos: %{customdata[0]} de %{customdata[1]} artículos<extra></extra>",
        )
    )

    fig = apply_theme_to_figure(fig, title="Top Medios por Tasa de Sindicación (Cables Duplicados)")
    fig.update_layout(
        xaxis=dict(
            rangemode="tozero",
            title="Tasa de Sindicación (%)",
            ticksuffix="%",
            gridcolor=THEME_COLORS["border"],
        ),
        yaxis=dict(
            title="",
            showgrid=False,
            automargin=True,
        ),
        margin=dict(l=20, r=24, t=40, b=30),
    )
    return fig


def create_pulse_anomalies_component(df_anomalies: pd.DataFrame) -> html.Div:
    """Construye un monitor visual de anomalías de longitud (ultra cortas y ultra largas)."""
    if df_anomalies.empty:
        return create_empty_state("Sin anomalías", "No se detectaron artículos fuera de rango.")

    # Tomar las 8 anomalías más relevantes
    sample = df_anomalies.head(8).to_dict("records")

    rows = []
    for item in sample:
        anomaly_type = item.get("anomaly_type", "")
        is_short = anomaly_type == "ultra_short"
        badge_class = "badge-warning" if is_short else "badge-info"
        badge_text = "Ultra Corto (< p01)" if is_short else "Ultra Largo (> p99)"
        
        char_len = item.get("char_length", 0)
        media_name = item.get("media_name", "Desconocido")
        url = item.get("url", "#")

        row = html.Div(
            className="anomaly-row",
            style={
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "space-between",
                "padding": "10px 12px",
                "borderBottom": f"1px solid {THEME_COLORS['border']}",
                "fontSize": "13px",
            },
            children=[
                html.Div([
                    html.A(
                        media_name,
                        href=url,
                        target="_blank",
                        style={
                            "color": THEME_COLORS["text_primary"],
                            "fontWeight": "600",
                            "textDecoration": "none",
                            "display": "block",
                        },
                    ),
                    html.Span(
                        f"{char_len:,} caracteres (~{char_len // 6:,} palabras)",
                        className="tabular-nums",
                        style={"color": THEME_COLORS["text_muted"], "fontSize": "11px"},
                    ),
                ]),
                html.Span(
                    badge_text,
                    className=f"badge {badge_class}",
                    style={"fontSize": "11px", "padding": "3px 8px", "borderRadius": "4px"},
                ),
            ],
        )
        rows.append(row)

    return html.Div(
        className="card",
        style={"padding": "18px", "height": "100%", "display": "flex", "flexDirection": "column"},
        children=[
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "12px"},
                children=[
                    html.H4("Monitor de Anomalías de Extensión", style={"margin": "0", "fontSize": "14px", "fontWeight": "600"}),
                    html.Span("p01 / p99 Outliers", style={"fontSize": "11px", "color": THEME_COLORS["text_muted"]}),
                ],
            ),
            html.Div(
                style={"overflowY": "auto", "maxHeight": "320px"},
                children=rows,
            ),
        ],
    )


def create_pulse_view(selected_media: str | None = None) -> html.Div:
    """
    Ensambla la vista operacional de 'El Pulso'.
    Contiene BANs, gráfico continuo de velocidad, ranking de sindicación y anomalías.
    """
    kpis = load_pulse_kpis()
    df_velocity = load_hourly_velocity()
    df_syndication = load_syndication_media()
    df_anomalies = load_length_anomalies()

    if selected_media and selected_media != "ALL":
        df_syndication = filter_by_media(df_syndication, selected_media)
        df_anomalies = filter_by_media(df_anomalies, selected_media)

    # 1. BANs Strip
    recent_vol = kpis.get("recent_24h_volume", 0)
    delta_pct = kpis.get("delta_24h_pct", 0.0)
    daily_avg = kpis.get("daily_avg_volume", 0.0)
    total_vol = kpis.get("total_window_volume", 0)
    syn_pct = kpis.get("syndication_rate_pct", 0.0)
    syn_count = kpis.get("syndicated_articles_count", 0)
    peak_max = int(df_velocity["news_count"].max()) if not df_velocity.empty else 0

    ban_strip = html.Div(
        className="grid grid-cols-4",
        style={"marginBottom": "20px"},
        children=[
            create_kpi_card(
                label="Volumen Últimas 24h",
                value=recent_vol,
                delta=delta_pct,
                delta_text="vs 24h previas",
                note=f"Total periodo: {total_vol:,} noticias",
                icon="⚡",
            ),
            create_kpi_card(
                label="Promedio Diario",
                value=f"{daily_avg:,.0f}",
                note="Ritmo sostenido en 7 días",
                icon="📅",
            ),
            create_kpi_card(
                label="Pico Récord Horario",
                value=peak_max,
                note="Noticias en una sola hora",
                icon="📈",
            ),
            create_kpi_card(
                label="Tasa de Sindicación",
                value=f"{syn_pct:.1f}%",
                note=f"{syn_count:,} cables duplicados (LSH)",
                icon="🔄",
            ),
        ],
    )

    # 2. Main Velocity Chart
    fig_velocity = build_pulse_velocity_figure(df_velocity)
    velocity_card = html.Div(
        className="card",
        style={"marginBottom": "20px", "padding": "16px"},
        children=[
            dcc.Graph(
                id="pulse-velocity-graph",
                figure=fig_velocity,
                config={"displayModeBar": False, "responsive": True},
            )
        ],
    )

    # 3. Bottom Row (Sindicación + Anomalías)
    fig_syndication = build_pulse_syndication_figure(df_syndication)
    syndication_card = html.Div(
        className="card",
        style={"padding": "16px"},
        children=[
            dcc.Graph(
                id="pulse-syndication-graph",
                figure=fig_syndication,
                config={"displayModeBar": False, "responsive": True},
            )
        ],
    )

    anomalies_card = create_pulse_anomalies_component(df_anomalies)

    bottom_row = html.Div(
        className="grid grid-cols-12",
        children=[
            html.Div(className="col-7", children=[syndication_card]),
            html.Div(className="col-5", children=[anomalies_card]),
        ],
    )

    return html.Div(
        className="view-container",
        children=[
            ban_strip,
            velocity_card,
            bottom_row,
        ],
    )
