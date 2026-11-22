"""
Componente Empty State para sobre-filtrado o ausencia de registros.
Proporciona una interfaz amigable con recuperación en un clic (Reset Filters).
"""
from __future__ import annotations

from dash import html


def create_empty_state(
    title: str = "Sin registros para este filtro",
    message: str = "El medio o criterio seleccionado no contiene datos en esta ventana temporal.",
    show_reset_button: bool = True,
    reset_button_id: str = "btn-empty-reset",
) -> html.Div:
    """Construye un estado vacío elegante con pautas de dashboard-ui-engineering."""
    children = [
        html.Div("🔍", className="empty-state-icon"),
        html.H3(title, className="empty-state-title"),
        html.P(message, className="empty-state-description"),
    ]

    if show_reset_button:
        children.append(
            html.Button(
                "Restablecer Filtros",
                id=reset_button_id,
                className="btn-reset",
                style={"marginTop": "8px"},
            )
        )

    return html.Div(children, className="empty-state-card dashboard-card")
