"""Pantalla de victoria de Battle Arena Challenge."""

import random
from pathlib import Path

import pygame

from avatar_renderer import RenderizadorAvatares


ANCHO = 1600
ALTO = 900

FONDO = (22, 25, 48)
BLANCO = (255, 255, 255)
DORADO = (255, 215, 80)
ROJO = (225, 75, 75)
AZUL = (70, 140, 230)

MUSICA_VICTORIA = (
    Path(__file__).resolve().parent
    / "assets"
    / "audio"
    / "victory.wav"
)


class PantallaVictoria:
    """Presenta al ganador y los resultados finales."""

    def __init__(self, estado: dict, avatares: dict[str, str]):
        self._estado = estado
        self._avatares = avatares
        self._renderizador = RenderizadorAvatares()

        partida = estado.get("match", {})
        jugadores = estado.get("players", {})

        self._ganador = partida.get("winner")
        self._puntos_rojo = jugadores.get("red", {}).get("score", 0)
        self._puntos_azul = jugadores.get("blue", {}).get("score", 0)

        self._confeti = [
            (
                random.randint(0, ANCHO),
                random.randint(0, ALTO),
                random.choice((DORADO, ROJO, AZUL, BLANCO)),
                random.randint(2, 6),
            )
            for _ in range(90)
        ]

    def ejecutar(self) -> bool:
        """Muestra la victoria hasta que se regrese al menú o se cierre."""

        pantalla = pygame.display.set_mode((ANCHO, ALTO))
        pygame.display.set_caption("Battle Arena - Victoria")

        fuente_titulo = pygame.font.SysFont(None, 90)
        fuente_texto = pygame.font.SysFont(None, 48)
        fuente_boton = pygame.font.SysFont(None, 38)

        reloj = pygame.time.Clock()

        musica_iniciada = False

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            pygame.mixer.music.load(str(MUSICA_VICTORIA))
            pygame.mixer.music.set_volume(0.35)
            pygame.mixer.music.play(-1)
            musica_iniciada = True

        except (pygame.error, OSError) as error:
            print(f"No se pudo reproducir la música de victoria: {error}")

        boton_volver = pygame.Rect(
            ANCHO // 2 - 170, ALTO - 130, 340, 65
        )

        while True:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    if musica_iniciada:
                        pygame.mixer.music.stop()
                    return False

                if evento.type == pygame.KEYDOWN:
                    if evento.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                        if musica_iniciada:
                            pygame.mixer.music.stop()
                        return True

                if evento.type == pygame.MOUSEBUTTONDOWN:
                    if evento.button == 1 and boton_volver.collidepoint(evento.pos):
                        if musica_iniciada:
                            pygame.mixer.music.stop()
                        return True

            pantalla.fill(FONDO)

            # Confeti animado.
            nuevo_confeti = []

            for x, y, color, velocidad in self._confeti:
                pygame.draw.circle(pantalla, color, (x, y), 4)

                y += velocidad

                if y > ALTO:
                    y = 0
                    x = random.randint(0, ANCHO)

                nuevo_confeti.append((x, y, color, velocidad))

            self._confeti = nuevo_confeti

            if self._ganador in ("red", "blue"):
                nombre = "ROJO" if self._ganador == "red" else "AZUL"
                mensaje = f"¡FELICIDADES, JUGADOR {nombre}!"

                titulo = fuente_titulo.render(mensaje, True, DORADO)
                pantalla.blit(
                    titulo,
                    titulo.get_rect(center=(ANCHO // 2, 130)),
                )

                avatar = self._avatares.get(
                    self._ganador,
                    "avatar_1",
                )

                self._renderizador.dibujar(
                    pantalla,
                    pygame.Vector2(ANCHO // 2, 340),
                    pygame.Vector2(1, 0),
                    avatar,
                    220,
                )
            else:
                titulo = fuente_titulo.render(
                    "¡PARTIDA FINALIZADA!",
                    True,
                    DORADO,
                )
                pantalla.blit(
                    titulo,
                    titulo.get_rect(center=(ANCHO // 2, 130)),
                )

            # Resultados finales.
            resultados = [
                (f"Jugador rojo: {self._puntos_rojo} puntos", ROJO),
                (f"Jugador azul: {self._puntos_azul} puntos", AZUL),
            ]

            for indice, (texto, color) in enumerate(resultados):
                superficie = fuente_texto.render(texto, True, color)
                pantalla.blit(
                    superficie,
                    superficie.get_rect(
                        center=(ANCHO // 2, 540 + indice * 65)
                    ),
                )

            # Botón para regresar al menú.
            pygame.draw.rect(
                pantalla,
                DORADO,
                boton_volver,
                border_radius=14,
            )

            texto_boton = fuente_boton.render(
                "VOLVER AL MENÚ",
                True,
                FONDO,
            )

            pantalla.blit(
                texto_boton,
                texto_boton.get_rect(center=boton_volver.center),
            )

            pygame.display.flip()
            reloj.tick(60)