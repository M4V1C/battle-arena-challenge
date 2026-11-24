"""Pantalla de victoria de Battle Arena Challenge."""

import random
from pathlib import Path

import pygame
import math

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

FONDO_VICTORIA = (
    Path(__file__).resolve().parent
    / "assets"
    / "images"
    / "victory_background.png"
)

def dibujar_estrella(pantalla, x, y, color, radio):
    """Dibuja una estrella de cinco puntas."""

    puntos = []

    for i in range(10):
        angulo = math.pi * i / 5 - math.pi / 2

        distancia = radio if i % 2 == 0 else radio * 0.45

        punto_x = x + math.cos(angulo) * distancia
        punto_y = y + math.sin(angulo) * distancia

        puntos.append((int(punto_x), int(punto_y)))

    pygame.draw.polygon(pantalla, color, puntos)

class PantallaVictoria:
    """Presenta al ganador y los resultados finales."""

    def __init__(self, estado: dict, avatares: dict[str, str],nombres: dict[str, str],):
        self._estado = estado
        self._avatares = avatares
        self._nombres = nombres
        self._renderizador = RenderizadorAvatares()

        partida = estado.get("match", {})
        jugadores = estado.get("players", {})

        self._ganador = partida.get("winner")
        self._puntos_rojo = jugadores.get("red", {}).get("score", 0)
        self._puntos_azul = jugadores.get("blue", {}).get("score", 0)
        # Duración total de la partida, proporcionada por el servidor.
        self._duracion = max(0, int(partida.get("elapsed", 0)))
        self._minutos, self._segundos = divmod(self._duracion, 60)
        # Determinar las posiciones finales según el ganador oficial.
        if self._ganador == "red":
            self._podio = [("red", 1), ("blue", 2)]
        elif self._ganador == "blue":
            self._podio = [("blue", 1), ("red", 2)]
        else:
            # Estado de respaldo si no se recibe un ganador válido.
            self._podio = [("red", 1), ("blue", 1)]

        # Información adicional del resultado.
        self._condicion = partida.get("condition", "")
        self._objetivo = partida.get("value", 0)
        self._prorrogas = partida.get("overtime", 0)

        colores_estrellas = [
            (255, 215, 80),   # Dorado
            (255, 100, 180),  # Rosa
            (100, 220, 255),  # Celeste
            (180, 120, 255),  # Violeta
            (120, 255, 180),  # Verde
            (255, 255, 255),  # Blanco
        ]

        self._confeti = [
            (
                random.randint(0, ANCHO),
                random.randint(0, ALTO),
                random.choice(colores_estrellas),
                random.randint(2, 5),
                random.randint(5, 11),
            )
            for _ in range(90)
        ]

    def ejecutar(self) -> bool:
        """Muestra la victoria hasta que se regrese al menú o se cierre."""

        pantalla = pygame.display.set_mode((ANCHO, ALTO))
        pygame.display.set_caption("Battle Arena - Victoria")

        fondo_espacial = pygame.image.load(str(FONDO_VICTORIA)).convert()
        fondo_espacial = pygame.transform.smoothscale(
            fondo_espacial,
            (ANCHO, ALTO),
        )

        fuente_titulo = pygame.font.SysFont(None, 90)
        fuente_texto = pygame.font.SysFont(None, 48)
        fuente_boton = pygame.font.SysFont(None, 38)
        fuente_podio = pygame.font.SysFont(None, 52)
        fuente_detalle = pygame.font.SysFont(None, 34)

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
            ANCHO // 2 - 170, ALTO - 85, 340, 55
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

            pantalla.blit(fondo_espacial, (0, 0))

            # Lluvia de estrellas de colores.
            nuevo_confeti = []

            for x, y, color, velocidad, tamano in self._confeti:

                dibujar_estrella(
                    pantalla,
                    x,
                    y,
                    color,
                    tamano,
                )

                y += velocidad

                if y > ALTO + tamano:
                    y = -tamano
                    x = random.randint(0, ANCHO)

                nuevo_confeti.append(
                    (x, y, color, velocidad, tamano)
                )

            self._confeti = nuevo_confeti

            if self._ganador in ("red", "blue"):
                nombre = self._nombres.get(self._ganador, "Jugador")
                mensaje = f"¡{nombre}!"

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

            # Podio oficial de la partida.
            for indice, (puesto, posicion) in enumerate(self._podio):
                nombre = self._nombres.get(puesto, puesto.capitalize())

                puntos = (
                    self._puntos_rojo
                    if puesto == "red"
                    else self._puntos_azul
                )

                color = DORADO if posicion == 1 else BLANCO

                texto = f"{posicion}° LUGAR - {nombre}: {puntos} puntos"

                superficie = fuente_podio.render(texto, True, color)

                pantalla.blit(
                    superficie,
                    superficie.get_rect(
                        center=(ANCHO // 2, 520 + indice * 65)
                    ),
                )

            # Mostrar la duración total de la partida.
            texto_duracion = (
                f"Duración: {self._minutos:02d}:{self._segundos:02d}"
            )

            superficie_duracion = fuente_texto.render(
                texto_duracion,
                True,
                BLANCO,
            )

            pantalla.blit(
                superficie_duracion,
                superficie_duracion.get_rect(
                    center=(ANCHO // 2, 690)
                ),
            )

            # Información de la partida.
            condiciones = {
                "time": "Tiempo",
                "points": "Puntuación",
            }

            nombre_condicion = condiciones.get(
                self._condicion,
                str(self._condicion).capitalize()
            )

            if self._ganador not in ("red", "blue"):
                texto_condicion = "Resultado: empate"
            elif self._condicion == "points":
                texto_condicion = (
                    f"Victoria por puntos | Objetivo: {self._objetivo} puntos"
                )
            elif self._condicion == "time":
                texto_condicion = (
                    f"Victoria por tiempo | Límite: {self._objetivo} minutos"
                )
            else:
                texto_condicion = f"Condición: {nombre_condicion}"

            superficie_condicion = fuente_detalle.render(
                texto_condicion,
                True,
                BLANCO,
            )

            pantalla.blit(
                superficie_condicion,
                superficie_condicion.get_rect(
                    center=(ANCHO // 2, 745)
                ),
            )

            if self._prorrogas:
                texto_prorrogas = fuente_detalle.render(
                    f"Prórrogas: {self._prorrogas}",
                    True,
                    DORADO,
                )

                pantalla.blit(
                    texto_prorrogas,
                    texto_prorrogas.get_rect(
                        center=(ANCHO // 2, 790)
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