"""
Configuración central del dashboard, tokens del tema oscuro y plantilla personalizada de Plotly.
"""
from __future__ import annotations

from pathlib import Path
import plotly.graph_objects as go
import plotly.io as pio

# Rutas del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DASHBOARD_DATA_DIR = DATA_DIR / "dashboard"
ASSETS_DIR = PROJECT_ROOT / "assets"

# Tokens cromáticos del Modo Oscuro Contemporáneo (Dark Slate)
THEME_COLORS = {
    # Superficies y fondos
    "bg_base": "#0B0F19",       # Fondo principal de la ventana
    "bg_card": "#1E293B",       # Superficie de las tarjetas
    "bg_card_hover": "#243247", # Hover de tarjetas y filas
    "bg_input": "#0F172A",      # Fondo de controles, dropdowns e inputs
    # Bordes y divisores
    "border": "#334155",        # Borde estándar para tarjetas y ejes
    "border_card": "#334155",   # Borde de 1px sutil para tarjetas
    "border_focus": "#3B82F6",  # Borde al hacer foco
    "border_subtle": "#1E293B", # Divisores internos suaves
    # Textos
    "text_primary": "#F8FAFC",  # Títulos, valores de KPIs y texto destacado
    "text_secondary": "#94A3B8",# Subtítulos, descripciones y etiquetas
    "text_muted": "#64748B",    # Metadatos secundarios, placeholders y ticks
    # Acentos de series analíticas
    "accent_primary": "#3B82F6",   # Azul principal (series, enlaces, selección)
    "accent_blue": "#3B82F6",      # Alias de azul principal
    "accent_secondary": "#8B5CF6", # Violeta (segundas series, géneros)
    "accent_cyan": "#06B6D4",      # Turquesa (organizaciones, conectividad)
    "accent_indigo": "#6366F1",    # Índigo (autores)
    # Semántica de alertas e indicadores
    "status_success": "#10B981", # Verde esmeralda: volumen positivo, scrapers activos
    "status_warning": "#F59E0B", # Ámbar: advertencia, retrasos 24-72h
    "status_danger": "#EF4444",  # Carmesí: picos informativos, alertas, inactividad >72h
    # Paleta cualitativa para gráficos multiserie (máx 7 colores - Miller's Law)
    "series_palette": [
        "#3B82F6", # Azul
        "#10B981", # Esmeralda
        "#F59E0B", # Ámbar
        "#8B5CF6", # Violeta
        "#06B6D4", # Turquesa
        "#EC4899", # Rosa
        "#64748B", # Pizarra (neutro / otros)
    ],
}

# Template de Plotly personalizado: news_dark
# Diseñado para fundirse al 100% con las tarjetas HTML sin marcos ni bordes discordantes.
NEWS_DARK_LAYOUT = go.Layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(
        family='Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        size=12,
        color=THEME_COLORS["text_secondary"],
    ),
    title=dict(
        font=dict(
            family='Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            size=14,
            color=THEME_COLORS["text_primary"],
        ),
        x=0.02,
        xanchor="left",
    ),
    margin=dict(l=40, r=20, t=35, b=30),
    xaxis=dict(
        gridcolor=THEME_COLORS["border_card"],
        gridwidth=1,
        zerolinecolor=THEME_COLORS["border_card"],
        zerolinewidth=1,
        tickfont=dict(color=THEME_COLORS["text_muted"], size=10),
        showline=False,
    ),
    yaxis=dict(
        gridcolor=THEME_COLORS["border_card"],
        gridwidth=1,
        zerolinecolor=THEME_COLORS["border_card"],
        zerolinewidth=1,
        tickfont=dict(color=THEME_COLORS["text_muted"], size=10),
        showline=False,
    ),
    colorway=THEME_COLORS["series_palette"],
    legend=dict(
        font=dict(color=THEME_COLORS["text_secondary"], size=11),
        bgcolor="rgba(0,0,0,0)",
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
    ),
    hoverlabel=dict(
        bgcolor=THEME_COLORS["bg_card"],
        bordercolor=THEME_COLORS["border_card"],
        font=dict(color=THEME_COLORS["text_primary"], size=12),
    ),
)

NEWS_DARK_TEMPLATE = go.layout.Template(layout=NEWS_DARK_LAYOUT)
pio.templates["news_dark"] = NEWS_DARK_TEMPLATE
pio.templates.default = "news_dark"


def apply_theme_to_figure(
    fig: go.Figure,
    height: int | None = None,
    title: str | None = None,
) -> go.Figure:
    """Aplica la plantilla y configuraciones consistentes a cualquier objeto Figure de Plotly."""
    layout_updates: dict[str, Any] = {
        "template": "news_dark",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
    }
    if height is not None:
        layout_updates["height"] = height
    if title is not None:
        layout_updates["title"] = dict(
            text=title,
            font=dict(size=14, color=THEME_COLORS["text_primary"]),
            x=0.02,
            xanchor="left",
        )
    fig.update_layout(**layout_updates)
    return fig
