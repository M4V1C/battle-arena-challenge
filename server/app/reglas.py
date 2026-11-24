"""Reglas de extracción y guardianes, leídas de server/data/reglas.json."""

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
    duracion_aturdimiento: float = 2.0
    velocidad_guardian: float = 120.0


def validar_reglas(datos: Any) -> Reglas:
    """Valida el contenido de reglas.json. Las claves desconocidas se ignoran."""
    if not isinstance(datos, dict):
        raise ValueError("Las reglas deben ser un objeto JSON.")
    puntos = datos.get("puntos_por_energia")
    intervalo = datos.get("intervalo_extraccion")
    aturdimiento = datos.get("duracion_aturdimiento", 2.0)
    velocidad_guardian = datos.get("velocidad_guardian", 120.0)
    if isinstance(puntos, bool) or not isinstance(puntos, int) or puntos < 1:
        raise ValueError("puntos_por_energia debe ser un entero mayor que cero.")
    if (
        isinstance(intervalo, bool)
        or not isinstance(intervalo, (int, float))
        or not math.isfinite(intervalo)
        or intervalo <= 0
    ):
        raise ValueError("intervalo_extraccion debe ser un número finito mayor que cero.")
    for nombre, valor in (("duracion_aturdimiento", aturdimiento),
                          ("velocidad_guardian", velocidad_guardian)):
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor <= 0:
            raise ValueError(f"{nombre} debe ser un número finito mayor que cero.")
    return Reglas(
        puntos_por_energia=puntos,
        intervalo_extraccion=float(intervalo),
        duracion_aturdimiento=float(aturdimiento),
        velocidad_guardian=float(velocidad_guardian),
    )


def cargar_reglas(ruta: Path = ARCHIVO_REGLAS) -> Reglas:
    with Path(ruta).open(encoding="utf-8") as archivo:
        return validar_reglas(json.load(archivo))
