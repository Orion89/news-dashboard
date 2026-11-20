"""
Gestor de estado y puntos de control (checkpoints) para resiliencia ante límites de cuota y cortes de ejecución.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .config import CACHE_DIR

STATE_FILE = CACHE_DIR / "pipeline_state.json"


def load_state() -> dict[str, Any]:
    """Carga el archivo de estado de ejecución o crea uno inicial si no existe."""
    if not STATE_FILE.exists():
        initial_state = {
            "version": "1.0",
            "last_updated": None,
            "countries": {},
            "history": [],
        }
        save_state(initial_state)
        return initial_state

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"version": "1.0", "last_updated": None, "countries": {}, "history": []}


def save_state(state: dict[str, Any]) -> None:
    """Guarda el estado del pipeline de manera atómica."""
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    temp_file = STATE_FILE.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    temp_file.replace(STATE_FILE)


def record_module_run(
    country: str,
    module_name: str,
    status: str,
    records_processed: int,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Registra la ejecución exitosa o con error de un módulo específico."""
    state = load_state()
    now_str = datetime.now(timezone.utc).isoformat()

    if country not in state["countries"]:
        state["countries"][country] = {"modules": {}, "last_extraction": None}

    state["countries"][country]["modules"][module_name] = {
        "status": status,
        "records_processed": records_processed,
        "completed_at": now_str,
        "metadata": metadata or {},
    }

    state["history"].append({
        "timestamp": now_str,
        "country": country,
        "module": module_name,
        "status": status,
        "records_processed": records_processed,
    })

    # Mantener historial acotado a los últimos 100 eventos
    if len(state["history"]) > 100:
        state["history"] = state["history"][-100:]

    save_state(state)


def get_module_status(country: str, module_name: str) -> dict[str, Any] | None:
    """Obtiene el estado del último procesamiento de un módulo."""
    state = load_state()
    return state.get("countries", {}).get(country, {}).get("modules", {}).get(module_name)
