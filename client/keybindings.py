# Carga las teclas de cada jugador desde un archivo JSON local.

import json
from pathlib import Path

import pygame

ARCHIVO = Path(__file__).with_name("keybindings.json")
ACCIONES = ("up", "down", "left", "right", "shoot", "interact")
JUGADORES = ("red", "blue")

# Devuelve {jugador: {accion: codigo_pygame}} validando el archivo.
def cargar_keybindings(ruta: Path = ARCHIVO) -> dict[str, dict[str, int]]:
    with ruta.open(encoding="utf-8") as archivo:
        datos = json.load(archivo)

    teclas: dict[str, dict[str, int]] = {}
    for jugador in JUGADORES:
        config = datos.get(jugador)
        if not isinstance(config, dict):
            raise ValueError(f"Faltan las teclas del jugador '{jugador}' en {ruta.name}.")
        teclas[jugador] = {}
        for accion in ACCIONES:
            nombre = config.get(accion)
            if not isinstance(nombre, str):
                raise ValueError(f"Falta la tecla '{accion}' de '{jugador}' en {ruta.name}.")
            try:
                teclas[jugador][accion] = pygame.key.key_code(nombre)
            except ValueError:
                raise ValueError(f"Tecla desconocida '{nombre}' para '{jugador}.{accion}'.") from None
    return teclas
