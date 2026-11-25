"""El registro de escritorio no falla cuando el servidor no devuelve el c\u00f3digo."""

import sys
from pathlib import Path

CARPETA_USUARIOS = Path(__file__).resolve().parent.parent / "Epica 01-Gestion de usuarios"
if str(CARPETA_USUARIOS) not in sys.path:
    sys.path.insert(0, str(CARPETA_USUARIOS))

import cuentas  # noqa: E402


class Campo:
    def __init__(self, texto):
        self.texto = texto
        self.error = ""


def registrar_con(monkeypatch, respuesta):
    monkeypatch.setattr(cuentas, "registrar", lambda usuario, correo, clave: respuesta)
    return cuentas.procesar_registro(
        Campo("ana"), Campo("ana@example.com"), Campo("Clave123"), Campo("Clave123")
    )


def test_registro_sin_codigo_en_la_respuesta(monkeypatch):
    usuario, mensaje = registrar_con(monkeypatch, {"ok": True, "usuario": "ana"})

    assert usuario == "ana"
    assert "correo" in mensaje


def test_registro_en_modo_demo_muestra_el_codigo(monkeypatch):
    usuario, mensaje = registrar_con(
        monkeypatch, {"ok": True, "usuario": "ana", "codigo_verificacion": "123456"}
    )

    assert usuario == "ana"
    assert "123456" in mensaje
