"""Pantalla de login de escritorio: los elementos no se tapan y caben en el panel (recuperada del stash 7094bf2)."""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
CARPETA_USUARIOS = Path(__file__).resolve().parent.parent / "Epica 01-Gestion de usuarios"
if str(CARPETA_USUARIOS) not in sys.path:
    sys.path.insert(0, str(CARPETA_USUARIOS))

import pantalla_login  # noqa: E402


@pytest.fixture
def elementos():
    return [
        pantalla_login.campo_ident.rect,
        pantalla_login.campo_clave.rect,
        pantalla_login.enlace_olvido.rect,
        pantalla_login.boton_login.rect,
        pantalla_login.boton_google.rect,
        pantalla_login.boton_ir_registro.rect,
    ]


def test_elementos_principales_no_se_sobrelapan(elementos):
    for indice, elemento in enumerate(elementos):
        for otro in elementos[indice + 1:]:
            assert not elemento.colliderect(otro), f"Solapamiento entre {elemento} y {otro}"


def test_elementos_caben_dentro_del_panel(elementos):
    for elemento in elementos:
        assert pantalla_login.PANEL.contains(elemento), f"Elemento fuera del panel: {elemento}"
