import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any


ARCHIVO_CONFIGURACION = Path(__file__).resolve().parents[1] / "data" / "game_config.json"
CONFIGURACION_INICIAL = {"condition": "points", "value": 20, "sensitivity": 1.0}


def validar_configuracion(datos: Any) -> dict[str, Any]:
    if not isinstance(datos, dict):
        raise ValueError("La configuracion debe ser un objeto JSON.")
    condicion = datos.get("condition")
    valor = datos.get("value")
    sensibilidad = datos.get("sensitivity", 1.0)
    if condicion not in ("points", "time"):
        raise ValueError("La condicion debe ser points o time.")
    if isinstance(valor, bool) or not isinstance(valor, int) or valor < 1:
        raise ValueError("El limite debe ser un entero mayor que cero.")
    if (
        isinstance(sensibilidad, bool)
        or not isinstance(sensibilidad, (int, float))
        or not 0 < sensibilidad < float("inf")
    ):
        raise ValueError("La sensibilidad debe ser un numero positivo finito.")
    return {"condition": condicion, "value": valor, "sensitivity": sensibilidad}


class AlmacenConfiguracion:
    def __init__(self, ruta: Path = ARCHIVO_CONFIGURACION):
        self.ruta = ruta
        self._bloqueo = threading.Lock()
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        if self.ruta.exists():
            with self.ruta.open(encoding="utf-8") as archivo:
                self._datos = validar_configuracion(json.load(archivo))
        else:
            self.guardar(CONFIGURACION_INICIAL)

    def obtener(self) -> dict[str, Any]:
        with self._bloqueo:
            return dict(self._datos)

    def guardar(self, datos: Any) -> dict[str, Any]:
        configuracion = validar_configuracion(datos)
        with self._bloqueo:
            temporal = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", dir=self.ruta.parent, delete=False
                ) as archivo:
                    temporal = Path(archivo.name)
                    json.dump(configuracion, archivo, indent=2, allow_nan=False)
                    archivo.write("\n")
                os.replace(temporal, self.ruta)
                self._datos = configuracion
            finally:
                if temporal is not None:
                    temporal.unlink(missing_ok=True)
            return dict(self._datos)