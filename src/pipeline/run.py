"""
Orquestador CLI principal para el pipeline de procesamiento de datos del News Dashboard.
Permite ejecutar todo el pipeline de punta a punta o submódulos individuales por país y ventana temporal.
"""
from __future__ import annotations

import os

# Prevenir colisión de OpenMP runtime en Windows antes de importar torch o numpy
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import argparse
import sys
import time
from typing import Any
import torch

from src.pipeline.config import AVAILABLE_COUNTRIES, DEFAULT_COUNTRY, DEFAULT_WINDOW_DAYS
from src.pipeline.db import extract_news
from src.pipeline.export import generate_manifest, print_dashboard_catalog, verify_dashboard_integrity
from src.pipeline.modules.authorship import process_authorship
from src.pipeline.modules.geopolitics import process_geopolitics
from src.pipeline.modules.pulse import process_pulse
from src.pipeline.modules.quality import process_quality
from src.pipeline.modules.tone import process_tone
from src.pipeline.state import record_module_run


def get_hardware_info() -> str:
    """Detecta el dispositivo de aceleración de hardware disponible."""
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        return f"CUDA Acelerado ({device_name})"
    return "CPU (Sin aceleración CUDA)"


def run_pipeline(
    country: str = DEFAULT_COUNTRY,
    days: int = DEFAULT_WINDOW_DAYS,
    module: str = "all",
    force_refresh: bool = False,
    limit_nlp: int | None = None,
    batch_size: int = 256,
    verify: bool = True,
) -> int:
    """
    Ejecuta el pipeline de procesamiento según los parámetros dados.
    Retorna 0 si es exitoso, o código distinto de 0 en caso de fallo.
    """
    country_key = country.lower().strip()
    if country_key not in AVAILABLE_COUNTRIES:
        print(f"[ERROR] País '{country}' no válido. Opciones: {list(AVAILABLE_COUNTRIES.keys())}")
        return 1

    start_total = time.time()
    hw_info = get_hardware_info()

    print("=" * 80)
    print("NEWS DASHBOARD DATA PIPELINE - ORQUESTADOR")
    print(f"País: {country_key.upper()} | Ventana: {days} días | Módulo: {module.upper()} | Hardware: {hw_info}")
    print("=" * 80)

    # Si solo se solicitó exportación y catálogo
    if module == "export":
        manifest = generate_manifest(country=country_key, days=days)
        print_dashboard_catalog(manifest)
        is_valid, errors = verify_dashboard_integrity()
        if not is_valid:
            print("[ADVERTENCIA] Errores de integridad detectados:")
            for err in errors:
                print(f"  - {err}")
            return 1
        return 0

    # 1. Extracción o carga de datos cacheados
    t0 = time.time()
    print(f"\n[1/6] Extrayendo datos sanitizados para {country_key} ({days} días)...")
    try:
        df = extract_news(country=country_key, days=days, force_refresh=force_refresh)
        print(f"  ✓ Datos cargados: {len(df):,} noticias ({time.time() - t0:.2f}s)")
    except Exception as e:
        print(f"  ✗ Error en la extracción: {e}")
        return 1

    modules_to_run = (
        ["pulse", "quality", "authorship", "tone", "geopolitics"]
        if module == "all"
        else [module]
    )

    execution_stats: dict[str, float] = {}

    # 2. Ejecutar módulos seleccionados
    if "pulse" in modules_to_run:
        t_mod = time.time()
        print("\n[2/6] Ejecutando Módulo 1: El Pulso (Volumen, Velocidad, Sindicación, Longitud)...")
        try:
            pulse_res = process_pulse(df=df, country=country_key, days=days)
            kpis = pulse_res["kpis"]
            execution_stats["pulse"] = time.time() - t_mod
            print(f"  ✓ Pulso completado ({execution_stats['pulse']:.2f}s)")
            print(f"    - Volumen 24h: {kpis['recent_24h_volume']} (Delta: {kpis['delta_24h_pct']}%)")
            print(f"    - Tasa Sindicación: {kpis['syndication_rate_pct']}% ({kpis['syndicated_articles_count']} cables)")
        except Exception as e:
            print(f"  ✗ Error en El Pulso: {e}")
            return 1

    if "quality" in modules_to_run:
        t_mod = time.time()
        print("\n[3/6] Ejecutando Módulo 5: Calidad de Datos y Salud de Fuentes...")
        try:
            qual_res = process_quality(df=df, country=country_key, days=days)
            summary = qual_res["summary"]
            execution_stats["quality"] = time.time() - t_mod
            print(f"  ✓ Calidad completada ({execution_stats['quality']:.2f}s)")
            print(f"    - Fuentes evaluadas: {summary['total_sources_evaluated']} (Score: {summary['health_score_pct']}%)")
            print(f"    - Semáforo: Verde={summary['sources_green']} | Amarillo={summary['sources_yellow']} | Rojo={summary['sources_red']}")
        except Exception as e:
            print(f"  ✗ Error en Calidad: {e}")
            return 1

    if "authorship" in modules_to_run:
        t_mod = time.time()
        print("\n[4/6] Ejecutando Módulo 3: Autoría y Complejidad (Sankey, Género, INFLESZ, POS)...")
        try:
            auth_res = process_authorship(df=df, country=country_key, days=days)
            g_kpis = auth_res["gender_kpis"]
            execution_stats["authorship"] = time.time() - t_mod
            print(f"  ✓ Autoría completada ({execution_stats['authorship']:.2f}s)")
            print(f"    - Notas firmadas: {g_kpis['signed_pct']}% | Participación femenina: {g_kpis['female_ratio_pct']}%")
            print(f"    - Medios con legibilidad evaluada: {len(auth_res['readability'])}")
        except Exception as e:
            print(f"  ✗ Error en Autoría: {e}")
            return 1

    if "tone" in modules_to_run:
        t_mod = time.time()
        print(f"\n[5/6] Ejecutando Módulo 2: El Tono (Emociones RoBERTuito, Péndulo, Sensacionalismo, N-gramas)...")
        try:
            tone_res = process_tone(df=df, country=country_key, days=days, limit_emotions=limit_nlp)
            execution_stats["tone"] = time.time() - t_mod
            print(f"  ✓ Tono completado ({execution_stats['tone']:.2f}s)")
            print(f"    - Trending topics detectados: {len(tone_res['emerging_ngrams'])}")
            print(f"    - Medios en ranking de sensacionalismo: {len(tone_res['sensationalism_ranking'])}")
        except Exception as e:
            print(f"  ✗ Error en El Tono: {e}")
            return 1

    if "geopolitics" in modules_to_run:
        t_mod = time.time()
        print(f"\n[6/6] Ejecutando Módulo 4: Geopolítico (NER spaCy, Localidades, Protagonistas)...")
        try:
            geo_res = process_geopolitics(df=df, country=country_key, days=days, limit_ner=limit_nlp)
            execution_stats["geopolitics"] = time.time() - t_mod
            print(f"  ✓ Geopolítico completado ({execution_stats['geopolitics']:.2f}s)")
            print(f"    - Protagonistas catalogados: {len(geo_res['protagonists'])}")
            print(f"    - Localidades georreferenciadas: {len(geo_res['locations'])}")
        except Exception as e:
            print(f"  ✗ Error en Geopolítico: {e}")
            return 1

    # 3. Compilación del manifiesto
    print("\n[Compilando catálogo y manifiesto de datos para Plotly Dash...]")
    manifest = generate_manifest(country=country_key, days=days)
    record_module_run(
        country=country_key,
        module_name="pipeline_full",
        status="success",
        records_processed=len(df),
        metadata={
            "days": days,
            "modules_executed": modules_to_run,
            "total_size_kb": manifest["total_size_kb"],
            "total_elapsed_seconds": round(time.time() - start_total, 2),
        },
    )

    # 4. Verificación de integridad si se solicita
    if verify:
        is_valid, errors = verify_dashboard_integrity()
        if not is_valid:
            print("[ADVERTENCIA] Errores en la verificación de integridad:")
            for err in errors:
                print(f"  - {err}")
        else:
            print("  ✓ Integridad 100% verificada para todos los datasets del dashboard.")

    print_dashboard_catalog(manifest)
    total_time = time.time() - start_total
    print(f"\nPIPELINE FINALIZADO CON ÉXITO EN {total_time:.2f} SEGUNDOS.")
    print("=" * 80)
    return 0


