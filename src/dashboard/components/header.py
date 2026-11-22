"""
Componente Header y Barra Superior de Controles Globales.
Integra selector de medios, metadatos de frescura y botón de restablecimiento.
"""
from __future__ import annotations

from typing import Any
from dash import dcc, html


def create_header(
    manifest: dict[str, Any],
    media_options: list[str],
    current_media: str = "ALL",
) -> html.Header:
    """
    Construye la barra superior fija con el branding, selectores de filtro y metadatos de frescura.
    """
    # Formateo de fecha de actualización
    generated_at = manifest.get("generated_at", "")
    date_display = "Reciente"
    if generated_at:
        try:
            date_display = generated_at[:10]
        except Exception:
            date_display = "Reciente"

    country_name = manifest.get("country", "Chile").capitalize()
    days = manifest.get("window_days", 7)

    # Opciones del dropdown de medios
    dropdown_options = [{"label": "🌐 Todos los medios (Agregado)", "value": "ALL"}]
    for m in media_options:
        dropdown_options.append({"label": m, "value": m})

    return html.Header(
        [
            # Branding & Título
            html.Div(
                [
                    html.Div("NP", className="brand-logo"),
                    html.Div(
                        [
                            html.H1("NewsPulse", className="brand-title"),
                            html.P("Monitoreo de Prensa Escrita & Análisis Semántico", className="brand-subtitle"),
                        ]
                    ),
                ],
                className="brand-section",
            ),
            # Filtros globales y metadatos
            html.Div(
                [
                    # Píldora de País y Ventana
                    html.Div(
                        [
                            html.Span(className="status-dot"),
                            html.Span(f"{country_name} • {days} Días", style={"fontWeight": "700"}),
                            html.Span(f"Actualizado: {date_display}", style={"opacity": "0.75"}),
                        ],
                        className="metadata-pill",
                    ),
                    # Selector de Medio
                    html.Div(
                        [
                            html.Span("Filtrar por Medio:", className="filter-label"),
                            dcc.Dropdown(
                                id="global-media-filter",
                                options=dropdown_options,
                                value=current_media,
                                clearable=False,
                                searchable=True,
                                placeholder="Selecciona un medio...",
                                style={"width": "260px"},
                            ),
                        ],
                        className="filter-item",
                    ),
                    # Botón de Restablecer Filtros
                    html.Button(
                        [
                            html.Span("↺", style={"fontSize": "14px"}),
                            html.Span("Restablecer"),
                        ],
                        id="btn-reset-filters",
                        className="btn-reset",
                        title="Restablece los filtros al estado agregado general",
                    ),
                ],
                className="filter-bar",
            ),
        ],
        className="dashboard-header",
    )
