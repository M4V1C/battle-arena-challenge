"""Dibujo de un cubo guardián con dos brazos en L y puños circulares."""

import pygame

COLOR_FRENTE = (115, 65, 175)
COLOR_SUPERIOR = (175, 125, 225)
COLOR_LATERAL = (75, 40, 125)
COLOR_BRAZOS = (235, 190, 90)
COLOR_PUNOS = (245, 215, 120)


def dibujar_guardian(pantalla: pygame.Surface, centro: tuple[float, float],
                     tamano: float = 40) -> None:
    """El hitbox mide `tamano`; los puños sobresalen solo visualmente."""
    escala = tamano / 40
    cx, cy = centro

    def punto(dx: float, dy: float) -> tuple[int, int]:
        return round(cx + dx * escala), round(cy + dy * escala)

    pygame.draw.polygon(pantalla, COLOR_SUPERIOR,
                        [punto(-13, -13), punto(-8, -19), punto(18, -19), punto(13, -13)])
    pygame.draw.polygon(pantalla, COLOR_LATERAL,
                        [punto(13, -13), punto(18, -19), punto(18, 7), punto(13, 13)])
    pygame.draw.rect(pantalla, COLOR_FRENTE,
                     pygame.Rect(*punto(-13, -13), round(26 * escala), round(26 * escala)))
    pygame.draw.rect(pantalla, COLOR_BRAZOS,
                     pygame.Rect(*punto(-13, -13), round(26 * escala), round(26 * escala)),
                     max(1, round(2 * escala)))
    for lado in (-1, 1):
        pygame.draw.lines(pantalla, COLOR_BRAZOS, False,
                          [punto(lado * 13, -4), punto(lado * 23, -4),
                           punto(lado * 23, 7)], max(2, round(3 * escala)))
        pygame.draw.circle(pantalla, COLOR_PUNOS, punto(lado * 23, 12),
                           max(3, round(6 * escala)))