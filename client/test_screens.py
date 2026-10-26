import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from screens import ALTO, ANCHO, Aplicacion, VOLVER, MODO_TIEMPO, CAMPO_VALOR, GUARDAR
from game import Juego


class PantallasTest(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.superficie = pygame.display.set_mode((ANCHO, ALTO))
        self.app = Aplicacion("127.0.0.1", 9000)
        self.parche_red = patch("screens.ConexionServidor")
        self.red = self.parche_red.start().return_value
        self.red.obtener_estado.return_value = None

    def tearDown(self):
        self.app._cerrar_configuracion()
        self.parche_red.stop()
        pygame.quit()

    def pulsar(self, posicion):
        self.app.procesar_evento(pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=posicion
        ))

    def test_navegacion_sin_servidor(self):
        self.pulsar(self.app.botones()[0][0].center)
        self.assertEqual(self.app.pantalla_actual, "inicio")
        boton_configuracion = next(
            rectangulo
            for rectangulo, _, destino in self.app.botones()
            if destino == "configuracion"
        )
        self.pulsar(boton_configuracion.center)
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

    def test_cargar_editar_y_guardar_configuracion(self):
        self.app._abrir_configuracion()
        self.red.obtener_estado.return_value = {
            "type": "config", "config": {"condition": "points", "value": 25, "sensitivity": 1.5}
        }
        self.app.actualizar_configuracion()
        self.assertEqual(self.app._valor, "25")
        self.pulsar(MODO_TIEMPO.center)
        self.pulsar(CAMPO_VALOR.center)
        self.app.procesar_evento(pygame.event.Event(pygame.TEXTINPUT, text="2"))
        self.pulsar(GUARDAR.center)
        self.red.guardar_configuracion.assert_called_once_with(
            {"condition": "time", "value": 2, "sensitivity": 1.5}
        )
        self.assertTrue(self.app._pendiente)
        self.red.obtener_estado.return_value = {
            "type": "config", "config": {"condition": "time", "value": 2, "sensitivity": 1.5}
        }
        self.app.actualizar_configuracion()
        self.assertEqual(self.app._confirmacion, "Configuracion guardada")
        self.app.dibujar(self.superficie, pygame.font.SysFont(None, 36))

    def test_valores_invalidos_no_se_envian(self):
        self.app._abrir_configuracion()
        self.app._configuracion_cargada = True
        self.app._pendiente = False
        for valor in ("0", "-1", "", "1.5"):
            self.app._valor = valor
            self.app._guardar_configuracion()
            self.assertTrue(self.app.error)
        self.red.guardar_configuracion.assert_not_called()

    @patch("game.PantallaVictoria")
    @patch("game.ConexionServidor")
    def test_finalizar_partida_vuelve_al_inicio_y_cierra_conexion(
        self, conexion, pantalla_victoria
    ):
        conexion.return_value.obtener_estado.return_value = {
            "type": "state",
            "match": {"finished": True, "winner": "red"},
            "players": {
                "red": {"score": 100},
                "blue": {"score": 75},
            },
        }

        pantalla_victoria.return_value.ejecutar.return_value = True

        juego = Juego("127.0.0.1", 9000)
        pygame.event.clear()

        self.assertTrue(juego.ejecutar())

        pantalla_victoria.assert_called_once_with(
            estado=juego._estado,
            avatares=juego._avatares,
        )
        pantalla_victoria.return_value.ejecutar.assert_called_once()
        conexion.return_value.cerrar.assert_called_once()

    @patch("game.ConexionServidor")
    def test_dibujo_separa_orientacion_y_direccion_deseada(self, conexion):
        juego = Juego("127.0.0.1", 9000)

        juego._estado = {
            "players": {
                "red": {
                    "x": 100,
                    "y": 100,
                    "dir_x": 1,
                    "dir_y": 0,
                    "move_x": 0,
                    "move_y": 1,
                }
            }
        }

        with patch.object(juego._renderizador_avatares, "dibujar") as dibujar_avatar:
            juego._dibujar(
                self.superficie,
                pygame.font.SysFont(None, 28),
            )

        # Verificar que el avatar conserva la orientación hacia la derecha.
        dibujar_avatar.assert_called_once()

        argumentos = dibujar_avatar.call_args.kwargs

        self.assertEqual(argumentos["centro"], pygame.Vector2(120, 120))
        self.assertEqual(argumentos["direccion"], pygame.Vector2(1, 0))
        self.assertEqual(argumentos["avatar"], juego._avatares["red"])

        # Verificar que la dirección deseada se dibuja hacia abajo.
        self.assertEqual(
            self.superficie.get_at((120, 150))[:3],
            (185, 195, 205),
        )