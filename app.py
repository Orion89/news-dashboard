"""
Punto de Entrada Principal (Entrypoint) del Dashboard Web interactivo en Plotly Dash.
Diseñado para alta velocidad, bajo consumo de RAM (< 150 MB) y despliegue autónomo en Railway.
"""
from __future__ import annotations

import os
from dash import Dash, html, dcc

from src.dashboard.config import ASSETS_DIR
from src.dashboard.data_loader import load_manifest, get_available_media_list
from src.dashboard.components.header import create_header
from src.dashboard.components.footer import create_footer
from src.dashboard.views.pulse_view import create_pulse_view
from src.dashboard.callbacks import register_callbacks

# Hojas de estilo externas (Iconos Bootstrap para redes sociales y repositorio)
BOOTSTRAP_ICONS = "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css"

# 1. Inicialización de la aplicación Dash
app = Dash(
    __name__,
    assets_folder=str(ASSETS_DIR),
    external_stylesheets=[BOOTSTRAP_ICONS],
    title="NewsPulse | Monitoreo de Prensa & Inteligencia Semántica",
    update_title=None,
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0, maximum-scale=1.0"},
        {"name": "description", "content": "Dashboard analítico y semántico de monitoreo de prensa chilena."},
    ],
)

# Servidor WSGI exportado para Gunicorn (imprescindible en Railway / Render / AWS)
server = app.server

# 2. Carga de metadatos iniciales
manifest = load_manifest()
media_list = get_available_media_list()

# 3. Ensamblado del Layout Principal
app.layout = html.Div(
    className="dashboard-wrapper",
    children=[
        # Cabecera fija con branding, selector de medio y metadatos
        create_header(manifest, media_list, current_media="ALL"),
        # Barra fija de navegación por pestañas (evita scroll infinito)
        html.Nav(
            className="custom-tabs-container",
            style={"maxWidth": "1440px", "margin": "0 auto", "padding": "0 24px"},
            children=[
                dcc.Tabs(
                    id="main-tabs",
                    value="tab-pulse",
                    className="custom-tabs",
                    children=[
                        dcc.Tab(
                            label="⚡ El Pulso",
                            value="tab-pulse",
                            className="custom-tab",
                            selected_className="custom-tab--selected",
                        ),
                        dcc.Tab(
                            label="🛡️ Calidad de Datos",
                            value="tab-quality",
                            className="custom-tab",
                            selected_className="custom-tab--selected",
                        ),
                        dcc.Tab(
                            label="🎭 El Tono",
                            value="tab-tone",
                            className="custom-tab",
                            selected_className="custom-tab--selected",
                        ),
                        dcc.Tab(
                            label="✍️ Autoría",
                            value="tab-authorship",
                            className="custom-tab",
                            selected_className="custom-tab--selected",
                        ),
                        dcc.Tab(
                            label="📍 Geopolítica",
                            value="tab-geopolitics",
                            className="custom-tab",
                            selected_className="custom-tab--selected",
                        ),
                    ],
                )
            ],
        ),
        # Contenedor dinámico de contenido renderizado por callbacks
        html.Main(
            id="tab-content-container",
            className="dashboard-content",
            style={"maxWidth": "1440px", "margin": "0 auto", "padding": "0 24px 40px"},
            children=create_pulse_view("ALL"),
        ),
        # Pie de página institucional, autoría y metadatos
        create_footer(),
    ],
)

# 4. Registro de interactividad
register_callbacks(app)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=False)
