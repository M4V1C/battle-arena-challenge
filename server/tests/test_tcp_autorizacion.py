"""Mensajes TCP que cambian datos compartidos exigen una conexi\u00f3n con join."""

import base64
import json
import socket
import threading

import pytest

from app.avatar_store import AlmacenAvatares
from app.game_config import AlmacenConfiguracion
from app.game_state import EstadoJuego
from app.socket_server import SesionCliente, manejar_cliente, procesar_mensaje

IMAGEN = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 64).decode()
MENSAJES = {
    "save_config": {"type": "save_config", "config": {"condition": "points", "value": 1, "sensitivity": 1}},
    "select_avatar": {"type": "select_avatar", "player": "blue", "avatar": "avatar_3"},
    "upload_avatar": {"type": "upload_avatar", "player": "red", "image": IMAGEN},
}


@pytest.fixture
def servidor(tmp_path):
    return EstadoJuego(), AlmacenConfiguracion(tmp_path / "config.json"), AlmacenAvatares()


def enviar(servidor, sesion, mensaje, validar_sesion=lambda token: token):
    juego, configuracion, avatares = servidor
    return json.loads(procesar_mensaje(
        json.dumps(mensaje), juego, configuracion, avatares, sesion, validar_sesion
    ))


@pytest.mark.parametrize("tipo", MENSAJES)
def test_sin_join_se_rechaza_con_motivo_y_no_cambia_nada(servidor, tipo):
    _, configuracion, avatares = servidor
    configuracion_antes, avatares_antes = configuracion.obtener(), avatares.obtener()

    respuesta = enviar(servidor, SesionCliente(), MENSAJES[tipo])

    assert respuesta["type"] == "reject"
    assert respuesta["code"] == "not_joined"
    assert "join" in respuesta["message"]
    assert configuracion.obtener() == configuracion_antes
    assert avatares.obtener() == avatares_antes


@pytest.mark.parametrize("tipo", MENSAJES)
def test_con_join_se_acepta(servidor, tipo):
    sesion = SesionCliente()
    assert enviar(servidor, sesion, {"type": "join", "token": "ana"})["type"] == "joined"

    respuesta = enviar(servidor, sesion, MENSAJES[tipo])

    assert respuesta["type"] in ("config", "avatars")


def test_join_con_token_invalido_no_habilita_cambios(servidor):
    sesion = SesionCliente()
    rechazo = enviar(servidor, sesion, {"type": "join", "token": "falso"}, validar_sesion=lambda token: None)

    assert rechazo["code"] == "invalid_token"
    assert enviar(servidor, sesion, MENSAJES["save_config"])["code"] == "not_joined"


def test_las_consultas_siguen_disponibles_sin_join(servidor):
    assert enviar(servidor, SesionCliente(), {"type": "get_config"})["type"] == "config"
    assert enviar(servidor, SesionCliente(), {"type": "get_avatars"})["type"] == "avatars"


def test_el_rechazo_llega_por_el_socket(servidor):
    juego, configuracion, avatares = servidor
    cliente, extremo_servidor = socket.socketpair()
    hilo = threading.Thread(target=manejar_cliente,
                            args=(extremo_servidor, ("127.0.0.1", 0), juego, configuracion, avatares))
    hilo.start()
    try:
        cliente.settimeout(5)
        with cliente, cliente.makefile("r", encoding="utf-8") as lector:
            cliente.sendall((json.dumps(MENSAJES["save_config"]) + "\n").encode("utf-8"))
            respuesta = json.loads(lector.readline())
    finally:
        cliente.close()
        hilo.join(timeout=5)

    assert respuesta["type"] == "reject"
    assert respuesta["code"] == "not_joined"
