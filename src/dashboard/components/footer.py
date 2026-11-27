"""
Componente Footer y Metadatos de Autoría del Proyecto.
Incorpora atribución de autoría, perfiles profesionales, enlace al repositorio
y disclaimer de proyecto académico según mejores prácticas de dashboard engineering.
"""
from __future__ import annotations

from dash import html


def create_footer() -> html.Footer:
    """
    Construye el pie de página institucional del dashboard.
    Incluye branding técnico, enlace al repositorio GitHub, redes del autor y disclaimer.
    """
    return html.Footer(
        className="dashboard-footer",
        children=[
            html.Div(
                className="footer-inner",
                children=[
                    # Fila superior: Branding + Acciones (Repo y Redes)
                    html.Div(
                        className="footer-top-row",
                        children=[
                            # Columna Izquierda: Información del proyecto y stack técnico
                            html.Div(
                                className="footer-brand",
                                children=[
                                    html.Span(
                                        "NewsPulse • Plataforma de Inteligencia Editorial y Monitoreo de Prensa Escrita",
                                        className="footer-brand-title",
                                    ),
                                    html.Span(
                                        "Procesamiento analítico con DuckDB, spaCy NER y PySentimiento RoBERTuito. Interfaz interactiva en Plotly Dash.",
                                        className="footer-brand-desc",
                                    ),
                                ],
                            ),
                            # Columna Derecha: Enlace al repositorio y perfiles del autor
                            html.Div(
                                className="footer-actions",
                                children=[
                                    # Botón interactivo al Repositorio en GitHub
                                    html.A(
                                        children=[
                                            html.I(className="bi bi-github", style={"fontSize": "15px"}),
                                            html.Span("Ver Repositorio"),
                                        ],
                                        href="https://github.com/Orion89/news-dashboard",
                                        target="_blank",
                                        rel="noopener noreferrer",
                                        title="Repositorio oficial en GitHub: Orion89/news-dashboard",
                                        className="footer-repo-link",
                                    ),
                                    # Caja de Autor y Redes
                                    html.Div(
                                        className="footer-author-box",
                                        children=[
                                            html.A(
                                                children=[html.I(className="bi bi-github")],
                                                href="https://github.com/Orion89",
                                                target="_blank",
                                                rel="noopener noreferrer",
                                                title="Perfil de GitHub de Leonardo Molina V.",
                                                className="footer-social-icon",
                                            ),
                                            html.A(
                                                children=[html.I(className="bi bi-linkedin")],
                                                href="https://www.linkedin.com/in/leonardo-molina-v-68a601183/",
                                                target="_blank",
                                                rel="noopener noreferrer",
                                                title="Perfil de LinkedIn de Leonardo Molina V.",
                                                className="footer-social-icon",
                                            ),
                                            html.Span(
                                                "2026 Leonardo Molina V.",
                                                style={"fontWeight": "600", "color": "var(--text-secondary)"},
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                    # Divisor sutil
                    html.Div(className="footer-divider"),
                    # Fila inferior: Disclaimer académico de responsabilidad
                    html.Div(
                        className="footer-bottom-row",
                        children=[
                            html.Span(
                                "Proyecto académico. El autor no se hace responsable del mal uso del contenido, métricas o inferencias automatizadas.",
                                style={"fontStyle": "italic"},
                            ),
                            html.Span(
                                "Monitoreo de prensa chilena • Datos procesados y agregados para visualización",
                                style={"opacity": "0.75"},
                            ),
                        ],
                    ),
                ],
            )
        ],
    )
