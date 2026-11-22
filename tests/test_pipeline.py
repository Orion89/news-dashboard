"""
Pruebas automatizadas de consistencia, configuración, estado y módulos analíticos.
Utiliza el módulo estándar unittest.
"""
import unittest
from pathlib import Path
import pandas as pd

from src.pipeline.config import (
    AVAILABLE_COUNTRIES,
    CACHE_DIR,
    DASHBOARD_DIR,
    RAW_CACHE_DIR,
)
from src.pipeline.state import (
    load_state,
    record_module_run,
    get_module_status,
)
from src.pipeline.db import (
    get_duckdb_connection,
    get_latest_valid_date,
    extract_news,
)
from src.pipeline.modules.pulse import (
    process_pulse,
    calculate_volume_and_deltas,
    calculate_hourly_velocity,
    calculate_syndication,
    calculate_length_anomalies,
)
from src.pipeline.modules.quality import (
    process_quality,
    calculate_corpus_integrity,
    calculate_source_health,
)
from src.pipeline.modules.authorship import (
    process_authorship,
    calculate_authorship_and_gender,
    calculate_readability,
    calculate_discourse_pos,
)
from src.pipeline.modules.tone import (
    process_tone,
    extract_emotions_with_cache,
    calculate_temporal_pendulum,
    calculate_sensationalism_index,
    calculate_emerging_ngrams,
)
from src.pipeline.modules.geopolitics import (
    process_geopolitics,
    extract_ner_with_cache,
    calculate_protagonists_and_locations,
)
from src.pipeline.export import (
    generate_manifest,
    verify_dashboard_integrity,
    REQUIRED_DATASETS,
)
from src.pipeline.run import run_pipeline


