import math
import os
import unittest
from collections import defaultdict
from unittest.mock import Mock, patch

import pygame

from controller import ControlSDL, EntradaControl, NormalizadorControl
from controller_probe import DemostracionControl, ejecutar
from game import Juego


class NormalizadorTest(unittest.TestCase):
    def setUp(self):
        self.control = NormalizadorControl()
        self.control.actualizar(0, 0, 0, False)

    def test_zona_muerta_elimina_ruido(self):
        self.assertEqual(self.control.actualizar(1000, -1000, 0, False), EntradaControl())

    def test_stick_preserva_intensidad_analogica(self):
        medio = self.control.actualizar(16384, 0, 0, False)
        completo = self.control.actualizar(32767, 0, 0, False)
        self.assertGreater(medio.x, 0)
        self.assertLess(medio.x, completo.x)
        self.assertEqual(completo.x, 1)

    def test_stick_normaliza_diagonal_y_signos(self):
        entrada = self.control.actualizar(-32768, 32767, 0, False)
        self.assertAlmostEqual(math.hypot(entrada.x, entrada.y), 1)
        self.assertLess(entrada.x, 0)
        self.assertGreater(entrada.y, 0)

    def test_x_interactua_una_vez_por_pulsacion(self):
        self.assertTrue(self.control.actualizar(0, 0, 0, True).interactuar)
        self.assertFalse(self.control.actualizar(0, 0, 0, True).interactuar)
        self.control.actualizar(0, 0, 0, False)
        self.assertTrue(self.control.actualizar(0, 0, 0, True).interactuar)

    def test_r2_dispara_con_umbral_e_histeresis(self):
        self.assertFalse(self.control.actualizar(0, 0, 10000, False).disparar)
        self.assertTrue(self.control.actualizar(0, 0, 24000, False).disparar)
        for valor in (32767, 18000, 16000, 24000):
            self.assertFalse(self.control.actualizar(0, 0, valor, False).disparar)
        self.control.actualizar(0, 0, 0, False)
        self.assertTrue(self.control.actualizar(0, 0, 32767, False).disparar)

    def test_conectar_con_botones_pulsados_no_genera_acciones(self):
        control = NormalizadorControl()
        entrada = control.actualizar(0, 0, 32767, True)
        self.assertFalse(entrada.interactuar)
        self.assertFalse(entrada.disparar)


class DispositivoTest(unittest.TestCase):
    @patch("controller.sdl_controller")
    def test_sin_dispositivo_no_hay_entrada(self, sdl):
        sdl.get_count.return_value = 0
        control = ControlSDL()
        self.assertFalse(control.conectado)
        self.assertEqual(control.leer(), EntradaControl())

    @patch("controller.sdl_controller")
    def test_mapeo_estandar_lee_x_y_r2_sin_indices_usb(self, sdl):
        sdl.get_count.return_value = 1
        sdl.is_controller.return_value = True
        dispositivo = sdl.Controller.return_value
        dispositivo.name = "DualSense"
        dispositivo.attached.return_value = True
        dispositivo.get_axis.return_value = 0
        dispositivo.get_button.return_value = False
        control = ControlSDL()
        control.leer()
        dispositivo.get_button.return_value = True
        dispositivo.get_axis.side_effect = lambda eje: {
            pygame.CONTROLLER_AXIS_LEFTX: 32767,
            pygame.CONTROLLER_AXIS_LEFTY: 0,
            pygame.CONTROLLER_AXIS_TRIGGERRIGHT: 32767,
        }[eje]
        entrada = control.leer()
        self.assertEqual(entrada.x, 1)
        self.assertTrue(entrada.interactuar)
        self.assertTrue(entrada.disparar)
        dispositivo.get_button.assert_called_with(pygame.CONTROLLER_BUTTON_A)

    @patch("controller.sdl_controller")
    def test_desconexion_detiene_entrada_y_permite_reconectar(self, sdl):
        sdl.get_count.return_value = 1
        sdl.is_controller.return_value = True
        dispositivo = sdl.Controller.return_value
        dispositivo.name = "DualSense"
        dispositivo.attached.return_value = False
        control = ControlSDL()
        self.assertEqual(control.leer(), EntradaControl())
        self.assertFalse(control.conectado)
        dispositivo.quit.assert_called_once()
        control.procesar_evento(Mock(type=pygame.CONTROLLERDEVICEADDED))
        self.assertTrue(control.conectado)


