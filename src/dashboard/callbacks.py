"""
Registro central de interactividad y callbacks de Plotly Dash.
Conecta la navegación por pestañas y el filtrado cruzado global de medios.
"""
from __future__ import annotations

from dash import Dash, Input, Output, html

from src.dashboard.views.pulse_view import create_pulse_view
from src.dashboard.views.quality_view import create_quality_view
from src.dashboard.views.tone_view import create_tone_view
from src.dashboard.views.authorship_view import create_authorship_view
from src.dashboard.views.geopolitics_view import create_geopolitics_view
from src.dashboard.components.empty_state import create_empty_state


def render_tab_content(active_tab: str, selected_media: str) -> html.Div:
    """Renderiza dinámicamente la vista seleccionada aplicando el filtro global de medio."""
    try:
        if active_tab == "tab-pulse":
            return create_pulse_view(selected_media)
        elif active_tab == "tab-quality":
            return create_quality_view(selected_media)
        elif active_tab == "tab-tone":
            return create_tone_view(selected_media)
        elif active_tab == "tab-authorship":
            return create_authorship_view(selected_media)
        elif active_tab == "tab-geopolitics":
            return create_geopolitics_view(selected_media)
        else:
            return create_pulse_view(selected_media)
    except Exception as e:
        return create_empty_state(
            "Error de visualización",
            f"No fue posible cargar el módulo ({str(e)}). Restablezca los filtros para continuar.",
        )


def reset_media_filter(n_clicks: int) -> str:
    """Restablece el selector global al agregador consolidado 'ALL'."""
    return "ALL"


def register_callbacks(app: Dash) -> None:
    """Registra todos los callbacks interactivos de la aplicación Dash."""
    app.callback(
        Output("tab-content-container", "children"),
        [
            Input("main-tabs", "value"),
            Input("global-media-filter", "value"),
        ],
    )(render_tab_content)

    app.callback(
        Output("global-media-filter", "value"),
        Input("btn-reset-filters", "n_clicks"),
        prevent_initial_call=True,
    )(reset_media_filter)
