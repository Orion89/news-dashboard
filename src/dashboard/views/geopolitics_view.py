"""
Vista de Inteligencia Geopolítica: Mapa de Chile y Radar de Protagonistas.
Presenta la geolocalización de noticias en comunas/regiones mediante scatter_geo,
y el ranking de figuras públicas (PER) e instituciones/organizaciones (ORG) extraídas con spaCy NER.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from dash import html, dcc

from src.dashboard.config import THEME_COLORS, apply_theme_to_figure
from src.dashboard.data_loader import (
    load_geopolitics_locations,
    load_geopolitics_protagonists,
)
from src.dashboard.components.kpi_card import create_kpi_card
from src.dashboard.components.empty_state import create_empty_state


def build_locations_map_figure(df_locations: pd.DataFrame) -> go.Figure:
    """Construye el mapa de dispersión geoespacial de Chile (scatter_geo)."""
    if df_locations.empty or "latitude" not in df_locations.columns:
        return apply_theme_to_figure(go.Figure(), title="Foco Geográfico de la Cobertura")

    fig = go.Figure()

    # Calcular tamaños proporcionales con mínimo legible
    max_mentions = df_locations["total_mentions"].max() if len(df_locations) > 0 else 1
    marker_sizes = [max(8, int(m / max_mentions * 28 + 6)) for m in df_locations["total_mentions"]]

    fig.add_trace(
        go.Scattergeo(
            lon=df_locations["longitude"],
            lat=df_locations["latitude"],
            text=df_locations["city"],
            mode="markers+text",
            textposition="top center",
            textfont=dict(color=THEME_COLORS["text_primary"], size=10, family="Inter, sans-serif"),
            marker=dict(
                size=marker_sizes,
                color=THEME_COLORS["accent_cyan"],
                opacity=0.88,
                line=dict(color="#FFFFFF", width=1.5),
                sizemode="diameter",
            ),
            customdata=list(zip(df_locations["region"], df_locations["total_mentions"])),
            hovertemplate="<b>%{text}</b><br>Región: %{customdata[0]}<br>Menciones directas: <b>%{customdata[1]:,}</b><extra></extra>",
        )
    )

    fig = apply_theme_to_figure(fig, title="Distribución Territorial de Noticias (Chile)")
    fig.update_geos(
        scope="south america",
        fitbounds=False,
        center=dict(lat=-35.6751, lon=-71.5430),
        projection_scale=2.7,
        showcountries=True,
        countrycolor=THEME_COLORS["border"],
        showland=True,
        landcolor="#1E293B",
        showocean=True,
        oceancolor="#0B0F19",
        showlakes=False,
        bgcolor="rgba(0,0,0,0)",
        lonaxis=dict(range=[-76, -66]),
        lataxis=dict(range=[-56, -17]),
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        height=480,
    )
    return fig


def build_protagonists_figure(df_protagonists: pd.DataFrame, entity_type: str = "PER") -> go.Figure:
    """Construye un gráfico de barras horizontales de figuras públicas o instituciones."""
    title_suffix = "Figuras Públicas (PER)" if entity_type == "PER" else "Organizaciones e Instituciones (ORG)"
    bar_color = THEME_COLORS["accent_primary"] if entity_type == "PER" else THEME_COLORS["accent_cyan"]

    if df_protagonists.empty or "type" not in df_protagonists.columns:
        return apply_theme_to_figure(go.Figure(), title=f"Top Protagonistas: {title_suffix}")

    # Filtrar por tipo y tomar top 10 ordenado ascendente (para que el mayor quede arriba)
    df_filtered = df_protagonists[df_protagonists["type"] == entity_type].copy()
    df_top = df_filtered.sort_values(by="total_mentions", ascending=True).tail(10)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df_top["total_mentions"],
            y=df_top["entity"],
            orientation="h",
            marker=dict(color=bar_color, line=dict(color="rgba(255,255,255,0.15)", width=1)),
            customdata=df_top["dominant_category"],
            hovertemplate="<b>%{y}</b><br>Menciones: <b>%{x:,}</b><br>Categoría: %{customdata}<extra></extra>",
        )
    )

    fig = apply_theme_to_figure(fig, title=f"Top Protagonistas: {title_suffix}")
    fig.update_layout(
        xaxis=dict(
            rangemode="tozero",
            title="Total de Menciones en Titulares y Leads",
            gridcolor=THEME_COLORS["border"],
        ),
        yaxis=dict(title="", showgrid=False, automargin=True),
        margin=dict(l=20, r=24, t=40, b=30),
    )
    return fig


def create_geopolitics_view(selected_media: str | None = None) -> html.Div:
    """
    Ensambla la vista analítica de 'Inteligencia Geopolítica'.
    Contiene mapa de Chile (scatter_geo) y radar de actores (PER y ORG).
    """
    df_locations = load_geopolitics_locations()
    df_protagonists = load_geopolitics_protagonists()

    # 1. BANs Strip
    total_locations = len(df_locations)
    total_per = len(df_protagonists[df_protagonists["type"] == "PER"]) if not df_protagonists.empty else 0
    total_org = len(df_protagonists[df_protagonists["type"] == "ORG"]) if not df_protagonists.empty else 0
    top_per_name = "N/A"
    if not df_protagonists.empty:
        df_per = df_protagonists[df_protagonists["type"] == "PER"]
        if not df_per.empty:
            top_per_name = df_per.sort_values(by="total_mentions", ascending=False).iloc[0]["entity"]

    ban_strip = html.Div(
        className="grid grid-cols-4",
        style={"marginBottom": "20px"},
        children=[
            create_kpi_card(
                label="Localidades Monitoreadas",
                value=total_locations,
                note="Comunas y regiones geocodificadas",
                icon="📍",
            ),
            create_kpi_card(
                label="Líder Más Mencionado",
                value=top_per_name,
                note="Figura con mayor frecuencia",
                icon="👤",
            ),
            create_kpi_card(
                label="Figuras Públicas (PER)",
                value=total_per,
                note="Entidades reconocidas con NER",
                icon="🏛️",
            ),
            create_kpi_card(
                label="Organizaciones (ORG)",
                value=total_org,
                note="Instituciones y empresas",
                icon="🏢",
            ),
        ],
    )

    # 2. Main Content: Map (col-5) + Protagonists (col-7)
    fig_map = build_locations_map_figure(df_locations)
    map_card = html.Div(
        className="card",
        style={"padding": "16px", "height": "100%"},
        children=[
            dcc.Graph(
                id="geopolitics-map-graph",
                figure=fig_map,
                config={"displayModeBar": False, "responsive": True},
            )
        ],
    )

    # Gráficos de Personas y Organizaciones
    fig_per = build_protagonists_figure(df_protagonists, entity_type="PER")
    fig_org = build_protagonists_figure(df_protagonists, entity_type="ORG")

    per_card = html.Div(
        className="card",
        style={"marginBottom": "16px", "padding": "16px"},
        children=[
            dcc.Graph(
                id="geopolitics-per-graph",
                figure=fig_per,
                config={"displayModeBar": False, "responsive": True},
            )
        ],
    )

    org_card = html.Div(
        className="card",
        style={"padding": "16px"},
        children=[
            dcc.Graph(
                id="geopolitics-org-graph",
                figure=fig_org,
                config={"displayModeBar": False, "responsive": True},
            )
        ],
    )

    right_col = html.Div(
        children=[
            per_card,
            org_card,
        ]
    )

    main_grid = html.Div(
        className="grid grid-cols-12",
        children=[
            html.Div(className="col-5", children=[map_card]),
            html.Div(className="col-7", children=[right_col]),
        ],
    )

    return html.Div(
        className="view-container",
        children=[
            ban_strip,
            main_grid,
        ],
    )
