import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from screens import ALTO, ANCHO, Aplicacion, VOLVER
from game import Juego


class PantallasTest(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.superficie = pygame.display.set_mode((ANCHO, ALTO))
        self.app = Aplicacion("127.0.0.1", 9000)

    def tearDown(self):
        pygame.quit()

    def pulsar(self, posicion):
        self.app.procesar_evento(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=posicion
        ))

    def test_navegacion_sin_servidor(self):
        self.pulsar(self.app.botones()[0][0].center)
        self.assertEqual(self.app.pantalla_actual, "inicio")
        self.pulsar(self.app.botones()[1][0].center)
        self.assertEqual(self.app.pantalla_actual, "configuracion")
        self.app.dibujar(self.superficie, pygame.font.SysFont(None, 36))
        self.pulsar(VOLVER.center)
        self.assertEqual(self.app.pantalla_actual, "inicio")
        self.pulsar(VOLVER.center)
        self.assertEqual(self.app.pantalla_actual, "login")

    @patch("screens.Juego")
    def test_partida_vuelve_al_inicio(self, juego):
        juego.return_value.ejecutar.return_value = True
        self.app.pantalla_actual = "inicio"
        self.pulsar(self.app.botones()[0][0].center)
        self.assertEqual(self.app.pantalla_actual, "inicio")
        self.assertTrue(self.app.activa)

    @patch("screens.Juego", side_effect=ConnectionRefusedError("Sin servidor"))
    def test_error_de_conexion_permite_seguir_en_menu(self, juego):
        self.app.pantalla_actual = "inicio"
        self.pulsar(self.app.botones()[0][0].center)
        self.assertEqual(self.app.error, "Sin servidor")
        self.assertTrue(self.app.activa)

    @patch("game.ConexionServidor")
    def test_flecha_cierra_conexion_sin_cerrar_pygame(self, conexion):
        juego = Juego("127.0.0.1", 9000)
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=VOLVER.center
        ))
        self.assertTrue(juego.ejecutar())
        conexion.return_value.cerrar.assert_called_once()
        self.assertTrue(pygame.display.get_init())

    @patch("game.ConexionServidor")
    def test_cerrar_ventana_termina_aplicacion(self, conexion):
        juego = Juego("127.0.0.1", 9000)
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.assertFalse(juego.ejecutar())
        conexion.return_value.cerrar.assert_called_once()