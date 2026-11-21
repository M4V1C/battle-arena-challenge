"""La arena distingue barreras, puertas y trampas sin recursos externos."""

import pygame
from unittest.mock import Mock

from game import Juego, FONDO, COLOR_PUERTA_CERRADA, COLOR_PUERTA_ABIERTA, COLORES_TRAMPA
from avatar_renderer import RenderizadorAvatares


def test_puerta_y_trampas_tienen_colores_distintos():
    pygame.init()
    try:
        juego = Juego.__new__(Juego)
        juego._mensaje = ""
        juego._nombres = {"red": "Rojo", "blue": "Azul"}
        juego._notificaciones = Mock()
        juego._estado = {
            "players": {},
            "obstacles": [{"x": 10, "y": 100, "width": 40, "height": 40}],
            "doors": [{"x": 100, "y": 100, "width": 40, "height": 40, "open": False}],
            "traps": [
                {"x": 200 + i * 100, "y": 100, "width": 64, "height": 64, "type": tipo}
                for i, tipo in enumerate(("jaula", "arenas", "inversion"))
            ],
        }
        pantalla = pygame.Surface((1600, 900))
        juego._dibujar(pantalla, pygame.font.SysFont(None, 28))
        assert pantalla.get_at((120, 120))[:3] == COLOR_PUERTA_CERRADA
        for i, tipo in enumerate(("jaula", "arenas", "inversion")):
            assert pantalla.get_at((205 + i * 100, 105))[:3] == COLORES_TRAMPA[tipo]
        juego._estado["doors"][0]["open"] = True
        juego._dibujar(pantalla, pygame.font.SysFont(None, 28))
        assert pantalla.get_at((100, 100))[:3] == COLOR_PUERTA_ABIERTA
        assert pantalla.get_at((120, 120))[:3] == FONDO
    finally:
        pygame.quit()


def test_trampa_de_inversion_gira_el_indicador_del_avatar():
    pygame.init()
    try:
        pantalla = pygame.Surface((100, 100))
        RenderizadorAvatares().dibujar(pantalla, pygame.Vector2(50, 50),
                                     pygame.Vector2(1, 0), "sin_imagen", 40, invertido=True)
        assert pantalla.get_at((35, 50))[:3] == (255, 255, 255)
        assert pantalla.get_at((65, 50))[:3] != (255, 255, 255)
    finally:
        pygame.quit()
