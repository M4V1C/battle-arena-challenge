"""Almacena una partida finalizada una sola vez por identificador."""

import json
import logging
import os
import sys
import tempfile
import threading
from importlib import import_module
from pathlib import Path
from typing import Any, Callable


ARCHIVO_RESULTADOS = Path(__file__).resolve().parents[1] / "data" / "resultados.json"
_BLOQUEO = threading.Lock()


def _actualizar_perfiles(resultado: dict[str, Any]) -> None:
    ruta_usuarios = Path(__file__).resolve().parents[2] / "Epica 01-Gestion de usuarios"
    if not ruta_usuarios.is_dir():
        return
    if str(ruta_usuarios) not in sys.path:
        sys.path.insert(0, str(ruta_usuarios))
    registrar_partida = import_module("perfil_datos").registrar_partida
    ganador = resultado["winner"]
    for puesto, jugador in resultado["players"].items():
        if jugador["username"]:
            registrar_partida(
                jugador["username"],
                "victoria" if puesto == ganador else "derrota",
                jugador["score"],
                int(resultado["elapsed"]),
            )


def guardar_resultado(
    resultado: dict[str, Any],
    ruta: Path = ARCHIVO_RESULTADOS,
    actualizar_perfiles: Callable[[dict[str, Any]], None] | None = _actualizar_perfiles,
) -> bool:
    """Persiste el resultado; False indica que ese id ya estaba guardado."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with _BLOQUEO:
        if ruta.exists():
            with ruta.open(encoding="utf-8") as archivo:
                resultados = json.load(archivo)
            if not isinstance(resultados, list):
                raise ValueError("El archivo de resultados es inválido.")
        else:
            resultados = []
        if any(r.get("id") == resultado["id"] for r in resultados):
            return False
        resultados.append(resultado)
        temporal = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=ruta.parent, delete=False
            ) as archivo:
                temporal = Path(archivo.name)
                json.dump(resultados, archivo, indent=2, ensure_ascii=False)
                archivo.write("\n")
                archivo.flush()
                os.fsync(archivo.fileno())
            os.replace(temporal, ruta)
        finally:
            if temporal is not None:
                temporal.unlink(missing_ok=True)
        if actualizar_perfiles is not None:
            try:
                actualizar_perfiles(resultado)
            except (ImportError, OSError, ValueError) as error:
                logging.getLogger(__name__).warning("Resultado guardado, perfil pendiente: %s", error)
        return True
