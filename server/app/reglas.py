"""Reglas de puntuación y extracción, leídas de server/data/reglas.json."""

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ARCHIVO_REGLAS = Path(__file__).resolve().parents[1] / "data" / "reglas.json"


@dataclass(frozen=True)
class Reglas:
    # Puntos que recibe el operador del reactor en cada extracción.
    puntos_por_energia: int
    # Segundos de operación continua del reactor entre una extracción y la siguiente.
    intervalo_extraccion: float


def validar_reglas(datos: Any) -> Reglas:
    """Valida el contenido de reglas.json. Las claves desconocidas se ignoran."""
    if not isinstance(datos, dict):
        raise ValueError("Las reglas deben ser un objeto JSON.")
    puntos = datos.get("puntos_por_energia")
    intervalo = datos.get("intervalo_extraccion")
    if isinstance(puntos, bool) or not isinstance(puntos, int) or puntos < 1:
        raise ValueError("puntos_por_energia debe ser un entero mayor que cero.")
    if (
        isinstance(intervalo, bool)
        or not isinstance(intervalo, (int, float))
        or not math.isfinite(intervalo)
        or intervalo <= 0
    ):
        raise ValueError("intervalo_extraccion debe ser un número finito mayor que cero.")
    return Reglas(puntos_por_energia=puntos, intervalo_extraccion=float(intervalo))


def cargar_reglas(ruta: Path = ARCHIVO_REGLAS) -> Reglas:
    with Path(ruta).open(encoding="utf-8") as archivo:
        return validar_reglas(json.load(archivo))