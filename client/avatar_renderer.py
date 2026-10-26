
"""Representación gráfica de los avatares dentro de la arena."""

import pygame

from avatar_repository import AVATARES_PREDETERMINADOS
from avatar_images import obtener_ruta_avatar

COLORES_AVATAR = (
    (225, 75, 75),
    (70, 140, 230),
    (75, 195, 120),
    (220, 170, 65),
    (170, 105, 220),
)


class RenderizadorAvatares:
    """Dibuja los avatares conservando la orientación del jugador."""

    def __init__(self):
        self._colores = dict(zip(AVATARES_PREDETERMINADOS, COLORES_AVATAR))
        self._imagenes: dict[str, pygame.Surface] = {}
    def dibujar(self,pantalla: pygame.Surface,centro: pygame.Vector2,direccion: pygame.Vector2,avatar: str,tamano: int,) -> None:
        """Dibuja un avatar con una indicación de orientación."""
        color = self._colores.get(avatar, COLORES_AVATAR[0])

        ruta = obtener_ruta_avatar(avatar)

        if ruta is not None:
            if avatar not in self._imagenes:
                try:
                    imagen = pygame.image.load(str(ruta)).convert_alpha()
                    self._imagenes[avatar] = pygame.transform.smoothscale(
                        imagen, (tamano, tamano)
                    )
                except pygame.error:
                    pass

            imagen = self._imagenes.get(avatar)

            if imagen is not None:
                angulo = -pygame.Vector2(1, 0).angle_to(direccion)
                imagen_rotada = pygame.transform.rotate(imagen, angulo)
                rectangulo = imagen_rotada.get_rect(center=centro)
                pantalla.blit(imagen_rotada, rectangulo)
                return
            
        pygame.draw.circle(
            pantalla,
            color,
            (round(centro.x), round(centro.y)),
            tamano // 2,
        )

        if direccion.length_squared() == 0:
            direccion = pygame.Vector2(1, 0)
        else:
            direccion = direccion.normalize()

        punta = centro + direccion * (tamano * 0.4)

        pygame.draw.line(
            pantalla,
            (255, 255, 255),
            centro,
            punta,
            4,
        )

        pygame.draw.circle(
            pantalla,
            (255, 255, 255),
            (round(punta.x), round(punta.y)),
            3,
        )
