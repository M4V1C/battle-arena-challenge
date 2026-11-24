"""La figura del guardián tiene cubo, dos brazos en L y dos puños."""

import pygame

from guardian_renderer import (COLOR_FRENTE, COLOR_PUNOS, COLORES_GUARDIAN,
                               color_de_guardian, dibujar_guardian)
from game import Juego, COLOR_INMOVILIZADO


def color_central(identificador):
    pantalla = pygame.Surface((100, 100))
    pantalla.fill((0, 0, 0))
    dibujar_guardian(pantalla, (50, 50), 40, identificador)
    return pantalla.get_at((50, 50))[:3]


def test_cada_guardian_de_las_esquinas_tiene_un_color_distinto():
    colores = [color_central(identificador) for identificador in COLORES_GUARDIAN]

    assert len(set(colores)) == 4
    assert colores == list(COLORES_GUARDIAN.values())


def test_el_color_de_un_guardian_es_estable_y_sale_de_la_paleta():
    assert color_de_guardian("extra_3") == color_de_guardian("extra_3")
    assert color_de_guardian("extra_3") in COLORES_GUARDIAN.values()
    assert color_de_guardian(None) == COLOR_FRENTE


def test_silueta_de_guardian_tiene_cubo_y_dos_punos():
    pygame.init()
    try:
        pantalla = pygame.Surface((100, 100))
        pantalla.fill((0, 0, 0))
        dibujar_guardian(pantalla, (50, 50), 40)
        assert pantalla.get_at((50, 50))[:3] == COLOR_FRENTE
        assert pantalla.get_at((27, 62))[:3] == COLOR_PUNOS
        assert pantalla.get_at((73, 62))[:3] == COLOR_PUNOS
    finally:
        pygame.quit()


def test_hud_muestra_aturdimiento_con_tiempo():
    texto, color = Juego._obtener_estado_jugador({
        "status": "stunned", "stun_remaining": 1.5,
        "frozen": True, "trap": "jaula", "trap_remaining": 2.0,
    })
    assert texto == "Aturdido (1.5s)"
    assert color == COLOR_INMOVILIZADO