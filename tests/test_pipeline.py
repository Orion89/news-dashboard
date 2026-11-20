"""
Pruebas automatizadas de consistencia, configuración, estado y extracción de datos.
Utiliza el módulo estándar unittest para no requerir dependencias adicionales.
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


class TestPipelinePhase1(unittest.TestCase):

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
        self.assertEqual(status["metadata"]["note"], "unit_test")

        state = load_state()
        self.assertIn(test_country, state["countries"])

    def test_db_connection_and_date_sanitization(self):
        """Valida que la conexión a PostgreSQL funcione y descarte fechas corruptas."""
        con = get_duckdb_connection()
        try:
            latest_date = get_latest_valid_date(con, "news_chile")
            self.assertIsNotNone(latest_date)
            # La fecha no debe ser en el año 1 ni en 2036
            self.assertTrue(latest_date.startswith("202"))
        finally:
            con.close()

    def test_extract_news_sanitized_and_cached(self):
        """Valida que la extracción genere un DataFrame sanitizado y guarde Parquet."""
        df = extract_news(country="chile", days=7, force_refresh=True)

        self.assertIsInstance(df, pd.DataFrame)
        self.assertGreater(len(df), 0)
        self.assertIn("body_hash", df.columns)
        self.assertIn("body", df.columns)
        self.assertIn("date", df.columns)

        # Validar que no hay duplicados exactos de body_hash
        self.assertEqual(df["body_hash"].duplicated().sum(), 0)

        # Validar que el archivo Parquet fue creado
        cache_file = RAW_CACHE_DIR / "chile_7d.parquet"
        self.assertTrue(cache_file.exists())

        # Validar lectura desde caché rápida
        df_cached = extract_news(country="chile", days=7, force_refresh=False)
        self.assertEqual(len(df_cached), len(df))


if __name__ == "__main__":
    unittest.main()
