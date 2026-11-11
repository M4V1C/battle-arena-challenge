
import pygame
from dataclasses import dataclass


@dataclass
class Notificacion:
    mensaje: str
    color: tuple[int, int, int]
    expiracion: int


class NotificacionesHUD:
    def __init__(self):
        self._notificaciones = []

    def agregar(
        self,
        mensaje: str,
        color: tuple[int, int, int] = (240, 240, 240),
        duracion: int = 3000,
    ) -> None:
        """Agrega una notificacion temporal."""
        ahora = pygame.time.get_ticks()

        self._notificaciones.append(
            Notificacion(
                mensaje=mensaje,
                color=color,
                expiracion=ahora + duracion,
            )
        )

    def actualizar(self) -> None:
        """Elimina las notificaciones expiradas."""
        ahora = pygame.time.get_ticks()

        self._notificaciones = [
            notificacion
            for notificacion in self._notificaciones
            if ahora < notificacion.expiracion
        ]

    def dibujar(
        self,
        pantalla: pygame.Surface,
        fuente: pygame.font.Font,
    ) -> None:
        """Dibuja las notificaciones en pantalla."""
        self.actualizar()

        ancho, _ = pantalla.get_size()

        for indice, notificacion in enumerate(self._notificaciones[-4:]):
            texto = fuente.render(
                notificacion.mensaje,
                True,
                notificacion.color,
            )

            rectangulo = texto.get_rect(
                center=(ancho // 2, 130 + indice * 35)
            )

            fondo = rectangulo.inflate(24, 14)

            pygame.draw.rect(
                pantalla,
                (45, 50, 65),
                fondo,
                border_radius=8,
            )

            pantalla.blit(texto, rectangulo)
