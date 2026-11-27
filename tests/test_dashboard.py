"""
Pruebas automatizadas para los cimientos del frontend: configuración, data loader y componentes base.
"""
import unittest
import pandas as pd
import plotly.graph_objects as go
from dash import html

from src.dashboard.config import (
    THEME_COLORS,
    NEWS_DARK_TEMPLATE,
    apply_theme_to_figure,
)
from src.dashboard.data_loader import (
    load_manifest,
    load_pulse_kpis,
    load_hourly_velocity,
    load_authorship_sankey,
    load_tone_emotions_timeseries,
    load_geopolitics_protagonists,
    load_quality_summary,
    get_available_media_list,
    filter_by_media,
)
from src.dashboard.components.kpi_card import create_kpi_card
from src.dashboard.components.header import create_header
from src.dashboard.components.footer import create_footer
from src.dashboard.components.empty_state import create_empty_state
from src.dashboard.views.pulse_view import (
    build_pulse_velocity_figure,
    build_pulse_syndication_figure,
    create_pulse_anomalies_component,
    create_pulse_view,
)
from src.dashboard.views.quality_view import (
    build_corpus_integrity_figure,
    create_sources_health_table,
    create_quality_view,
)
from src.dashboard.views.tone_view import (
    build_emotions_timeseries_figure,
    build_sensationalism_ranking_figure,
    build_pendulum_gauge_figure,
    create_emerging_ngrams_component,
    create_tone_view,
)
from src.dashboard.views.authorship_view import (
    build_authorship_sankey_figure,
    build_readability_figure,
    build_pos_distribution_figure,
    create_authorship_view,
)
from src.dashboard.views.geopolitics_view import (
    build_locations_map_figure,
    build_protagonists_figure,
    create_geopolitics_view,
)


