"""
Configuración central, rutas de directorios y parámetros del pipeline.
"""
from __future__ import annotations

import os

# Prevenir colisión de OpenMP runtime en entornos Windows con PyTorch + MKL
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from pathlib import Path

# Localización de rutas raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

# Base de datos
POSTGRES_URI = os.getenv(
    "POSTGRES_URI",
    "postgresql://postgres:0rioN-689@192.168.1.85:5432/news"
)

# Rutas de almacenamiento de datos
DATA_DIR = PROJECT_ROOT / "data"
RAW_CACHE_DIR = DATA_DIR / "raw_cache"
CACHE_DIR = DATA_DIR / "cache"
DASHBOARD_DIR = DATA_DIR / "dashboard"

# Crear directorios automáticamente si no existen
for directory in [DATA_DIR, RAW_CACHE_DIR, CACHE_DIR, DASHBOARD_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Mapeo de países soportados a sus tablas en PostgreSQL
AVAILABLE_COUNTRIES: dict[str, str] = {
    "chile": "news_chile",
    "argentina": "news_argentina",
    "bolivia": "news_bolivia",
    "colombia": "news_colombia",
    "costa_rica": "news_costa_rica",
    "ecuador": "news_ecuador",
    "espana": "news_espana",
    "estados_unidos": "news_estados_unidos",
    "guatemala": "news_guatemala",
    "internacional": "news_internacional",
    "mexico": "news_mexico",
    "nicaragua": "news_nicaragua",
    "panama": "news_panama",
    "peru": "news_peru",
    "religion": "news_religion",
    "rep_dominicana": "news_rep_dominicana",
    "tecnologia": "news_tecnologia",
    "uruguay": "news_uruguay",
    "venezuela": "news_venezuela",
    "video_juegos": "news_video_juegos",
}

# Parámetros por defecto
DEFAULT_COUNTRY = "chile"
DEFAULT_WINDOW_DAYS = 7
MIN_VALID_YEAR = 2020
DEFAULT_NLP_BATCH_SIZE = 256