class TestPipeline(unittest.TestCase):

    def test_directory_structure(self):
        """Valida que los directorios esenciales existan."""
        self.assertTrue(RAW_CACHE_DIR.exists())
        self.assertTrue(CACHE_DIR.exists())
        self.assertTrue(DASHBOARD_DIR.exists())

    def test_state_management(self):
        """Valida el ciclo de vida de registro y lectura de checkpoints de ejecución."""
        test_country = "test_country"
        test_module = "test_module"

        record_module_run(
            country=test_country,
            module_name=test_module,
            status="success",
            records_processed=42,
            metadata={"note": "unit_test"},
        )

        status = get_module_status(test_country, test_module)
        self.assertIsNotNone(status)
        self.assertEqual(status["status"], "success")
        self.assertEqual(status["records_processed"], 42)

    def test_db_connection_and_date_sanitization(self):
        """Valida que la conexión a PostgreSQL funcione y descarte fechas corruptas."""
        con = get_duckdb_connection()
        try:
            latest_date = get_latest_valid_date(con, "news_chile")
            self.assertIsNotNone(latest_date)
            self.assertTrue(latest_date.startswith("202"))
        finally:
            con.close()

    def test_extract_news_sanitized_and_cached(self):
        """Valida que la extracción genere un DataFrame sanitizado y guarde Parquet."""
        df = extract_news(country="chile", days=7, force_refresh=False)

        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
        self.assertIn("body_hash", df.columns)
        self.assertEqual(df["body_hash"].duplicated().sum(), 0)

        cache_file = RAW_CACHE_DIR / "chile_7d.parquet"
        self.assertTrue(cache_file.exists())

    def test_pulse_module(self):
        """Valida la ejecución y consistencia del Módulo 1 (El Pulso)."""
        df = extract_news(country="chile", days=7)
        results = process_pulse(df=df, country="chile", days=7)

        # 1. Validar KPIs
        kpis = results["kpis"]
        self.assertIn("recent_24h_volume", kpis)
        self.assertIn("delta_24h_pct", kpis)
        self.assertIn("syndication_rate_pct", kpis)
        self.assertGreater(kpis["recent_24h_volume"], 0)

        # 2. Validar velocidad horaria
        df_hourly = results["hourly_overall"]
        self.assertFalse(df_hourly.empty)
        self.assertIn("is_peak", df_hourly.columns)
        self.assertIn("news_count", df_hourly.columns)

        # 3. Validar archivos en data/dashboard/
        self.assertTrue((DASHBOARD_DIR / "pulse_kpis.parquet").exists())
        self.assertTrue((DASHBOARD_DIR / "pulse_hourly_velocity.parquet").exists())
        self.assertTrue((DASHBOARD_DIR / "pulse_hourly_top_media.parquet").exists())
        self.assertTrue((DASHBOARD_DIR / "pulse_syndication_by_media.parquet").exists())
        self.assertTrue((DASHBOARD_DIR / "pulse_length_anomalies.parquet").exists())

    def test_quality_module(self):
        """Valida la ejecución y consistencia del Módulo 5 (Calidad de Datos)."""
        df = extract_news(country="chile", days=7)
        results = process_quality(df=df, country="chile", days=7)

        # 1. Validar integridad
        df_integ = results["integrity"]
        self.assertFalse(df_integ.empty)
        self.assertIn("null_pct", df_integ.columns)

        # 2. Validar salud de fuentes (semáforo)
        df_sources = results["sources_health"]
        self.assertFalse(df_sources.empty)
        self.assertIn("status", df_sources.columns)

        # 3. Validar archivos en data/dashboard/
        self.assertTrue((DASHBOARD_DIR / "quality_corpus_integrity.parquet").exists())
        self.assertTrue((DASHBOARD_DIR / "quality_sources_health.parquet").exists())
        self.assertTrue((DASHBOARD_DIR / "quality_summary.parquet").exists())

    def test_authorship_module(self):
        """Valida la ejecución y consistencia del Módulo 3 (Autoría y Complejidad)."""
        df = extract_news(country="chile", days=7)
        results = process_authorship(df=df, country="chile", days=7)

        # 1. Validar Sankey
        sankey = results["sankey"]
        self.assertEqual(len(sankey["nodes"]), 7)
        self.assertEqual(len(sankey["links"]), 6)

        # 2. Validar archivos en data/dashboard/
        self.assertTrue((DASHBOARD_DIR / "authorship_sankey.json").exists())
        self.assertTrue((DASHBOARD_DIR / "authorship_gender_kpis.parquet").exists())
        self.assertTrue((DASHBOARD_DIR / "authorship_media_stats.parquet").exists())
        self.assertTrue((DASHBOARD_DIR / "authorship_readability.parquet").exists())
        self.assertTrue((DASHBOARD_DIR / "authorship_pos_distribution.parquet").exists())

    def test_tone_module(self):
        """Valida la ejecución y consistencia del Módulo 2 (El Tono)."""
        df = extract_news(country="chile", days=7)
        sample_df = df.head(100).copy()
        results = process_tone(df=sample_df, country="chile", days=7, limit_emotions=100)

        # 1. Validar series temporales de emociones
        df_emo = results["emotions_timeseries"]
        self.assertFalse(df_emo.empty)
        self.assertIn("emotion", df_emo.columns)
        self.assertIn("intensity", df_emo.columns)

        # 2. Validar archivos en data/dashboard/
        self.assertTrue((DASHBOARD_DIR / "tone_emotions_timeseries.parquet").exists())
        self.assertTrue((DASHBOARD_DIR / "tone_pendulum_daily.parquet").exists())
        self.assertTrue((DASHBOARD_DIR / "tone_sensationalism_ranking.parquet").exists())
        self.assertTrue((DASHBOARD_DIR / "tone_emerging_ngrams.parquet").exists())

    def test_geopolitics_module(self):
        """Valida la ejecución y consistencia del Módulo 4 (Geopolítico)."""
        df = extract_news(country="chile", days=7)
        sample_df = df.head(100).copy()
        results = process_geopolitics(df=sample_df, country="chile", days=7, limit_ner=100)

        # 1. Validar protagonistas
        df_prot = results["protagonists"]
        self.assertIn("entity", df_prot.columns)
        self.assertIn("total_mentions", df_prot.columns)

        # 2. Validar archivos en data/dashboard/
        self.assertTrue((DASHBOARD_DIR / "geopolitics_protagonists.parquet").exists())
        self.assertTrue((DASHBOARD_DIR / "geopolitics_locations.parquet").exists())

    def test_export_manifest(self):
        """Valida la generación del manifiesto y la verificación de integridad de datasets."""
        manifest = generate_manifest(country="chile", days=7)
        self.assertIn("datasets", manifest)
        self.assertEqual(manifest["total_datasets"], len(REQUIRED_DATASETS))
        self.assertGreater(manifest["total_size_kb"], 0)

        manifest_file = DASHBOARD_DIR / "data_manifest.json"
        self.assertTrue(manifest_file.exists())

        is_valid, errors = verify_dashboard_integrity()
        self.assertTrue(is_valid, f"Errores de integridad detectados: {errors}")

    def test_cli_runner(self):
        """Valida la invocación programática del orquestador CLI."""
        exit_code = run_pipeline(country="chile", days=7, module="export", verify=True)
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
