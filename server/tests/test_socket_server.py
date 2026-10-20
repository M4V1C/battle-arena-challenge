import json
import math
import socket
import threading

import pytest

from app.game_state import EstadoJuego
from app.socket_server import crear_socket_servidor, procesar_mensaje, servir


def posiciones(estado: dict) -> dict:
    return {
        nombre: {"x": j["x"], "y": j["y"]} for nombre, j in estado["players"].items()
    }


def test_estado_inicial_tiene_dos_jugadores():
    """El estado inicial incluye las posiciones de ambos jugadores."""
    estado = EstadoJuego().estado()

    assert posiciones(estado) == {
        "red": {"x": 100, "y": 100},
        "blue": {"x": 1460, "y": 760},
    }


def test_mover_actualiza_los_dos_jugadores_independientemente():
    """Las entradas producen movimiento independiente para cada jugador."""
    juego = EstadoJuego()

    juego.actualizar_entradas(
        {
            "red": {"x": 0, "y": 1},
            "blue": {"x": 0, "y": -1},
        }
    )
    estado = juego.avanzar(1 / 60)

    radio = juego.VELOCIDAD / juego.VELOCIDAD_GIRO
    angulo = juego.VELOCIDAD_GIRO / 60
    assert posiciones(estado)["red"] == pytest.approx({
        "x": 100 + radio * math.sin(angulo), "y": 100 + radio * (1 - math.cos(angulo))
    })
    assert posiciones(estado)["blue"] == pytest.approx({
        "x": 1460 - radio * math.sin(angulo), "y": 760 - radio * (1 - math.cos(angulo))
    })


def test_velocidad_no_depende_de_la_frecuencia_de_actualizacion():
    """El mismo tiempo simulado produce la misma distancia en varios ticks."""
    juego = EstadoJuego()
    juego.actualizar_entradas(
        {
            "red": {"x": 0, "y": 1},
            "blue": {"x": 0, "y": 0},
        }
    )

    for _ in range(30):
        juego.avanzar(1 / 60)
    estado_30_fps = juego.estado()["players"]["red"]["x"]

    otro_juego = EstadoJuego()
    otro_juego.actualizar_entradas(
        {
            "red": {"x": 0, "y": 1},
            "blue": {"x": 0, "y": 0},
        }
    )
    for _ in range(60):
        otro_juego.avanzar(1 / 120)
    estado_120_fps = otro_juego.estado()["players"]["red"]["x"]

    esperado = 100 + juego.VELOCIDAD / juego.VELOCIDAD_GIRO
    assert estado_30_fps == pytest.approx(esperado)
    assert estado_120_fps == pytest.approx(esperado)


def test_movimiento_diagonal_mantiene_la_misma_velocidad():
    """La normalización evita que desplazarse en diagonal sea más rápido."""
    juego = EstadoJuego()
    juego.actualizar_entradas(
        {
            "red": {"x": 1, "y": 1},
            "blue": {"x": 0, "y": 0},
        }
    )

    estado = juego.avanzar(1 / 60)
    jugador = estado["players"]["red"]
    distancia = math.hypot(jugador["x"] - 100, jugador["y"] - 100)

    esperado = 2 * juego.VELOCIDAD / juego.VELOCIDAD_GIRO * math.sin(juego.VELOCIDAD_GIRO / 120)
    assert distancia == pytest.approx(esperado)


def test_desconectar_detiene_el_movimiento():
    """El servidor deja de mover a los jugadores al cerrar el cliente."""
    juego = EstadoJuego()
    juego.actualizar_entradas(
        {
            "red": {"x": 1, "y": 0},
            "blue": {"x": 0, "y": 0},
        }
    )
    juego.detener_movimiento()

    estado = juego.avanzar(1.0)

    assert posiciones(estado)["red"] == {"x": 100, "y": 100}


def test_movimientos_concurrentes_no_pierden_actualizaciones():
    """Las actualizaciones de hilos distintos se aplican sin interferirse."""
    juego = EstadoJuego()

    def mover_rojo():
        for _ in range(20):
            juego.avanzar(1 / 60)

    def mover_azul():
        for _ in range(20):
            juego.avanzar(1 / 60)

    juego.actualizar_entradas(
        {
            "red": {"x": 0, "y": 1},
            "blue": {"x": 0, "y": -1},
        }
    )
    hilos = [
        threading.Thread(target=mover_rojo),
        threading.Thread(target=mover_azul),
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    estado = juego.estado()
    radio = juego.VELOCIDAD / juego.VELOCIDAD_GIRO
    assert estado["players"]["red"]["x"] == pytest.approx(100 + radio)
    distancia_recta = juego.VELOCIDAD * (40 / 60 - math.pi / 2 / juego.VELOCIDAD_GIRO)
    assert estado["players"]["red"]["y"] == pytest.approx(100 + radio + distancia_recta)
    assert estado["players"]["blue"]["y"] == pytest.approx(760 - radio - distancia_recta)


def test_mover_limita_jugadores_a_la_arena():
    """Los jugadores no pueden salir de los límites de la ventana."""
    juego = EstadoJuego()
    juego._jugadores["red"].x, juego._jugadores["red"].y = 0, 0
    juego._jugadores["red"].dir_x, juego._jugadores["red"].dir_y = -1, 0
    juego._jugadores["blue"].x, juego._jugadores["blue"].y = 1560, 860
    juego._jugadores["blue"].dir_x, juego._jugadores["blue"].dir_y = 1, 0

    juego.actualizar_entradas(
        {
            "red": {"x": 0, "y": -1},
            "blue": {"x": 0, "y": 1},
        }
    )
    for _ in range(400):
        juego.avanzar(1 / 60)

    estado = juego.estado()
    assert posiciones(estado)["red"] == {"x": 0, "y": 0}
    assert posiciones(estado)["blue"] == {"x": 1560, "y": 860}


@pytest.mark.parametrize(
    "entrada",
    [
        {"red": {"x": 2, "y": 0}, "blue": {"x": 0, "y": 0}},
        {"red": {"x": True, "y": 0}, "blue": {"x": 0, "y": 0}},
        {"red": {"x": 0, "y": 0}},
    ],
)
def test_mover_rechaza_entradas_invalidas(entrada):
    """Las direcciones mal formadas no modifican el estado del juego."""
    juego = EstadoJuego()

    with pytest.raises(ValueError):
        juego.actualizar_entradas(entrada)

    assert posiciones(juego.estado())["red"] == {"x": 100, "y": 100}


def test_procesar_mensaje_devuelve_estado_json():
    """El protocolo TCP expone snapshots serializados como JSON."""
    respuesta = procesar_mensaje('{"type":"state"}', EstadoJuego())

    assert json.loads(respuesta)["type"] == "state"


def test_procesar_mensaje_reporta_errores_de_protocolo():
    """Los mensajes inválidos reciben una respuesta de error estructurada."""
    respuesta = json.loads(procesar_mensaje("no-json", EstadoJuego()))

    assert respuesta["type"] == "error"


def test_intercambio_por_socket():
    """Un cliente TCP puede consultar el estado inicial del servidor."""
    servidor = crear_socket_servidor("127.0.0.1", 0)
    threading.Thread(target=servir, args=(servidor,), daemon=True).start()

    try:
        with socket.create_connection(
            ("127.0.0.1", servidor.getsockname()[1]), timeout=5
        ) as conn:
            conn.sendall(b'{"type":"state"}\n')
            with conn.makefile("r", encoding="utf-8") as lector:
                respuesta = json.loads(lector.readline())
        assert set(respuesta["players"]) == {"red", "blue"}
    finally:
        servidor.close()
