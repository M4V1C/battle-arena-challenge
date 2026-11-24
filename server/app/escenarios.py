"""Carga y valida los escenarios usados por el servidor."""

import json
import math
import re
from pathlib import Path
from typing import Any


DIRECTORIO_ESCENARIOS = Path(__file__).resolve().parents[1] / "data" / "escenarios"
TAMANO_AVATAR = 40
TAMANO_GUARDIAN = 40
COLORES = ("background", "obstacle", "door_closed", "door_open", "reactor")


def _numero(valor: Any, nombre: str) -> float:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
        raise ValueError(f"{nombre} debe ser un número finito.")
    return float(valor)


def _rectangulo(datos: Any, nombre: str, ancho: int, alto: int) -> dict[str, float]:
    if not isinstance(datos, dict):
        raise ValueError(f"{nombre} debe ser un rectángulo.")
    zona = {clave: _numero(datos.get(clave), f"{nombre}.{clave}")
            for clave in ("x", "y", "width", "height")}
    if (zona["x"] < 0 or zona["y"] < 0 or zona["width"] <= 0 or zona["height"] <= 0
            or zona["x"] + zona["width"] > ancho
            or zona["y"] + zona["height"] > alto):
        raise ValueError(f"{nombre} está fuera de la arena o tiene tamaño inválido.")
    return zona


def _contiene(zona: dict, avatar: dict) -> bool:
    return (zona["x"] <= avatar["x"] and zona["y"] <= avatar["y"]
            and avatar["x"] + avatar["width"] <= zona["x"] + zona["width"]
            and avatar["y"] + avatar["height"] <= zona["y"] + zona["height"])


def _chocan(a: dict, b: dict) -> bool:
    return (a["x"] < b["x"] + b["width"] and a["x"] + a["width"] > b["x"]
            and a["y"] < b["y"] + b["height"] and a["y"] + a["height"] > b["y"])


