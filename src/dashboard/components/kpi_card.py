"""
Componente de tarjeta KPI (Big Ass Number - BAN) para el Top Banner.
Incluye formateo de números tabulares, deltas de tendencia semánticos e iconos.
"""
from __future__ import annotations

from typing import Any
from dash import html


def create_kpi_card(
    label: str,
    value: str | int | float,
    delta: float | None = None,
    delta_text: str | None = None,
    note: str | None = None,
    icon: str | None = None,
    card_id: str | None = None,
) -> html.Div:
    """
    Genera una tarjeta KPI estandarizada con las pautas de dashboard-ui-engineering:
    - Tipografía tabular-nums obligatoria.
    - Delta relativo con clase semántica (positivo/verde o negativo/rojo).
    - Nota de contexto inferior.
    """
    # Formateo del valor
    if isinstance(value, float):
        formatted_val = f"{value:,.1f}"
    elif isinstance(value, int):
        formatted_val = f"{value:,}"
    else:
        formatted_val = str(value)

    # Construcción del badge delta
    delta_element = None
    if delta is not None:
        sign = "+" if delta > 0 else ""
        delta_class = (
            "kpi-delta delta-positive"
            if delta > 0
            else ("kpi-delta delta-negative" if delta < 0 else "kpi-delta delta-neutral")
        )
        subtext = f" {delta_text}" if delta_text else " vs prev"
        arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "—")
        delta_element = html.Span(
            [f"{arrow} {sign}{delta:.1f}%", html.Span(subtext, style={"opacity": "0.75", "fontSize": "10px"})],
            className=delta_class,
        )

    header_children = [html.Span(label, className="kpi-label")]
    if icon:
        header_children.append(html.Span(icon, className="kpi-icon"))

    card_children = [
        html.Div(header_children, className="kpi-header"),
        html.Div(
            [
                html.Span(formatted_val, className="kpi-value tabular-nums"),
                delta_element,
            ],
            className="kpi-value-row",
        ),
    ]

    if note:
        card_children.append(html.Div(note, className="kpi-footer-note"))

    props: dict[str, Any] = {"className": "kpi-card"}
    if card_id:
        props["id"] = card_id

    return html.Div(card_children, **props)
