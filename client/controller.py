import math
from dataclasses import dataclass

import pygame
from pygame._sdl2 import controller as sdl_controller


@dataclass(frozen=True)
class EntradaControl:
    x: float = 0.0
    y: float = 0.0
    gatillo: float = 0.0
    boton_x: bool = False
    interactuar: bool = False
    disparar: bool = False


class NormalizadorControl:
    ZONA_MUERTA = 0.15
    UMBRAL_DISPARO = 0.55
    UMBRAL_LIBERACION = 0.30

    def __init__(self):
        self._x_anterior: bool | None = None
        self._r2_activo: bool | None = None

    def actualizar(self, eje_x: int, eje_y: int, r2: int, boton_x: bool) -> EntradaControl:
        horizontal = eje_x / (32768 if eje_x < 0 else 32767)
        vertical = eje_y / (32768 if eje_y < 0 else 32767)
        magnitud = math.hypot(horizontal, vertical)
        if magnitud <= self.ZONA_MUERTA:
            horizontal = vertical = 0.0
        else:
            intensidad = (min(magnitud, 1.0) - self.ZONA_MUERTA) / (1 - self.ZONA_MUERTA)
            horizontal = horizontal / magnitud * intensidad
            vertical = vertical / magnitud * intensidad
        gatillo = max(0.0, min(1.0, r2 / 32767))
        interactuar = self._x_anterior is False and boton_x
        self._x_anterior = boton_x
        disparar = False
        if self._r2_activo is None:
            self._r2_activo = gatillo > self.UMBRAL_LIBERACION
        elif self._r2_activo:
            if gatillo <= self.UMBRAL_LIBERACION:
                self._r2_activo = False
        elif gatillo >= self.UMBRAL_DISPARO:
            self._r2_activo = True
            disparar = True
        return EntradaControl(horizontal, vertical, gatillo, boton_x, interactuar, disparar)


class ControlSDL:
    def __init__(self):
        sdl_controller.init()
        self._control = None
        self._normalizador = NormalizadorControl()
        self.nombre = "Sin control"
        self.error = ""
        self._buscar()

    @property
    def conectado(self) -> bool:
        return self._control is not None

    def _buscar(self) -> None:
        if self._control is not None:
            return
        self.error = ""
        for indice in range(sdl_controller.get_count()):
            if sdl_controller.is_controller(indice):
                self._control = sdl_controller.Controller(indice)
                self.nombre = self._control.name
                self._normalizador = NormalizadorControl()
                return
        if sdl_controller.get_count():
            self.error = "Dispositivo detectado sin mapeo SDL compatible"

    def procesar_evento(self, evento: pygame.event.Event) -> None:
        if evento.type in (pygame.CONTROLLERDEVICEADDED, pygame.JOYDEVICEADDED):
            self._buscar()

    def leer(self) -> EntradaControl:
        if self._control is None:
            return EntradaControl()
        try:
            if not self._control.attached():
                self.cerrar()
                return EntradaControl()
            return self._normalizador.actualizar(
                self._control.get_axis(pygame.CONTROLLER_AXIS_LEFTX),
                self._control.get_axis(pygame.CONTROLLER_AXIS_LEFTY),
                self._control.get_axis(pygame.CONTROLLER_AXIS_TRIGGERRIGHT),
                bool(self._control.get_button(pygame.CONTROLLER_BUTTON_A)),
            )
        except pygame.error as error:
            self.cerrar()
            self.error = str(error)
            return EntradaControl()

    def cerrar(self) -> None:
        if self._control is not None:
            self._control.quit()
            self._control = None
        self.nombre = "Sin control"
        self._normalizador = NormalizadorControl()