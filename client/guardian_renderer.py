"""Dibujo de un cubo guardián con dos brazos en L y puños circulares."""

import pygame

COLOR_FRENTE = (115, 65, 175)
COLOR_SUPERIOR = (175, 125, 225)
COLOR_LATERAL = (75, 40, 125)
COLOR_BRAZOS = (235, 190, 90)
COLOR_PUNOS = (245, 215, 120)
# Un color de cuerpo por guardián para distinguirlos entre sí.
COLORES_GUARDIAN = {
    "noroeste": COLOR_FRENTE,
    "noreste": (35, 140, 135),
    "suroeste": (190, 95, 35),
    "sureste": (170, 45, 110),
}
PALETA_GUARDIANES = tuple(COLORES_GUARDIAN.values())


def color_de_guardian(identificador: str | None) -> tuple[int, int, int]:
    """Color estable para un guardián; los que no son de las esquinas usan la paleta."""
    if identificador is None:
        return COLOR_FRENTE
    if identificador in COLORES_GUARDIAN:
        return COLORES_GUARDIAN[identificador]
    return PALETA_GUARDIANES[sum(map(ord, identificador)) % len(PALETA_GUARDIANES)]


def _tono(color: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    """Aclara (factor > 1) u oscurece (factor < 1) un color."""
    if factor >= 1:
        return tuple(round(c + (255 - c) * (factor - 1)) for c in color)
    return tuple(round(c * factor) for c in color)


def dibujar_guardian(pantalla: pygame.Surface, centro: tuple[float, float],
                     tamano: float = 40, identificador: str | None = None) -> None:
    """El hitbox mide `tamano`; los puños sobresalen solo visualmente."""
    escala = tamano / 40
    cx, cy = centro
    frente = color_de_guardian(identificador)
    superior = COLOR_SUPERIOR if frente == COLOR_FRENTE else _tono(frente, 1.4)
    lateral = COLOR_LATERAL if frente == COLOR_FRENTE else _tono(frente, 0.65)

    def punto(dx: float, dy: float) -> tuple[int, int]:
        return round(cx + dx * escala), round(cy + dy * escala)

    pygame.draw.polygon(pantalla, superior,
                        [punto(-13, -13), punto(-8, -19), punto(18, -19), punto(13, -13)])
    pygame.draw.polygon(pantalla, lateral,
                        [punto(13, -13), punto(18, -19), punto(18, 7), punto(13, 13)])
    pygame.draw.rect(pantalla, frente,
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