def validar_escenario(datos: Any) -> dict[str, Any]:
    if not isinstance(datos, dict):
        raise ValueError("El escenario debe ser un objeto JSON.")
    identidad = datos.get("id")
    nombre = datos.get("name")
    if not isinstance(identidad, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", identidad):
        raise ValueError("El id del escenario es inválido.")
    if not isinstance(nombre, str) or not nombre.strip():
        raise ValueError("El escenario necesita un nombre.")
    ancho, alto = datos.get("width"), datos.get("height")
    if (isinstance(ancho, bool) or not isinstance(ancho, int) or ancho < 400
            or isinstance(alto, bool) or not isinstance(alto, int) or alto < 300):
        raise ValueError("Los límites del escenario son inválidos.")

    def lista_rectangulos(clave: str) -> list[dict[str, float]]:
        elementos = datos.get(clave)
        if not isinstance(elementos, list):
            raise ValueError(f"{clave} debe ser una lista.")
        return [_rectangulo(item, f"{clave}[{indice}]", ancho, alto)
                for indice, item in enumerate(elementos)]

    transitables = lista_rectangulos("walkable")
    if not transitables:
        raise ValueError("El escenario necesita zonas transitables.")
    obstaculos = lista_rectangulos("obstacles")
    reactor_bruto = datos.get("reactor")
    if not isinstance(reactor_bruto, dict) or reactor_bruto.get("size") != TAMANO_AVATAR:
        raise ValueError("El reactor debe tener tamaño 40.")
    reactor = _rectangulo({"x": reactor_bruto.get("x"), "y": reactor_bruto.get("y"),
                           "width": TAMANO_AVATAR, "height": TAMANO_AVATAR},
                          "reactor", ancho, alto)
    if not any(_contiene(zona, reactor) for zona in transitables):
        raise ValueError("El reactor debe estar en una zona transitable.")
    if any(_chocan(reactor, obstaculo) for obstaculo in obstaculos):
        raise ValueError("El reactor no puede estar dentro de un obstáculo.")

    puertas_brutas = datos.get("doors")
    if not isinstance(puertas_brutas, list):
        raise ValueError("doors debe ser una lista.")
    puertas = []
    ids = set()
    for indice, puerta in enumerate(puertas_brutas):
        if not isinstance(puerta, dict) or not isinstance(puerta.get("id"), str):
            raise ValueError("Cada puerta necesita un id.")
        if puerta["id"] in ids:
            raise ValueError("Los ids de puertas deben ser únicos.")
        ids.add(puerta["id"])
        zona = _rectangulo(puerta, f"doors[{indice}]", ancho, alto)
        if not any(_contiene(transitable, zona) for transitable in transitables):
            raise ValueError("Una puerta está fuera de las zonas transitables.")
        if _chocan(zona, reactor) or any(_chocan(zona, o) for o in obstaculos):
            raise ValueError("Una puerta se superpone con el reactor o un obstáculo.")
        puertas.append({"id": puerta["id"], **zona})

    posiciones = datos.get("spawns")
    if not isinstance(posiciones, dict) or set(posiciones) != {"red", "blue"}:
        raise ValueError("Se necesitan posiciones iniciales para red y blue.")
    jugadores = {}
    for puesto in ("red", "blue"):
        punto = posiciones[puesto]
        if not isinstance(punto, dict):
            raise ValueError(f"La posición inicial {puesto} es inválida.")
        zona = _rectangulo({"x": punto.get("x"), "y": punto.get("y"),
                           "width": TAMANO_AVATAR, "height": TAMANO_AVATAR},
                          f"spawns.{puesto}", ancho, alto)
        if not any(_contiene(transitable, zona) for transitable in transitables):
            raise ValueError(f"La posición inicial {puesto} no es transitable.")
        if any(_chocan(zona, o) for o in obstaculos + [reactor] + puertas):
            raise ValueError(f"La posición inicial {puesto} choca con un sólido.")
        jugadores[puesto] = zona
    if _chocan(jugadores["red"], jugadores["blue"]):
        raise ValueError("Las posiciones iniciales se superponen.")

    guardianes_brutos = datos.get("guardians")
    if not isinstance(guardianes_brutos, list) or len(guardianes_brutos) < 4:
        raise ValueError("El escenario necesita al menos cuatro guardianes.")
    guardianes = []
    ids = set()
    for indice, guardian in enumerate(guardianes_brutos):
        if not isinstance(guardian, dict) or not isinstance(guardian.get("id"), str):
            raise ValueError("Cada guardián necesita un id.")
        if guardian["id"] in ids:
            raise ValueError("Los ids de guardianes deben ser únicos.")
        ids.add(guardian["id"])
        zona = _rectangulo({"x": guardian.get("x"), "y": guardian.get("y"),
                           "width": TAMANO_GUARDIAN, "height": TAMANO_GUARDIAN},
                          f"guardians[{indice}]", ancho, alto)
        if not any(_contiene(t, zona) for t in transitables):
            raise ValueError("Un guardián está fuera de las zonas transitables.")
        if any(_chocan(zona, o) for o in obstaculos + [reactor] + puertas + list(jugadores.values())):
            raise ValueError("Un guardián aparece dentro de un sólido o un jugador.")
        guardianes.append({"id": guardian["id"], "x": zona["x"], "y": zona["y"]})

    trampas = datos.get("traps")
    if (not isinstance(trampas, list) or len(trampas) != 3
            or not all(isinstance(t, dict) for t in trampas)
            or {t.get("type") for t in trampas} !=
            {"jaula", "arenas", "inversion"}):
        raise ValueError("El escenario necesita las tres trampas distintas.")
    tipos_trampa = []
    for trampa in trampas:
        duracion = _numero(trampa.get("duration"), "traps.duration")
        if duracion <= 0:
            raise ValueError("La duración de una trampa debe ser positiva.")
        tipos_trampa.append({"type": trampa["type"], "duration": duracion})

    tema = datos.get("theme")
    if not isinstance(tema, dict):
        raise ValueError("El escenario necesita un tema visual.")
    colores = {}
    for clave in COLORES:
        color = tema.get(clave)
        if (not isinstance(color, list) or len(color) != 3
                or any(isinstance(c, bool) or not isinstance(c, int) or not 0 <= c <= 255
                       for c in color)):
            raise ValueError(f"El color {clave} es inválido.")
        colores[clave] = color
    return {"id": identidad, "name": nombre, "width": ancho, "height": alto,
            "walkable": transitables, "obstacles": obstaculos, "reactor": reactor,
            "doors": puertas, "spawns": jugadores, "guardians": guardianes,
            "traps": tipos_trampa, "theme": colores}


def cargar_escenario(identidad: str, directorio: Path = DIRECTORIO_ESCENARIOS) -> dict[str, Any]:
    if not isinstance(identidad, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", identidad):
        raise ValueError("El id del escenario es inválido.")
    ruta = Path(directorio) / f"{identidad}.json"
    try:
        with ruta.open(encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except FileNotFoundError as error:
        raise ValueError(f"Escenario desconocido: {identidad}.") from error
    escenario = validar_escenario(datos)
    if escenario["id"] != identidad:
        raise ValueError("El id del archivo no coincide con el escenario.")
    return escenario
