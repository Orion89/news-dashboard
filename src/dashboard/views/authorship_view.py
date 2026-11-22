"""
Vista de Análisis de Autoría, Diversidad y Complejidad Editorial.
Presenta el diagrama de flujo Sankey (Corpus → Tipología → Género),
diversidad de género en periodistas, índice de legibilidad INFLESZ y perfiles POS.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from dash import html, dcc

from src.dashboard.config import THEME_COLORS, apply_theme_to_figure
from src.dashboard.data_loader import (
    load_authorship_sankey,
    load_authorship_gender_kpis,
    load_authorship_readability,
    load_authorship_pos_distribution,
    filter_by_media,
)
from src.dashboard.components.kpi_card import create_kpi_card
from src.dashboard.components.empty_state import create_empty_state


def build_authorship_sankey_figure(sankey_data: dict) -> go.Figure:
    """Construye el diagrama de flujo Sankey para visualizar la trazabilidad de firmas."""
    if not sankey_data or "nodes" not in sankey_data or "links" not in sankey_data:
        return apply_theme_to_figure(go.Figure(), title="Flujo de Autoría del Corpus")

    nodes = sankey_data["nodes"]
    links = sankey_data["links"]

    node_labels = [n.get("label", "") for n in nodes]
    node_colors = [
        "#3B82F6",  # Total Noticias
        "#F59E0B",  # Agencias
        "#64748B",  # Redacción / Anónimo
        "#06B6D4",  # Artículos Firmados
        "#3B82F6",  # Periodistas Hombres
        "#EC4899",  # Periodistas Mujeres
        "#8B5CF6",  # Género Indeterminado
    ]
    colors = node_colors[: len(nodes)] if len(node_colors) >= len(nodes) else [n.get("color", "#3B82F6") for n in nodes]

    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node=dict(
                pad=18,
                thickness=18,
                line=dict(color="#0F172A", width=1),
                label=node_labels,
                color=colors,
                hovertemplate="<b>%{label}</b><br>Artículos: <b>%{value:,}</b><extra></extra>",
            ),
            link=dict(
                source=[l["source"] for l in links],
                target=[l["target"] for l in links],
                value=[l["value"] for l in links],
                color="rgba(148, 163, 184, 0.22)",
                hovertemplate="<b>%{source.label} → %{target.label}</b><br>Volumen: <b>%{value:,}</b> noticias<extra></extra>",
            ),
        )
    )

    fig = apply_theme_to_figure(fig, title="Trazabilidad y Flujo de Autoría Editorial")
    fig.update_layout(
        font=dict(family="Inter, sans-serif", size=12, color=THEME_COLORS["text_primary"]),
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def build_readability_figure(df_readability: pd.DataFrame) -> go.Figure:
    """Construye un gráfico de barras horizontales con el índice de legibilidad INFLESZ."""
    if df_readability.empty or "mean_inflesz" not in df_readability.columns:
        return apply_theme_to_figure(go.Figure(), title="Legibilidad Editorial (INFLESZ)")

    df_sorted = df_readability.sort_values(by="mean_inflesz", ascending=True)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df_sorted["mean_inflesz"],
            y=df_sorted["media_name"],
            orientation="h",
            marker=dict(
                color=THEME_COLORS["accent_primary"],
                line=dict(color="rgba(255,255,255,0.15)", width=1),
            ),
            customdata=list(zip(df_sorted["readability_category"], df_sorted["mean_schooling_years"])),
            hovertemplate="<b>%{y}</b><br>Puntaje INFLESZ: <b>%{x:.1f} pts</b><br>Nivel: %{customdata[0]}<br>Años de escolaridad sugeridos: %{customdata[1]:.1f}<extra></extra>",
        )
    )

    # Línea vertical de referencia: Escala Estándar Prensa (55-65 = Normal)
    fig.add_vline(
        x=55.0,
        line_dash="dot",
        line_color=THEME_COLORS["status_warning"],
        line_width=1.5,
        annotation_text="Umbral Prensa (55 pts)",
        annotation_position="bottom right",
        annotation_font=dict(color=THEME_COLORS["status_warning"], size=10),
    )

    fig = apply_theme_to_figure(fig, title="Índice de Legibilidad INFLESZ por Medio")
    fig.update_layout(
        xaxis=dict(
            rangemode="tozero",
            title="Puntaje INFLESZ (Mayor = Más accesible)",
            gridcolor=THEME_COLORS["border"],
        ),
        yaxis=dict(title="", showgrid=False, automargin=True),
        margin=dict(l=20, r=24, t=40, b=30),
    )
    return fig


def build_pos_distribution_figure(df_pos: pd.DataFrame) -> go.Figure:
    """Construye gráfico de barras apiladas al 100% con la distribución morfosintáctica POS."""
    if df_pos.empty or "noun_pct" not in df_pos.columns:
        return apply_theme_to_figure(go.Figure(), title="Perfil Discursivo Gramatical (POS)")

    df_sorted = df_pos.sort_values(by="noun_pct", ascending=True)

    fig = go.Figure()
    # 1. Sustantivos
    fig.add_trace(
        go.Bar(
            x=df_sorted["noun_pct"],
            y=df_sorted["media_name"],
            orientation="h",
            name="Sustantivos",
            marker=dict(color=THEME_COLORS["accent_primary"]),
            hovertemplate="<b>%{y}</b><br>Sustantivos: <b>%{x:.1f}%</b><extra></extra>",
        )
    )
    # 2. Verbos
    fig.add_trace(
        go.Bar(
            x=df_sorted["verb_pct"],
            y=df_sorted["media_name"],
            orientation="h",
            name="Verbos",
            marker=dict(color=THEME_COLORS["status_success"]),
            hovertemplate="<b>%{y}</b><br>Verbos: <b>%{x:.1f}%</b><extra></extra>",
        )
    )
    # 3. Adjetivos
    fig.add_trace(
        go.Bar(
            x=df_sorted["adj_pct"],
            y=df_sorted["media_name"],
            orientation="h",
            name="Adjetivos",
            marker=dict(color=THEME_COLORS["status_warning"]),
            hovertemplate="<b>%{y}</b><br>Adjetivos: <b>%{x:.1f}%</b><extra></extra>",
        )
    )

    fig = apply_theme_to_figure(fig, title="Perfil Discursivo: Distribución Gramatical POS (%)")
    fig.update_layout(
        barmode="stack",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(
            range=[0, 100],
            title="Proporción sobre Palabras de Contenido (%)",
            ticksuffix="%",
            gridcolor=THEME_COLORS["border"],
        ),
        yaxis=dict(title="", showgrid=False, automargin=True),
        margin=dict(l=20, r=24, t=40, b=30),
    )
    return fig


def create_authorship_view(selected_media: str | None = None) -> html.Div:
    """
    Ensambla la vista analítica de 'Autoría y Complejidad'.
    Contiene BANs de género y firma, diagrama Sankey interactivo, legibilidad INFLESZ y POS.
    """
    sankey_data = load_authorship_sankey()
    gender_kpis = load_authorship_gender_kpis()
    df_readability = load_authorship_readability()
    df_pos = load_authorship_pos_distribution()

    if selected_media and selected_media != "ALL":
        df_readability = filter_by_media(df_readability, selected_media)
        df_pos = filter_by_media(df_pos, selected_media)

    # 1. BANs Strip
    signed_pct = gender_kpis.get("signed_pct", 0.0)
    total_signed = gender_kpis.get("total_signed", 0)
    female_ratio = gender_kpis.get("female_ratio_pct", 0.0)
    female_cnt = gender_kpis.get("female_count", 0)
    male_cnt = gender_kpis.get("male_count", 0)
    avg_inflesz = float(df_readability["mean_inflesz"].mean()) if not df_readability.empty else 0.0

    ban_strip = html.Div(
        className="grid grid-cols-4",
        style={"marginBottom": "20px"},
        children=[
            create_kpi_card(
                label="Tasa de Artículos Firmados",
                value=f"{signed_pct:.1f}%",
                note=f"{total_signed:,} noticias con byline explícito",
                icon="✍️",
            ),
            create_kpi_card(
                label="Diversidad de Género (Byline)",
                value=f"{female_ratio:.1f}%",
                note=f"{female_cnt:,} autoras mujeres identificadas",
                icon="👥",
            ),
            create_kpi_card(
                label="Firmas Masculinas",
                value=f"{male_cnt:,}",
                note=f"{100.0 - female_ratio:.1f}% del total identificado",
                icon="👔",
            ),
            create_kpi_card(
                label="Legibilidad Media INFLESZ",
                value=f"{avg_inflesz:.1f} pts",
                note="Nivel Prensa estándar (55-65)",
                icon="📖",
            ),
        ],
    )

    # 2. Main Sankey Flow Chart
    fig_sankey = build_authorship_sankey_figure(sankey_data)
    sankey_card = html.Div(
        className="card",
        style={"marginBottom": "20px", "padding": "16px"},
        children=[
            dcc.Graph(
                id="authorship-sankey-graph",
                figure=fig_sankey,
                config={"displayModeBar": False, "responsive": True},
            )
        ],
    )

    # 3. Bottom Row: INFLESZ Readability + POS Grammar Profile
    fig_read = build_readability_figure(df_readability)
    read_card = html.Div(
        className="card",
        style={"padding": "16px"},
        children=[
            dcc.Graph(
                id="authorship-readability-graph",
                figure=fig_read,
                config={"displayModeBar": False, "responsive": True},
            )
        ],
    )

    fig_pos = build_pos_distribution_figure(df_pos)
    pos_card = html.Div(
        className="card",
        style={"padding": "16px"},
        children=[
            dcc.Graph(
                id="authorship-pos-graph",
                figure=fig_pos,
                config={"displayModeBar": False, "responsive": True},
            )
        ],
    )

    bottom_row = html.Div(
        className="grid grid-cols-12",
        children=[
            html.Div(className="col-6", children=[read_card]),
            html.Div(className="col-6", children=[pos_card]),
        ],
    )

    return html.Div(
        className="view-container",
        children=[
            ban_strip,
            sankey_card,
            bottom_row,
        ],
    )
