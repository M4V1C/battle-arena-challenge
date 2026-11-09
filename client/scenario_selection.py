
import pygame

from dataclasses import dataclass


@dataclass(frozen=True)
class Escenario:
    id: str
    nombre: str
    descripcion: str


ESCENARIOS = (
    Escenario(
        "arena_clasica",
        "Arena clasica",
        "Obstaculos simetricos y reactor central",
    ),
    Escenario(
        "laberinto",
        "Laberinto",
        "Pasillos estrechos y rutas alternativas",
    ),
)


class SelectorEscenarios:
    def __init__(self):
        self.seleccionado = ESCENARIOS[0].id

    def tarjetas(self, ancho: int, alto: int):
        ancho_tarjeta = 380
        separacion = 40
        inicio_x = (ancho - 2 * ancho_tarjeta - separacion) // 2

        return [
            (
                pygame.Rect(
                    inicio_x + indice * (ancho_tarjeta + separacion),
                    alto // 2 - 120,
                    ancho_tarjeta,
                    240,
                ),
                escenario,
            )
            for indice, escenario in enumerate(ESCENARIOS)
        ]

    def procesar_evento(self, evento, ancho: int, alto: int):
        if evento.type != pygame.MOUSEBUTTONDOWN or evento.button != 1:
            return False

        for rectangulo, escenario in self.tarjetas(ancho, alto):
            if rectangulo.collidepoint(evento.pos):
                self.seleccionado = escenario.id
                return True

        return False

    def dibujar(self, pantalla, fuente):
        ancho, alto = pantalla.get_size()

        for rectangulo, escenario in self.tarjetas(ancho, alto):
            activo = escenario.id == self.seleccionado

            color = (65, 105, 135) if activo else (45, 50, 65)
            borde = (120, 210, 255) if activo else (100, 110, 125)

            pygame.draw.rect(
                pantalla, color, rectangulo, border_radius=12
            )
            pygame.draw.rect(
                pantalla, borde, rectangulo, 3, border_radius=12
            )

            titulo = fuente.render(
                escenario.nombre, True, (240, 240, 240)
            )
            pantalla.blit(
                titulo,
                titulo.get_rect(
                    center=(rectangulo.centerx, rectangulo.y + 75)
                ),
            )

            descripcion = pygame.font.SysFont(None, 25).render(
                escenario.descripcion, True, (200, 205, 215)
            )
            pantalla.blit(
                descripcion,
                descripcion.get_rect(
                    center=(rectangulo.centerx, rectangulo.y + 130)
                ),
            )

            if activo:
                texto = fuente.render(
                    "Seleccionado", True, (140, 235, 170)
                )
                pantalla.blit(
                    texto,
                    texto.get_rect(
                        center=(rectangulo.centerx, rectangulo.y + 190)
                    ),
                )
