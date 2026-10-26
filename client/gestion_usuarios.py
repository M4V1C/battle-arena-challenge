"""Adaptador de las pantallas de gestión de usuarios al cliente del juego."""

import sys
import pygame
from pathlib import Path

RUTA_USUARIOS = (
    Path(__file__).resolve().parent.parent
    / "Epica 01-Gestion de usuarios"
)

if str(RUTA_USUARIOS) not in sys.path:
    sys.path.insert(0, str(RUTA_USUARIOS))

from sesion import SESION
from estado import Estado, PANTALLAS, ir_a, dibujar_pantalla

# Importar las pantallas permite registrarlas en PANTALLAS.
import pantalla_registro
import pantalla_verificacion
import pantalla_login
import pantalla_recuperacion
import pantalla_perfil
import pantalla_juego


class GestionUsuarios:
    """Gestiona las pantallas de autenticación y perfil."""
    def __init__(self):
        self.estado = Estado()

        # Identidades de los dos participantes de la partida.
        self.jugador_rojo: str | None = None
        self.jugador_azul: str | None = None

        ir_a(self.estado, "login")
    @property
    def autenticado(self) -> bool:
        return SESION.activa

    @property
    def usuario(self) -> str | None:
        return SESION.usuario

    def procesar_evento(self, evento):
        PANTALLAS[self.estado.pantalla]["eventos"](evento, self.estado)

    def dibujar(self):
        dibujar_pantalla(self.estado)

    def ir_a(self, pantalla: str):
        ir_a(self.estado, pantalla)

    def cerrar_sesion(self):
        SESION.cerrar()
        self.jugador_rojo = None
        self.jugador_azul = None
        self._sesion_principal = None
        ir_a(self.estado, "login")

        # Reactivar la entrada de texto de Pygame.
        pygame.key.start_text_input()

        campos = PANTALLAS["login"]["campos"]
        if campos:
            campos[0].activo = True

    def abrir_perfil(self):
        if not SESION.activa:
            return

        ir_a(self.estado, "perfil")

    def preparar_segundo_jugador(self):
        """Conserva la primera sesión y abre el login del segundo jugador."""
        if not SESION.activa:
            return False

        self.jugador_rojo = SESION.usuario
        self._sesion_principal = {
            "usuario": SESION.usuario,
            "correo": SESION.correo,
            "avatar": SESION.avatar,
        }
        self.jugador_azul = None

        SESION.cerrar()
        ir_a(self.estado, "login")
        pygame.key.start_text_input()
        return True

    def completar_segundo_jugador(self):
        """Valida la segunda identidad y restaura la sesión principal."""
        if not SESION.activa:
            return False

        segundo = SESION.usuario

        if segundo == self.jugador_rojo:
            SESION.iniciar(self._sesion_principal)
            ir_a(self.estado, "login")
            self.estado.poner_mensaje(
                "El segundo jugador debe utilizar una cuenta diferente."
            )
            SESION.cerrar()
            return False

        self.jugador_azul = segundo
        SESION.iniciar(self._sesion_principal)
        return True

    def cancelar_segundo_jugador(self):
        """Restaura la sesión principal si se cancela el segundo login."""
        if hasattr(self, "_sesion_principal"):
            SESION.iniciar(self._sesion_principal)
        self.jugador_azul = None