def main() -> None:
    """Punto de entrada de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Orquestador CLI para el procesamiento de datos del News Dashboard."
    )
    parser.add_argument(
        "--country",
        default=DEFAULT_COUNTRY,
        help=f"País de la tabla de noticias a procesar. Por defecto: {DEFAULT_COUNTRY}.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_WINDOW_DAYS,
        help=f"Ventana de días a analizar. Por defecto: {DEFAULT_WINDOW_DAYS}.",
    )
    parser.add_argument(
        "--module",
        choices=["all", "pulse", "quality", "authorship", "tone", "geopolitics", "export"],
        default="all",
        help="Módulo específico a ejecutar (o 'all' para el flujo completo).",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Fuerza la re-extracción de datos desde PostgreSQL ignorando la caché cruda.",
    )
    parser.add_argument(
        "--limit-nlp",
        type=int,
        default=None,
        help="Límite opcional de noticias para inferencia pesada (útil para pruebas rápidas).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=256,
        help="Tamaño de lote para modelos de Deep Learning (PySentimiento y spaCy).",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Omite la verificación final de integridad de datasets.",
    )

    args = parser.parse_args()

    exit_code = run_pipeline(
        country=args.country,
        days=args.days,
        module=args.module,
        force_refresh=args.force_refresh,
        limit_nlp=args.limit_nlp,
        batch_size=args.batch_size,
        verify=not args.no_verify,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
