"""
Vista de Monitoreo Operacional: Calidad de Datos y Salud del Scraper.
Presenta el semáforo de fuentes activas/caídas, completitud del corpus por columna
y un directorio interactivo paginado de medios.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from dash import html, dcc, dash_table

from src.dashboard.config import THEME_COLORS, apply_theme_to_figure
from src.dashboard.data_loader import (
    load_quality_summary,
    load_quality_corpus_integrity,
    load_quality_sources_health,
    filter_by_media,
)
from src.dashboard.components.kpi_card import create_kpi_card
from src.dashboard.components.empty_state import create_empty_state


def build_corpus_integrity_figure(df_integrity: pd.DataFrame) -> go.Figure:
    """Construye un gráfico de barras horizontales con la tasa de completitud por columna."""
    if df_integrity.empty or "column_name" not in df_integrity.columns:
        return apply_theme_to_figure(go.Figure(), title="Completitud de Campos del Corpus")

    df = df_integrity.copy()
    # Calcular tasa de completitud real (100 - null - empty)
    total_rows = df["total_rows"].iloc[0] if "total_rows" in df.columns and len(df) > 0 else 5603
    df["missing_count"] = df["null_count"] + df.get("empty_string_count", 0)
    df["fill_rate_pct"] = (100.0 * (total_rows - df["missing_count"]) / total_rows).clip(0, 100)

    # Ordenar ascendente para que los campos más completos queden arriba
    df_sorted = df.sort_values(by="fill_rate_pct", ascending=True)

    # Asignar colores según umbral semántico de salud de datos
    colors = []
    for rate in df_sorted["fill_rate_pct"]:
        if rate >= 90.0:
            colors.append(THEME_COLORS["status_success"])
        elif rate >= 70.0:
            colors.append(THEME_COLORS["status_warning"])
        else:
            colors.append(THEME_COLORS["status_danger"])

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df_sorted["fill_rate_pct"],
            y=df_sorted["column_name"],
            orientation="h",
            marker=dict(color=colors, line=dict(color="rgba(255,255,255,0.1)", width=1)),
            customdata=df_sorted["missing_count"],
            hovertemplate="<b>Campo: %{y}</b><br>Completitud: <b>%{x:.1f}%</b><br>Valores faltantes: %{customdata:,} registros<extra></extra>",
        )
    )

    fig = apply_theme_to_figure(fig, title="Integridad del Corpus por Columna (% de Relleno)")
    fig.update_layout(
        xaxis=dict(
            range=[0, 105],
            rangemode="tozero",
            title="Tasa de Completitud (%)",
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


def create_sources_health_table(df_sources: pd.DataFrame) -> dash_table.DataTable:
    """Construye un DataTable interactivo con ordenamiento, filtrado nativo y paginación."""
    if df_sources.empty:
        return html.Div("No hay registros de fuentes disponibles.")

    df = df_sources.copy()
    
    # Mapear estado a etiquetas con emoji accesible
    status_map = {
        "verde": "🟢 Activa (≤ 12h)",
        "amarillo": "🟡 Advertencia (12-48h)",
        "rojo": "🔴 Silenciosa (> 48h)",
    }
    df["status_label"] = df["status"].map(lambda s: status_map.get(s, s))

    if "last_seen" in df.columns:
        df["last_seen_str"] = pd.to_datetime(df["last_seen"]).dt.strftime("%d-%b %H:%M")
    else:
        df["last_seen_str"] = "N/A"

    df["hours_inactive"] = df["hours_since_last_seen"].round(1)

    table_data = df[["status_label", "media_name", "total_articles", "hours_inactive", "last_seen_str"]].to_dict("records")

    columns = [
        {"name": "Estado", "id": "status_label"},
        {"name": "Medio / Fuente", "id": "media_name"},
        {"name": "Total Noticias", "id": "total_articles", "type": "numeric"},
        {"name": "Horas Inactivo", "id": "hours_inactive", "type": "numeric"},
        {"name": "Última Noticia", "id": "last_seen_str"},
    ]

    return dash_table.DataTable(
        id="quality-sources-table",
        data=table_data,
        columns=columns,
        page_size=10,
        sort_action="native",
        filter_action="native",
        style_as_list_view=True,
        style_header={
            "backgroundColor": "#1E293B",
            "color": THEME_COLORS["text_primary"],
            "fontWeight": "600",
            "borderBottom": f"1px solid {THEME_COLORS['border']}",
            "borderTop": "none",
            "borderLeft": "none",
            "borderRight": "none",
            "fontFamily": "Inter, sans-serif",
            "fontSize": "12px",
            "textTransform": "uppercase",
            "letterSpacing": "0.05em",
            "padding": "12px 14px",
        },
        style_data={
            "backgroundColor": "#0F172A",
            "color": THEME_COLORS["text_primary"],
            "borderBottom": "1px solid #1E293B",
            "borderTop": "none",
            "borderLeft": "none",
            "borderRight": "none",
            "fontFamily": "Inter, sans-serif",
            "fontSize": "13px",
            "padding": "10px 14px",
            "height": "auto",
        },
        style_cell={
            "textAlign": "left",
            "fontVariantNumeric": "tabular-nums",
        },
        style_cell_conditional=[
            {"if": {"column_id": "total_articles"}, "textAlign": "right"},
            {"if": {"column_id": "hours_inactive"}, "textAlign": "right"},
        ],
        style_data_conditional=[
            {
                "if": {"filter_query": '{status_label} contains "🟢"'},
                "color": "#10B981",
            },
            {
                "if": {"filter_query": '{status_label} contains "🟡"'},
                "color": "#F59E0B",
            },
            {
                "if": {"filter_query": '{status_label} contains "🔴"'},
                "color": "#F43F5E",
            },
        ],
    )


def create_quality_view(selected_media: str | None = None) -> html.Div:
    """
    Ensambla la vista operacional de 'Calidad de Datos'.
    Contiene semáforo de scrapers, barra de completitud de campos y directorio interactivo.
    """
    summary = load_quality_summary()
    df_integrity = load_quality_corpus_integrity()
    df_sources = load_quality_sources_health()

    if selected_media and selected_media != "ALL":
        df_sources = filter_by_media(df_sources, selected_media)

    # 1. BANs Strip de Salud Operacional
    health_score = summary.get("health_score_pct", 0.0)
    sources_green = summary.get("sources_green", 0)
    sources_yellow = summary.get("sources_yellow", 0)
    sources_red = summary.get("sources_red", 0)
    total_sources = summary.get("total_sources_evaluated", 0)

    ban_strip = html.Div(
        className="grid grid-cols-4",
        style={"marginBottom": "20px"},
        children=[
            create_kpi_card(
                label="Salud Global del Scraper",
                value=f"{health_score:.1f}%",
                note=f"{sources_green} de {total_sources} fuentes activas",
                icon="🛡️",
            ),
            create_kpi_card(
                label="Fuentes Saludables",
                value=sources_green,
                note="Noticia en últimas 12 horas",
                icon="🟢",
            ),
            create_kpi_card(
                label="Fuentes con Advertencia",
                value=sources_yellow,
                note="Inactividad entre 12h y 48h",
                icon="🟡",
            ),
            create_kpi_card(
                label="Fuentes en Silencio / Caídas",
                value=sources_red,
                note="Sin noticias hace más de 48h",
                icon="🔴",
            ),
        ],
    )

    # 2. Main Integrity Chart
    fig_integrity = build_corpus_integrity_figure(df_integrity)
    integrity_card = html.Div(
        className="card",
        style={"marginBottom": "20px", "padding": "16px"},
        children=[
            dcc.Graph(
                id="quality-integrity-graph",
                figure=fig_integrity,
                config={"displayModeBar": False, "responsive": True},
            )
        ],
    )

    # 3. Directory Table Card
    table_comp = create_sources_health_table(df_sources)
    directory_card = html.Div(
        className="card",
        style={"padding": "20px"},
        children=[
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "16px"},
                children=[
                    html.H4("Directorio de Fuentes y Diagnóstico de Scraping", style={"margin": "0", "fontSize": "15px", "fontWeight": "600"}),
                    html.Span(f"{len(df_sources)} medios registrados", style={"fontSize": "12px", "color": THEME_COLORS["text_muted"]}),
                ],
            ),
            table_comp,
        ],
    )

    return html.Div(
        className="view-container",
        children=[
            ban_strip,
            integrity_card,
            directory_card,
        ],
    )
