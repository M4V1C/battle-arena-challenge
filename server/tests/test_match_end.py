import json
import socket
import threading

import pytest

from app.game_config import AlmacenConfiguracion
from app.game_state import EstadoJuego
from app.socket_server import manejar_cliente, procesar_mensaje


def test_reloj_no_avanza_antes_de_empezar():
    juego = EstadoJuego()
    assert juego.avanzar(120)["match"]["elapsed"] == 0


@pytest.mark.parametrize("minutos", [1, 2, 5])
def test_partida_termina_en_minutos_configurados(minutos):
    juego = EstadoJuego()
    juego.iniciar_partida({"condition": "time", "value": minutos})
    assert not juego.avanzar(minutos * 60 - 0.1)["match"]["finished"]
    assert juego.avanzar(0.1)["match"]["finished"]
    final = juego.estado()
    assert juego.avanzar(100) == final
    assert juego.actualizar_entradas({"red": {"x": 1, "y": 0}, "blue": {"x": 0, "y": 0}}) == final


@pytest.mark.parametrize("objetivo", [1, 20, 25, 30])
@pytest.mark.parametrize("nombre", ["red", "blue"])
def test_cualquier_jugador_puede_terminar_por_puntos(objetivo, nombre):
    juego = EstadoJuego()
    juego.iniciar_partida({"condition": "points", "value": objetivo})
    juego._jugadores[nombre].x, juego._jugadores[nombre].y = 740, 430
    entradas = {jugador: {"x": 0, "y": 0, "interact": int(jugador == nombre)} for jugador in ("red", "blue")}
    juego.actualizar_entradas(entradas)
    estado = juego.avanzar(objetivo * 0.5 + 1)
    assert estado["match"]["finished"]
    assert estado["players"][nombre]["score"] == objetivo


def test_configuracion_del_protocolo_se_aplica_al_iniciar(tmp_path):
    almacen = AlmacenConfiguracion(tmp_path / "config.json")
    juego = EstadoJuego()
    configuracion = {"condition": "time", "value": 2, "sensitivity": 3}
    respuesta = json.loads(procesar_mensaje(json.dumps({"type": "save_config", "config": configuracion}), juego, almacen))
    assert respuesta == {"type": "config", "config": configuracion}
    estado = json.loads(procesar_mensaje('{"type":"start"}', juego, almacen))
    assert estado["match"]["condition"] == "time"
    assert estado["match"]["value"] == 2
    almacen.guardar({"condition": "points", "value": 1})
    assert juego.estado()["match"]["value"] == 2


def test_sensibilidad_no_cambia_la_velocidad():
    juego = EstadoJuego(obstaculos=())
    juego.iniciar_partida({"condition": "points", "value": 20, "sensitivity": 5})
    juego.actualizar_entradas({"red": {"x": 1, "y": 0}, "blue": {"x": 0, "y": 0}})
    assert juego.avanzar(0.1)["players"]["red"]["x"] == pytest.approx(124)


def test_solo_se_aplica_la_condicion_seleccionada():
    juego = EstadoJuego()
    juego.iniciar_partida({"condition": "points", "value": 1})
    assert not juego.avanzar(120)["match"]["finished"]
    juego.iniciar_partida({"condition": "time", "value": 1})
    juego._jugadores["red"].x, juego._jugadores["red"].y = 740, 430
    juego.actualizar_entradas({"red": {"x": 0, "y": 0, "interact": 1}, "blue": {"x": 0, "y": 0}})
    estado = juego.avanzar(0.5)
    assert estado["players"]["red"]["score"] == 1
    assert not estado["match"]["finished"]


def test_cerrar_conexion_de_configuracion_no_reinicia_partida(tmp_path):
    almacen = AlmacenConfiguracion(tmp_path / "config.json")
    juego = EstadoJuego()
    juego.iniciar_partida({"condition": "time", "value": 2})
    juego.avanzar(10)
    anterior = juego.estado()
    cliente, servidor = socket.socketpair()
    hilo = threading.Thread(target=manejar_cliente, args=(servidor, ("127.0.0.1", 0), juego, almacen))
    hilo.start()
    try:
        cliente.settimeout(5)
        with cliente, cliente.makefile("r", encoding="utf-8") as lector:
            cliente.sendall(b'{"type":"get_config"}\n')
            assert json.loads(lector.readline())["type"] == "config"
    finally:
        cliente.close()
        hilo.join(timeout=5)
    assert not hilo.is_alive()
    assert juego.estado() == anterior