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

    # Establecemos un ganador para evitar un empate.
    juego._jugadores["red"].puntos = 5
    juego._jugadores["blue"].puntos = 3

    # La partida no debe terminar antes del tiempo configurado.
    assert not juego.avanzar(minutos * 60 - 0.1)["match"]["finished"]

    # Al alcanzar el tiempo, debe finalizar y declarar ganador.
    estado = juego.avanzar(0.1)

    assert estado["match"]["finished"] is True
    assert estado["match"]["winner"] == "red"
    assert estado["match"]["elapsed"] == pytest.approx(minutos * 60)
    assert estado["match"]["overtime"] == 0

    # Después de finalizar, el estado no debe cambiar.
    final = juego.estado()

    assert juego.avanzar(100) == final
    assert juego.actualizar_entradas({
        "red": {"x": 1, "y": 0},
        "blue": {"x": 0, "y": 0},
    }) == final

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
    estados = []
    for sensibilidad in (1, 5):
        juego = EstadoJuego(obstaculos=())
        juego.iniciar_partida({"condition": "points", "value": 20, "sensitivity": sensibilidad})
        juego.actualizar_entradas({"red": {"x": 0, "y": 1}, "blue": {"x": 0, "y": 0}})
        estados.append(juego.avanzar(0.1))
    assert estados[0] == estados[1]
    assert estados[0]["players"]["red"]["x"] > 100


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

def test_declara_ganador_por_puntos():
    juego = EstadoJuego()
    juego.iniciar_partida({"condition": "points", "value": 5})

    juego._jugadores["red"].puntos = 4
    juego._jugadores["blue"].puntos = 2

    juego._jugadores["red"].x = 740
    juego._jugadores["red"].y = 430

    juego.actualizar_entradas({
        "red": {"x": 0, "y": 0, "interact": 1},
        "blue": {"x": 0, "y": 0},
    })

    estado = juego.avanzar(0.5)

    assert estado["match"]["finished"] is True
    assert estado["match"]["winner"] == "red"
    assert estado["players"]["red"]["score"] == 5
    assert estado["players"]["blue"]["score"] == 2


def test_empate_activa_prorroga_de_dos_minutos():
    juego = EstadoJuego()
    juego.iniciar_partida({"condition": "time", "value": 1})

    juego._jugadores["red"].puntos = 5
    juego._jugadores["blue"].puntos = 5

    estado = juego.avanzar(60)

    # Un empate no debe finalizar definitivamente la partida.
    assert estado["match"]["finished"] is False
    assert estado["match"]["winner"] is None

    # Deben conservarse los puntos.
    assert estado["players"]["red"]["score"] == 5
    assert estado["players"]["blue"]["score"] == 5

    # La prórroga agrega dos minutos al límite original.
    assert estado["match"]["elapsed"] == pytest.approx(60)
    assert estado["match"]["time_limit"] == pytest.approx(180)
    assert estado["match"]["overtime"] == 1

    # Los jugadores regresan a sus posiciones iniciales.
    assert estado["players"]["red"]["x"] == 100
    assert estado["players"]["red"]["y"] == 100
    assert estado["players"]["blue"]["x"] == 1460
    assert estado["players"]["blue"]["y"] == 760

def test_empate_repite_prorrogas_hasta_haber_ganador():
    juego = EstadoJuego()
    juego.iniciar_partida({"condition": "time", "value": 1})

    juego._jugadores["red"].puntos = 5
    juego._jugadores["blue"].puntos = 5

    # Termina el minuto reglamentario con empate.
    primera = juego.avanzar(60)

    assert primera["match"]["finished"] is False
    assert primera["match"]["overtime"] == 1
    assert primera["match"]["time_limit"] == pytest.approx(180)

    # Termina la primera prórroga y persiste el empate.
    segunda = juego.avanzar(120)

    assert segunda["match"]["finished"] is False
    assert segunda["match"]["winner"] is None
    assert segunda["match"]["overtime"] == 2
    assert segunda["match"]["elapsed"] == pytest.approx(180)
    assert segunda["match"]["time_limit"] == pytest.approx(300)

    # Durante la segunda prórroga, rojo obtiene más puntos.
    juego._jugadores["red"].puntos = 6

    # Se cumple el límite de la segunda prórroga.
    final = juego.avanzar(120)

    assert final["match"]["finished"] is True
    assert final["match"]["winner"] == "red"
    assert final["match"]["overtime"] == 2
    assert final["match"]["elapsed"] == pytest.approx(300)
    assert final["players"]["red"]["score"] == 6
    assert final["players"]["blue"]["score"] == 5

def test_empate_por_puntos_activa_prorroga_de_dos_minutos():
    juego = EstadoJuego()
    juego.iniciar_partida({"condition": "points", "value": 5})

    # Ambos jugadores alcanzaron el puntaje objetivo.
    juego._jugadores["red"].puntos = 5
    juego._jugadores["blue"].puntos = 5

    estado = juego.avanzar(0)

    assert estado["match"]["finished"] is False
    assert estado["match"]["winner"] is None
    assert estado["match"]["overtime"] == 1
    assert estado["match"]["time_limit"] == pytest.approx(120)

    # Los puntajes deben conservarse.
    assert estado["players"]["red"]["score"] == 5
    assert estado["players"]["blue"]["score"] == 5

    # Durante la prórroga, rojo consigue un punto adicional.
    juego._jugadores["red"].puntos = 6

    # La partida no debe terminar antes de los dos minutos.
    intermedio = juego.avanzar(119)

    assert intermedio["match"]["finished"] is False
    assert intermedio["match"]["winner"] is None

    # Al terminar la prórroga se declara ganador.
    final = juego.avanzar(1)

    assert final["match"]["finished"] is True
    assert final["match"]["winner"] == "red"
    assert final["match"]["overtime"] == 1