"""La selección llega al inicio y los colores salen del estado compartido."""

from unittest.mock import Mock, patch
from pathlib import Path
import socket
import threading
import time

import pygame

from game import Juego
from local_match_network import ConexionPartidaLocal
from screens import Aplicacion
from importlib import import_module

def test_la_pantalla_envia_el_escenario_elegido_al_juego():
    pygame.init()
    try:
        app = Aplicacion("127.0.0.1", 9000)
        app.usuarios.jugador_rojo = "ana"
        app.usuarios.jugador_azul = "beto"
        app._selector_escenarios.seleccionado = "laberinto"
        with patch("screens.Juego") as juego:
            juego.return_value.ejecutar.return_value = True
            app._iniciar_juego()
        juego.assert_called_once_with("127.0.0.1", 9000, "ana", "beto",
                                      escenario="laberinto")
    finally:
        pygame.quit()


def test_la_arena_usa_el_tema_recibido_del_servidor():
    pygame.init()
    try:
        juego = Juego.__new__(Juego)
        juego._mensaje = ""
        juego._nombres = {"red": "Rojo", "blue": "Azul"}
        juego._notificaciones = Mock()
        juego._estado = {
            "players": {},
            "scenario": {"id": "laberinto", "name": "Laberinto",
                         "theme": {"background": [20, 38, 47], "obstacle": [58, 111, 126],
                                   "door_closed": [215, 90, 105], "door_open": [85, 225, 195],
                                   "reactor": [110, 235, 240]},
                         "walkable": [{"x": 0, "y": 0, "width": 1600, "height": 900}]},
            "obstacles": [{"x": 300, "y": 180, "width": 40, "height": 240}],
            "doors": [{"x": 620, "y": 300, "width": 40, "height": 120, "open": False}],
            "reactor": {"x": 780, "y": 360, "size": 40,
                        "ring_radius": 60, "status": "available", "operator": None},
        }
        pantalla = pygame.Surface((1600, 900))
        juego._dibujar(pantalla, pygame.font.SysFont(None, 28))
        assert pantalla.get_at((100, 300))[:3] == (20, 38, 47)
        assert pantalla.get_at((310, 200))[:3] == (58, 111, 126)
        assert pantalla.get_at((630, 320))[:3] == (215, 90, 105)
        assert pantalla.get_at((800, 380))[:3] == (110, 235, 240)
    finally:
        pygame.quit()


def test_ventana_local_inicia_laberinto_con_dos_sesiones(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "server"))
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "server"))
    EstadoJuego = import_module("app.game_state").EstadoJuego
    manejar_cliente = import_module("app.socket_server").manejar_cliente

    juego = EstadoJuego(semilla=5)
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.bind(("127.0.0.1", 0))
    servidor.listen(2)
    servidor.settimeout(5)
    hilos = []

    def aceptar():
        for _ in range(2):
            cliente, direccion = servidor.accept()
            hilo = threading.Thread(target=manejar_cliente,
                                    args=(cliente, direccion, juego), daemon=True)
            hilos.append(hilo)
            hilo.start()

    aceptador = threading.Thread(target=aceptar, daemon=True)
    aceptador.start()
    conexion = ConexionPartidaLocal("127.0.0.1", servidor.getsockname()[1],
                                   {"red": "ana", "blue": "beto"}, "laberinto")
    try:
        limite = time.monotonic() + 5
        estado = None
        while estado is None and time.monotonic() < limite:
            estado = conexion.obtener_estado()
            time.sleep(0.01)
        assert estado is not None and estado["type"] == "state"
        assert estado["match"]["started"]
        assert estado["scenario"]["id"] == "laberinto"
        conexion.enviar_entradas({"red": {"x": 0, "y": 0, "interact": 0, "shoot": 0},
                                 "blue": {"x": 0, "y": 0, "interact": 0, "shoot": 0}})
        siguiente = None
        while siguiente is None and time.monotonic() < limite:
            siguiente = conexion.obtener_estado()
            time.sleep(0.01)
        assert siguiente is not None and siguiente["scenario"]["id"] == "laberinto"
    finally:
        conexion.cerrar()
        servidor.close()
        aceptador.join(timeout=1)
        for hilo in hilos:
            hilo.join(timeout=1)
