"""El cliente de develop dibuja el escenario y trampas del motor integrado."""

from unittest.mock import Mock

import pygame

from game import Juego


def test_escenario_con_trampa_guardian_y_reactor_se_dibuja():
    pygame.init()
    try:
        juego = Juego.__new__(Juego)
        juego._mensaje = ""
        juego._nombres = {"red": "Rojo", "blue": "Azul"}
        juego._puesto = "red"
        juego._notificaciones = Mock()
        juego._estado = {
            "players": {},
            "scenario": {
                "name": "Laberinto",
                "theme": {
                    "background": [20, 38, 47],
                    "obstacle": [58, 111, 126],
                    "door_closed": [215, 90, 105],
                    "door_open": [85, 225, 195],
                    "reactor": [110, 235, 240],
                },
                "walkable": [{"x": 0, "y": 0, "width": 1600, "height": 900}],
            },
            "obstacles": [{"x": 300, "y": 180, "width": 40, "height": 240}],
            "doors": [{"x": 620, "y": 300, "width": 40, "height": 120, "open": False}],
            "traps": [{"x": 100, "y": 100, "width": 64, "height": 64, "type": "jaula"}],
            "guardians": [{"x": 1400, "y": 700, "size": 40, "temporary": False}],
            "reactor": {"x": 780, "y": 360, "size": 40,
                        "ring_radius": 60, "status": "available", "operator": None},
        }
        pantalla = pygame.Surface((1600, 900))
        juego._dibujar(pantalla, pygame.font.SysFont(None, 28))
        assert pantalla.get_at((50, 300))[:3] == (20, 38, 47)
        assert pantalla.get_at((310, 200))[:3] == (58, 111, 126)
        assert pantalla.get_at((630, 320))[:3] == (215, 90, 105)
        assert pantalla.get_at((800, 380))[:3] == (110, 235, 240)
    finally:
        pygame.quit()
