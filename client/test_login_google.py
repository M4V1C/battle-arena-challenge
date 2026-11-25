"""El login de escritorio deja de esperar a Google cuando el flujo falla, vence o ya se us\u00f3."""

import os
import sys
from pathlib import Path

import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
CARPETA_USUARIOS = Path(__file__).resolve().parent.parent / "Epica 01-Gestion de usuarios"
if str(CARPETA_USUARIOS) not in sys.path:
    sys.path.insert(0, str(CARPETA_USUARIOS))

import pantalla_login  # noqa: E402
from estado import Estado  # noqa: E402
from sesion import SESION  # noqa: E402


def revisar_google(monkeypatch, respuesta):
    monkeypatch.setattr(pantalla_login, "estado_google", lambda state: respuesta)
    estado = Estado()
    estado.google_state = "S1"
    pantalla_login.eventos_login(pygame.event.Event(pygame.USEREVENT), estado)
    return estado


@pytest.mark.parametrize("respuesta, mensaje", [
    ({"estado": "fallido", "mensaje": "Se cancel\u00f3 el inicio de sesi\u00f3n con Google."},
     "Se cancel\u00f3 el inicio de sesi\u00f3n con Google."),
    ({"estado": "fallido"}, pantalla_login.MENSAJES_GOOGLE["fallido"]),
    ({"estado": "entregado"}, pantalla_login.MENSAJES_GOOGLE["entregado"]),
    ({"estado": "expirado"}, pantalla_login.MENSAJES_GOOGLE["expirado"]),
    ({"estado": "desconocido"}, pantalla_login.MENSAJES_GOOGLE["desconocido"]),
])
def test_un_flujo_terminado_sin_sesion_deja_de_consultarse(monkeypatch, respuesta, mensaje):
    estado = revisar_google(monkeypatch, respuesta)

    assert estado.google_state is None
    assert estado.mensaje == mensaje
    assert not SESION.activa


def test_un_flujo_pendiente_se_sigue_consultando(monkeypatch):
    estado = revisar_google(monkeypatch, {"estado": "pendiente"})

    assert estado.google_state == "S1"
    assert estado.mensaje == ""
