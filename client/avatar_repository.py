
"""Persistencia local de la selección de avatares."""

import json
import os
from pathlib import Path
from threading import Lock


AVATARES_PREDETERMINADOS = tuple(
    f"avatar_{numero}" for numero in range(1, 6)
)
JUGADORES = ("red", "blue")


class RepositorioAvatares:
    """Guarda y recupera las selecciones de los jugadores."""

    def __init__(self, ruta: Path | None = None):
        self._ruta = ruta or (
            Path(__file__).resolve().parent / "data" / "avatars.json"
        )
        self._bloqueo = Lock()

    def obtener(self) -> dict[str, str]:
        """Devuelve la selección almacenada o los valores iniciales."""
        with self._bloqueo:
            if not self._ruta.exists():
                return {
                    "red": "avatar_1",
                    "blue": "avatar_2",
                }

            with self._ruta.open("r", encoding="utf-8") as archivo:
                datos = json.load(archivo)

            if not isinstance(datos, dict):
                raise ValueError("El archivo de avatares no es válido.")

            if any(
                not isinstance(datos.get(jugador), str)
                for jugador in JUGADORES
            ):
                raise ValueError("La selección de avatares está incompleta.")

            return {jugador: datos[jugador] for jugador in JUGADORES}

    def guardar(self, jugador: str, avatar: str) -> None:
        """Actualiza el avatar de un jugador sin perder el del otro."""
        if jugador not in JUGADORES:
            raise ValueError("Jugador no válido.")

        if not isinstance(avatar, str) or not avatar:
            raise ValueError("Avatar no válido.")

        with self._bloqueo:
            # Leer sin volver a adquirir el mismo Lock.
            if self._ruta.exists():
                with self._ruta.open("r", encoding="utf-8") as archivo:
                    datos = json.load(archivo)
                if not isinstance(datos, dict):
                    raise ValueError("El archivo de avatares no es válido.")
            else:
                datos = {"red": "avatar_1", "blue": "avatar_2"}

            datos[jugador] = avatar
            self._ruta.parent.mkdir(parents=True, exist_ok=True)

            temporal = self._ruta.with_suffix(".tmp")
            try:
                with temporal.open("w", encoding="utf-8") as archivo:
                    json.dump(datos, archivo, indent=4, ensure_ascii=False)
                os.replace(temporal, self._ruta)
            finally:
                temporal.unlink(missing_ok=True)