class DemostracionTest(unittest.TestCase):
    @patch.dict(os.environ, {"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"})
    @patch("controller_probe.dibujar")
    @patch("controller_probe.ControlSDL")
    @patch("controller_probe.DemostracionControl")
    def test_verificacion_completa_espera_cierre_de_ventana(self, demostracion, control, dibujar):
        demo = demostracion.return_value
        demo.verificada = True
        demo.direcciones = set()
        demo.verificaciones = {"Stick izquierdo": True, "X": True, "R2": True}
        with patch("controller_probe.pygame.event.get", side_effect=[
            [], [pygame.event.Event(pygame.QUIT)]
        ]) as eventos:
            self.assertEqual(ejecutar(verificar=True), 0)
        self.assertEqual(eventos.call_count, 2)
        control.return_value.cerrar.assert_called_once()

    def test_entradas_del_control_ejecutan_acciones_visibles(self):
        demo = DemostracionControl()
        inicial = demo.posicion.copy()
        demo.actualizar(EntradaControl(x=0.5), 0.1)
        self.assertAlmostEqual(demo.posicion.x - inicial.x, 12)
        demo.actualizar(EntradaControl(interactuar=True, disparar=True), 0)
        self.assertEqual(demo.interacciones, 1)
        self.assertEqual(demo.disparos, 1)
        self.assertGreater(demo.anillo, 0)
        self.assertEqual(len(demo.proyectiles), 1)

    def test_verificacion_exige_cuatro_direcciones_reposo_y_acciones(self):
        demo = DemostracionControl()
        for horizontal, vertical in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            demo.actualizar(EntradaControl(x=horizontal, y=vertical), 0)
        self.assertFalse(demo.verificada)
        demo.actualizar(EntradaControl(interactuar=True, disparar=True), 0)
        self.assertTrue(demo.verificada)

    def test_sin_hardware_no_se_completa_la_verificacion(self):
        demo = DemostracionControl()
        for _ in range(60):
            demo.actualizar(EntradaControl(), 1 / 60)
        self.assertFalse(demo.verificada)
        self.assertEqual(demo.disparos, 0)
        self.assertEqual(demo.interacciones, 0)


class IntegracionJuegoTest(unittest.TestCase):
    def crear_juego(self):
        juego = Juego.__new__(Juego)
        juego._teclas = {
            "red": {"left": pygame.K_a, "right": pygame.K_d, "up": pygame.K_w, "down": pygame.K_s},
            "blue": {
                "left": pygame.K_LEFT, "right": pygame.K_RIGHT,
                "up": pygame.K_UP, "down": pygame.K_DOWN,
            },
        }
        juego._contadores = {
            "red": {"shoot": 0, "interact": 0},
            "blue": {"shoot": 0, "interact": 0},
        }
        return juego

    @patch("game.pygame.key.get_pressed")
    def test_dualsense_mapea_stick_x_y_r2_al_jugador_rojo(self, get_pressed):
        get_pressed.return_value = defaultdict(int, {pygame.K_d: 1, pygame.K_UP: 1})
        juego = self.crear_juego()
        juego._control = Mock()
        juego._control.leer.return_value = EntradaControl(
            x=0.35, y=-0.6, interactuar=True, disparar=True
        )

        entradas = juego._leer_controles()

        self.assertEqual(entradas["red"], {"x": 0.35, "y": -0.6, "shoot": 1, "interact": 1})
        self.assertEqual(entradas["blue"], {"x": 0, "y": -1, "shoot": 0, "interact": 0})
        juego._control.leer.assert_called_once()

    @patch("game.pygame.key.get_pressed")
    def test_teclado_rojo_sigue_funcionando_con_stick_centrado(self, get_pressed):
        get_pressed.return_value = defaultdict(int, {pygame.K_a: 1, pygame.K_s: 1})
        juego = self.crear_juego()
        juego._control = Mock()
        juego._control.leer.return_value = EntradaControl()

        entradas = juego._leer_controles()

        self.assertEqual(entradas["red"]["x"], -1)
        self.assertEqual(entradas["red"]["y"], 1)

    @patch("game.pygame.key.get_pressed")
    def test_contadores_de_control_solo_suben_al_pulsar(self, get_pressed):
        get_pressed.return_value = defaultdict(int)
        juego = self.crear_juego()
        juego._control = Mock()
        juego._control.leer.side_effect = [
            EntradaControl(interactuar=True, disparar=True),
            EntradaControl(),
            EntradaControl(interactuar=True),
        ]

        entradas = [juego._leer_controles() for _ in range(3)]

        self.assertEqual(entradas[0]["red"]["interact"], 1)
        self.assertEqual(entradas[0]["red"]["shoot"], 1)
        self.assertEqual(entradas[1]["red"]["interact"], 1)
        self.assertEqual(entradas[1]["red"]["shoot"], 1)
        self.assertEqual(entradas[2]["red"]["interact"], 2)
        self.assertEqual(entradas[2]["red"]["shoot"], 1)