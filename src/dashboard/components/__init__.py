"""
Componentes visuales reutilizables del dashboard.
"""
from src.dashboard.components.header import create_header
from src.dashboard.components.kpi_card import create_kpi_card
from src.dashboard.components.empty_state import create_empty_state
from src.dashboard.components.footer import create_footer

__all__ = [
    "create_header",
    "create_kpi_card",
    "create_empty_state",
    "create_footer",
]
