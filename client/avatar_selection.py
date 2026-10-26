
"""Pantalla de selección de avatares para dos jugadores."""

import pygame

from avatar_repository import (AVATARES_PREDETERMINADOS, RepositorioAvatares,)
from tkinter import Tk, filedialog
from avatar_images import importar_avatar

COLORES_AVATAR = (
    (225, 75, 75),
    (70, 140, 230),
    (75, 195, 120),
    (220, 170, 65),
    (170, 105, 220),
)


class PantallaAvatares:
    
    """Gestiona la presentación y selección de avatares."""

    def __init__(self,repositorio: RepositorioAvatares,nombres: dict[str, str],):
        self._repositorio = repositorio
        self._nombres = nombres
        self._selecciones = repositorio.obtener()
        self._jugador_actual = "red"
        self._opciones: list[tuple[pygame.Rect, str]] = []
        self._boton_importar = pygame.Rect(650, 600, 300, 55)
        self._mensaje = ""

    def actualizar_nombres(self, nombres: dict[str, str]) -> None:
        self._nombres = nombres

    def procesar_evento(self, evento: pygame.event.Event) -> None:
        """Procesa la selección de jugador y avatar."""
        if evento.type != pygame.MOUSEBUTTONDOWN or evento.button != 1:
            return

        x, y = evento.pos

        if self._boton_importar.collidepoint(x, y):
            ventana = Tk()
            ventana.withdraw()
            try:
                ruta = filedialog.askopenfilename(
                    parent=ventana,
                    title="Seleccionar imagen de avatar",
                    filetypes=[
                        ("Imágenes", "*.png *.jpg *.jpeg"),
                    ],
                )
            finally:
                ventana.destroy()

            if ruta:
                try:
                    identificador = importar_avatar(ruta)
                    self._repositorio.guardar(self._jugador_actual, identificador)
                    self._selecciones[self._jugador_actual] = identificador
                    self._mensaje = "Imagen cargada correctamente."
                except (OSError, ValueError) as error:
                    self._mensaje = str(error)
            return

        if pygame.Rect(460, 240, 300, 55).collidepoint(x, y):
            self._jugador_actual = "red"
            return

        if pygame.Rect(800, 240, 300, 55).collidepoint(x, y):
            self._jugador_actual = "blue"
            return

        for rectangulo, avatar in self._opciones:
            if rectangulo.collidepoint(x, y):
                self._repositorio.guardar(self._jugador_actual, avatar)
                self._selecciones[self._jugador_actual] = avatar
                return

    def dibujar(self, pantalla: pygame.Surface, fuente: pygame.font.Font) -> None:
        """Dibuja las opciones disponibles y la selección actual."""
      
        for jugador, x in (
            ("red", 460),
            ("blue", 800),
        ):
            texto = self._nombres.get(jugador) or (
                "Jugador 1" if jugador == "red" else "Jugador 2"
            )
            rectangulo = pygame.Rect(x, 240, 300, 55)
            activo = jugador == self._jugador_actual
            color = (90, 110, 135) if activo else (45, 50, 65)
            pygame.draw.rect(pantalla, color, rectangulo, border_radius=8)
            etiqueta = fuente.render(texto, True, (240, 240, 240))
            pantalla.blit(etiqueta, etiqueta.get_rect(center=rectangulo.center))

        self._opciones.clear()

        for indice, avatar in enumerate(AVATARES_PREDETERMINADOS):
            x = 300 + indice * 210
            rectangulo = pygame.Rect(x, 370, 160, 160)
            self._opciones.append((rectangulo, avatar))

            seleccionado = self._selecciones[self._jugador_actual] == avatar
            pygame.draw.rect(
                pantalla,
                (245, 245, 245) if seleccionado else (80, 85, 100),
                rectangulo,
                border_radius=12,
                width=4 if seleccionado else 2,
            )

            pygame.draw.circle(
                pantalla,
                COLORES_AVATAR[indice],
                rectangulo.center,
                48,
            )

            etiqueta = fuente.render(f"Avatar {indice + 1}", True, (240, 240, 240))
            pantalla.blit(
                etiqueta,
                etiqueta.get_rect(center=(rectangulo.centerx, 560)),
            )

        for indice, jugador in enumerate(("red", "blue")):
            nombre = self._nombres.get(jugador) or (
                "Jugador 1" if jugador == "red" else "Jugador 2"
            )
            texto = f"{nombre}: {self._selecciones[jugador]}"
            etiqueta = fuente.render(texto, True, (240, 240, 240))
            pantalla.blit(etiqueta, (490, 690 + indice * 40))

        pygame.draw.rect(
            pantalla,
            (65, 105, 115),
            self._boton_importar,
            border_radius=8,
        )

        texto = fuente.render("Cargar imagen", True, (240, 240, 240))
        pantalla.blit(
            texto,
            texto.get_rect(center=self._boton_importar.center),
        )

        if self._mensaje:
            mensaje = fuente.render(self._mensaje, True, (240, 240, 240))
            pantalla.blit(
                mensaje,
                mensaje.get_rect(center=(800, 770)),
            )
