"""La figura del guardián tiene cubo, dos brazos en L y dos puños."""

import pygame

from guardian_renderer import COLOR_FRENTE, COLOR_PUNOS, dibujar_guardian
from game import Juego, COLOR_INMOVILIZADO


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