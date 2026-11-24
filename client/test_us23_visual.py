"""Selección de escenario con un cliente autenticado por jugador."""

from unittest.mock import patch

import pygame

from screens import Aplicacion
from sesion import SESION


def test_pantalla_envia_escenario_y_token_del_jugador():
    pygame.init()
    try:
        app = Aplicacion("127.0.0.1", 9000)
        app.usuarios.jugador_rojo = "ana"
        app.usuarios.jugador_azul = "beto"
        SESION.iniciar({"usuario": "ana", "correo": "ana@example.com", "token": "token-de-ana"})
        app._selector_escenarios.seleccionado = "laberinto"
        with patch("screens.Juego") as juego:
            juego.return_value.ejecutar.return_value = True
            app._iniciar_juego()
        juego.assert_called_once_with(
            "127.0.0.1", 9000, "ana", "beto",
            token="token-de-ana", escenario="laberinto",
        )
    finally:
        SESION.cerrar()
        pygame.quit()
