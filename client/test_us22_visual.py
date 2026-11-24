"""Los efectos temporales se distinguen en la ventana principal."""

from unittest.mock import Mock

import pygame

from game import Juego, COLOR_ENERGIA_EXTRA, COLOR_SOBRECARGA


def test_icono_extra_y_reactor_sobrecargado():
    pygame.init()
    try:
        juego = Juego.__new__(Juego)
        juego._mensaje = ""
        juego._nombres = {"red": "Rojo", "blue": "Azul"}
        juego._notificaciones = Mock()
        juego._estado = {
            "players": {},
            "energy_items": [{"id": "energia_1", "x": 300, "y": 300,
                              "size": 32, "points": 3}],
            "reactor": {"x": 780, "y": 430, "size": 40,
                        "ring_radius": 60, "status": "overload", "operator": None},
            "events": [{"id": "sobrecarga_1", "type": "overload",
                        "status": "active", "remaining": 2.5}],
        }
        pantalla = pygame.Surface((1600, 900))
        juego._dibujar(pantalla, pygame.font.SysFont(None, 28))
        assert pantalla.get_at((316, 300))[:3] == COLOR_ENERGIA_EXTRA
        assert pantalla.get_at((800, 450))[:3] == COLOR_SOBRECARGA
        assert juego._obtener_estado_reactor(juego._estado["reactor"])[0].startswith("SOBRECARGADO")
    finally:
        pygame.quit()
