"""Carga y validación de escenarios desde archivos JSON."""

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DIRECTORIO_ESCENARIOS = (
    Path(__file__).resolve().parents[1] / "data" / "escenarios"
)


@dataclass(frozen=True)
class Escenario:
    id: str
    nombre: str
    ancho: int
    alto: int
    posiciones: dict[str, tuple[float, float]]
    reactor: tuple[float, float, float, float]
    obstaculos: tuple[tuple[float, float, float, float], ...]
    puertas: tuple[tuple[str, tuple[float, float, float, float]], ...]


def validar_escenario(datos: Any) -> Escenario:
    if not isinstance(datos, dict):
        raise ValueError("El escenario debe ser un objeto JSON.")

    identificador = datos.get("id")
    nombre = datos.get("nombre")

    if not isinstance(identificador, str) or not identificador.strip():
        raise ValueError("El escenario necesita un identificador válido.")

    if not isinstance(nombre, str) or not nombre.strip():
        raise ValueError("El escenario necesita un nombre válido.")

    limites = datos.get("limites")
    if not isinstance(limites, dict):
        raise ValueError("Los límites del escenario son inválidos.")

    ancho = limites.get("ancho")
    alto = limites.get("alto")

    if (
        type(ancho) is not int
        or type(alto) is not int
        or ancho <= 0
        or alto <= 0
    ):
        raise ValueError("Las dimensiones deben ser enteros positivos.")

    def numero(valor: Any, campo: str) -> float:
        if (
            isinstance(valor, bool)
            or not isinstance(valor, (int, float))
            or not math.isfinite(valor)
        ):
            raise ValueError(f"Valor numérico inválido: {campo}.")
        return float(valor)

    def rectangulo(elemento: Any, nombre_elemento: str):
        if not isinstance(elemento, dict):
            raise ValueError(f"{nombre_elemento} debe ser un objeto.")

        x = numero(elemento.get("x"), "x")
        y = numero(elemento.get("y"), "y")
        w = numero(elemento.get("ancho"), "ancho")
        h = numero(elemento.get("alto"), "alto")

        if w <= 0 or h <= 0:
            raise ValueError(f"{nombre_elemento} tiene dimensiones inválidas.")

        if x < 0 or y < 0 or x + w > ancho or y + h > alto:
            raise ValueError(f"{nombre_elemento} está fuera de la arena.")

        return (x, y, w, h)

    reactor = rectangulo(datos.get("reactor"), "Reactor")

    obstaculos_json = datos.get("obstaculos")
    if not isinstance(obstaculos_json, list):
        raise ValueError("Los obstáculos deben ser una lista.")

    obstaculos = tuple(
        rectangulo(item, "Obstáculo") for item in obstaculos_json
    )

    puertas_json = datos.get("puertas")
    if not isinstance(puertas_json, list):
        raise ValueError("Las puertas deben ser una lista.")

    puertas = []
    ids_puertas = set()

    for item in puertas_json:
        if not isinstance(item, dict):
            raise ValueError("Cada puerta debe ser un objeto.")

        puerta_id = item.get("id")
        if not isinstance(puerta_id, str) or not puerta_id.strip():
            raise ValueError("Una puerta tiene un identificador inválido.")

        if puerta_id in ids_puertas:
            raise ValueError("Hay identificadores de puertas duplicados.")

        ids_puertas.add(puerta_id)
        puertas.append((puerta_id, rectangulo(item, "Puerta")))

    posiciones_json = datos.get("posiciones_iniciales")
    if not isinstance(posiciones_json, dict):
        raise ValueError("Faltan las posiciones iniciales.")

    posiciones = {}
    tamano_jugador = 40

    for puesto in ("red", "blue"):
        posicion = posiciones_json.get(puesto)

        if not isinstance(posicion, dict):
            raise ValueError(f"Falta la posición de {puesto}.")

        x = numero(posicion.get("x"), "x")
        y = numero(posicion.get("y"), "y")

        jugador = (x, y, tamano_jugador, tamano_jugador)

        if x < 0 or y < 0 or x + tamano_jugador > ancho or y + tamano_jugador > alto:
            raise ValueError(f"Posición inicial inválida: {puesto}.")

        def colisiona(a, b):
            return (
                a[0] < b[0] + b[2]
                and a[0] + a[2] > b[0]
                and a[1] < b[1] + b[3]
                and a[1] + a[3] > b[1]
            )

        if any(colisiona(jugador, obstaculo) for obstaculo in obstaculos):
            raise ValueError(f"{puesto} aparece dentro de un obstáculo.")

        if colisiona(jugador, reactor):
            raise ValueError(f"{puesto} aparece dentro del reactor.")

        if any(colisiona(jugador, zona) for _, zona in puertas):
            raise ValueError(f"{puesto} aparece dentro de una puerta.")

        posiciones[puesto] = (x, y)

    return Escenario(
        id=identificador,
        nombre=nombre,
        ancho=ancho,
        alto=alto,
        posiciones=posiciones,
        reactor=reactor,
        obstaculos=obstaculos,
        puertas=tuple(puertas),
    )


def cargar_escenario(
    identificador: str,
    directorio: Path = DIRECTORIO_ESCENARIOS,
) -> Escenario:
    if identificador not in ("arena_clasica", "laberinto"):
        raise ValueError("El escenario solicitado no existe.")

    ruta = Path(directorio) / f"{identificador}.json"

    with ruta.open(encoding="utf-8") as archivo:
        datos = json.load(archivo)

    escenario = validar_escenario(datos)

    if escenario.id != identificador:
        raise ValueError("El identificador del archivo no coincide.")

    return escenario