class TestDashboardBase(unittest.TestCase):

    def test_config_and_theme(self):
        """Valida que los tokens de color y la plantilla Plotly Dark existan y se apliquen."""
        self.assertIn("bg_base", THEME_COLORS)
        self.assertIn("bg_card", THEME_COLORS)
        self.assertIn("text_primary", THEME_COLORS)
        self.assertIn("status_success", THEME_COLORS)
        self.assertIn("status_danger", THEME_COLORS)

        # Validar aplicación del template a una figura
        fig = go.Figure(data=go.Scatter(x=[1, 2], y=[10, 20]))
        fig = apply_theme_to_figure(fig, title="Test Plot")
        self.assertEqual(fig.layout.template.layout.paper_bgcolor, "rgba(0,0,0,0)")
        self.assertEqual(fig.layout.title.text, "Test Plot")

    def test_data_loader(self):
        """Valida la carga en memoria de datasets y extracción de medios disponibles."""
        manifest = load_manifest()
        self.assertIn("datasets", manifest)
        self.assertEqual(manifest["total_datasets"], 19)

        # Carga de KPIs y dataframes
        kpis = load_pulse_kpis()
        self.assertIn("recent_24h_volume", kpis)

        df_hourly = load_hourly_velocity()
        self.assertFalse(df_hourly.empty)
        self.assertIn("news_count", df_hourly.columns)

        sankey = load_authorship_sankey()
        self.assertIn("nodes", sankey)
        self.assertIn("links", sankey)

        df_emotions = load_tone_emotions_timeseries()
        self.assertFalse(df_emotions.empty)

        df_prot = load_geopolitics_protagonists()
        self.assertFalse(df_prot.empty)

        qual_sum = load_quality_summary()
        self.assertIn("total_sources_evaluated", qual_sum)

        # Lista de medios
        media_list = get_available_media_list()
        self.assertGreater(len(media_list), 0)

        # Filtrado por medio
        sample_media = media_list[0]
        df_filtered = filter_by_media(df_hourly, sample_media)
        # Si df_hourly no tiene media_name, retorna intacto
        self.assertIsInstance(df_filtered, pd.DataFrame)

    def test_kpi_card_component(self):
        """Valida la generación del componente KPI card y sus clases semánticas."""
        card_positive = create_kpi_card(
            label="Volumen 24h",
            value=890,
            delta=15.4,
            delta_text="vs ayer",
            note="Promedio diario: 800",
            icon="⚡",
        )
        self.assertIsInstance(card_positive, html.Div)

        card_negative = create_kpi_card(
            label="Sindicación",
            value="5.4%",
            delta=-2.3,
            delta_text="vs prev",
        )
        self.assertIsInstance(card_negative, html.Div)

    def test_header_and_empty_state_components(self):
        """Valida la construcción del header, footer y empty state."""
        manifest = load_manifest()
        media_list = get_available_media_list()
        header = create_header(manifest, media_list, current_media="ALL")
        self.assertIsInstance(header, html.Header)

        footer = create_footer()
        self.assertIsInstance(footer, html.Footer)

        empty_state = create_empty_state("Sin datos", "Intente cambiar el medio.")
        self.assertIsInstance(empty_state, html.Div)

    def test_pulse_view(self):
        """Valida la generación de figuras y componentes de la vista El Pulso."""
        df_velocity = load_hourly_velocity()
        fig_vel = build_pulse_velocity_figure(df_velocity)
        self.assertIsInstance(fig_vel, go.Figure)
        self.assertGreater(len(fig_vel.data), 0)

        from src.dashboard.data_loader import load_syndication_media, load_length_anomalies
        df_syn = load_syndication_media()
        fig_syn = build_pulse_syndication_figure(df_syn)
        self.assertIsInstance(fig_syn, go.Figure)
        self.assertGreater(len(fig_syn.data), 0)

        df_anom = load_length_anomalies()
        comp_anom = create_pulse_anomalies_component(df_anom)
        self.assertIsInstance(comp_anom, html.Div)

        view = create_pulse_view()
        self.assertIsInstance(view, html.Div)

    def test_quality_view(self):
        """Valida la generación de figuras y tablas de la vista Calidad de Datos."""
        from src.dashboard.data_loader import load_quality_corpus_integrity, load_quality_sources_health
        df_integ = load_quality_corpus_integrity()
        fig_integ = build_corpus_integrity_figure(df_integ)
        self.assertIsInstance(fig_integ, go.Figure)
        self.assertGreater(len(fig_integ.data), 0)

        df_sources = load_quality_sources_health()
        table = create_sources_health_table(df_sources)
        self.assertTrue(hasattr(table, "data"))
        self.assertGreater(len(table.data), 0)

        view = create_quality_view()
        self.assertIsInstance(view, html.Div)

    def test_tone_view(self):
        """Valida la generación de figuras y componentes de la vista El Tono."""
        from src.dashboard.data_loader import (
            load_tone_emotions_timeseries,
            load_tone_sensationalism_ranking,
            load_tone_pendulum_daily,
            load_tone_emerging_ngrams,
        )
        df_emotions = load_tone_emotions_timeseries()
        fig_emo = build_emotions_timeseries_figure(df_emotions)
        self.assertIsInstance(fig_emo, go.Figure)

        df_sens = load_tone_sensationalism_ranking()
        fig_sens = build_sensationalism_ranking_figure(df_sens)
        self.assertIsInstance(fig_sens, go.Figure)

        df_pen = load_tone_pendulum_daily()
        fig_gauge = build_pendulum_gauge_figure(df_pen)
        self.assertIsInstance(fig_gauge, go.Figure)

        df_ngrams = load_tone_emerging_ngrams()
        comp_ng = create_emerging_ngrams_component(df_ngrams)
        self.assertIsInstance(comp_ng, html.Div)

        view = create_tone_view()
        self.assertIsInstance(view, html.Div)

    def test_authorship_view(self):
        """Valida la generación de figuras y componentes de la vista Autoría y Complejidad."""
        from src.dashboard.data_loader import (
            load_authorship_sankey,
            load_authorship_readability,
            load_authorship_pos_distribution,
        )
        sankey = load_authorship_sankey()
        fig_sankey = build_authorship_sankey_figure(sankey)
        self.assertIsInstance(fig_sankey, go.Figure)

        df_read = load_authorship_readability()
        fig_read = build_readability_figure(df_read)
        self.assertIsInstance(fig_read, go.Figure)

        df_pos = load_authorship_pos_distribution()
        fig_pos = build_pos_distribution_figure(df_pos)
        self.assertIsInstance(fig_pos, go.Figure)

        view = create_authorship_view()
        self.assertIsInstance(view, html.Div)

    def test_geopolitics_view(self):
        """Valida la generación del mapa de Chile y radar de actores de la vista Geopolítica."""
        from src.dashboard.data_loader import (
            load_geopolitics_locations,
            load_geopolitics_protagonists,
        )
        df_loc = load_geopolitics_locations()
        fig_map = build_locations_map_figure(df_loc)
        self.assertIsInstance(fig_map, go.Figure)

        df_prot = load_geopolitics_protagonists()
        fig_per = build_protagonists_figure(df_prot, entity_type="PER")
        self.assertIsInstance(fig_per, go.Figure)

        fig_org = build_protagonists_figure(df_prot, entity_type="ORG")
        self.assertIsInstance(fig_org, go.Figure)

        view = create_geopolitics_view()
        self.assertIsInstance(view, html.Div)

    def test_app_and_callbacks(self):
        """Valida que app.py instancie el layout, exporte server y que los callbacks respondan."""
        from app import app, server
        self.assertIsNotNone(server)
        self.assertIsNotNone(app.layout)

        # Validar llamada a los callbacks registrados
        from src.dashboard.callbacks import render_tab_content, reset_media_filter
        
        # Test cambio de cada tab
        for tab_id in ["tab-pulse", "tab-quality", "tab-tone", "tab-authorship", "tab-geopolitics"]:
            content = render_tab_content(tab_id, "ALL")
            self.assertIsInstance(content, html.Div)

        # Test restablecimiento de filtro
        res = reset_media_filter(1)
        self.assertEqual(res, "ALL")


if __name__ == "__main__":
    unittest.main()
