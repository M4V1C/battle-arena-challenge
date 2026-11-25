"""Inicio de sesi\u00f3n con Google con el proveedor simulado: cancelaci\u00f3n, fallos, correo y token."""

import io
import json
import urllib.error
import urllib.request

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.auth_store import AlmacenCuentas, CorreoNoVerificado
from app.social_store import RETENCION_FLUJO, VIGENCIA_FLUJO, AlmacenLoginSocial
from tests.helpers import NODE, abrir_webapp

CANCELADO = "Se cancel\u00f3 el inicio de sesi\u00f3n con Google."
FALLO = "No se pudo completar el inicio de sesi\u00f3n con Google. Int\u00e9ntalo de nuevo."


class Reloj:
    def __init__(self):
        self.ahora = 1_000.0

    def __call__(self):
        return self.ahora


@pytest.fixture
def google(tmp_path, monkeypatch):
    """API con cuentas temporales, Google configurado y un proveedor simulado."""
    cuentas = AlmacenCuentas(tmp_path / "usuarios.json", tmp_path / "sesiones.json")
    reloj = Reloj()
    social = AlmacenLoginSocial(cuentas, reloj=reloj)
    monkeypatch.setattr(main, "cuentas", cuentas)
    monkeypatch.setattr(main, "social", social)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cliente-prueba")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secreto-prueba")
    perfil = {"sub": "google-1", "email": "ana@example.com", "email_verified": True, "name": "Ana"}
    llamadas = []

    def urlopen_simulado(peticion, timeout=None):
        llamadas.append(peticion.full_url)
        if isinstance(perfil.get("fallo"), Exception):
            raise perfil["fallo"]
        cuerpo = {"access_token": "acceso"} if "token" in peticion.full_url else perfil
        return io.BytesIO(json.dumps(cuerpo).encode("utf-8"))

    monkeypatch.setattr(urllib.request, "urlopen", urlopen_simulado)
    cliente = TestClient(main.app, follow_redirects=False)
    return cliente, cuentas, social, perfil, reloj, llamadas


def iniciar(cliente):
    respuesta = cliente.post("/auth/social/google/start", json={})
    assert respuesta.status_code == 200
    return respuesta.json()["state"]


def estado(cliente, state):
    return cliente.get("/auth/social/google/status", params={"state": state}).json()


def test_login_correcto_entrega_el_token_una_sola_vez(google):
    cliente, cuentas, _, _, _, _ = google
    state = iniciar(cliente)

    respuesta = cliente.get("/auth/social/google/callback", params={"state": state, "code": "codigo"})

    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == f"/webapp/?google_state={state}"
    primera = estado(cliente, state)
    assert primera["estado"] == "completado"
    assert cuentas.validar_sesion(primera["resultado"]["token"]) == primera["resultado"]["usuario"]
    assert estado(cliente, state) == {"estado": "entregado"}


@pytest.mark.parametrize("parametros", [
    {"error": "access_denied"},
    {},
])
def test_cancelar_en_google_vuelve_a_la_web_con_mensaje_y_marca_el_flujo_fallido(google, parametros):
    cliente, _, _, _, _, llamadas = google
    state = iniciar(cliente)

    respuesta = cliente.get("/auth/social/google/callback", params={"state": state, **parametros})

    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/webapp/?google_error=cancelado"
    assert estado(cliente, state) == {"estado": "fallido", "mensaje": CANCELADO}
    assert llamadas == []


def test_callback_sin_parametros_no_responde_json_ni_422(google):
    cliente = google[0]

    respuesta = cliente.get("/auth/social/google/callback")

    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/webapp/?google_error=cancelado"


@pytest.mark.parametrize("fallo", [
    urllib.error.URLError("detalle-interno-de-red"),
    urllib.error.HTTPError("https://oauth2.googleapis.com/token", 400, "detalle-interno-http", None, None),
    KeyError("detalle-interno-userinfo"),
])
def test_fallo_del_proveedor_da_un_mensaje_generico_sin_detalle(google, fallo):
    cliente, _, _, perfil, _, _ = google
    perfil["fallo"] = fallo
    state = iniciar(cliente)

    respuesta = cliente.get("/auth/social/google/callback", params={"state": state, "code": "codigo"})

    assert respuesta.status_code == 303
    assert respuesta.headers["location"] == "/webapp/?google_error=fallo"
    resultado = estado(cliente, state)
    assert resultado == {"estado": "fallido", "mensaje": FALLO}
    assert "detalle-interno" not in respuesta.text + json.dumps(resultado)


def test_userinfo_sin_sub_es_un_fallo_generico(google):
    cliente, _, _, perfil, _, _ = google
    del perfil["sub"]
    state = iniciar(cliente)

    respuesta = cliente.get("/auth/social/google/callback", params={"state": state, "code": "codigo"})

    assert respuesta.headers["location"] == "/webapp/?google_error=fallo"
    assert estado(cliente, state)["estado"] == "fallido"


def test_correo_no_verificado_no_vincula_la_cuenta_local(google):
    cliente, cuentas, _, perfil, _, _ = google
    registro = cuentas.registrar("ana", "ana@example.com", "Clave123")
    cuentas.verificar("ana", registro["codigo_verificacion"])
    perfil["email_verified"] = False
    state = iniciar(cliente)

    respuesta = cliente.get("/auth/social/google/callback", params={"state": state, "code": "codigo"})

    assert respuesta.headers["location"] == "/webapp/?google_error=correo_no_verificado"
    resultado = estado(cliente, state)
    assert resultado["estado"] == "fallido"
    assert "resultado" not in resultado
    assert "google_subject" not in cuentas._buscar_usuario("ana")


def test_correo_verificado_vincula_la_cuenta_local(google):
    cliente, cuentas, _, _, _, _ = google
    registro = cuentas.registrar("ana", "ana@example.com", "Clave123")
    cuentas.verificar("ana", registro["codigo_verificacion"])
    state = iniciar(cliente)

    cliente.get("/auth/social/google/callback", params={"state": state, "code": "codigo"})

    assert estado(cliente, state)["resultado"]["usuario"] == "ana"
    assert cuentas._buscar_usuario("ana")["google_subject"] == "google-1"


def test_sin_correo_verificado_no_se_crea_una_cuenta_nueva(tmp_path):
    cuentas = AlmacenCuentas(tmp_path / "usuarios.json", tmp_path / "sesiones.json")

    with pytest.raises(CorreoNoVerificado):
        cuentas.login_social_google("google-2", "nuevo@example.com", "Nuevo")

    assert cuentas._buscar_usuario("Nuevo") is None


def test_un_flujo_cancelado_no_se_puede_completar_despues(google):
    cliente, _, _, _, _, _ = google
    state = iniciar(cliente)
    cliente.get("/auth/social/google/callback", params={"state": state, "error": "access_denied"})

    respuesta = cliente.get("/auth/social/google/callback", params={"state": state, "code": "codigo"})

    assert respuesta.headers["location"] == "/webapp/?google_error=fallo"
    assert estado(cliente, state) == {"estado": "fallido", "mensaje": CANCELADO}


def test_flujos_vencidos_y_terminados_se_purgan(google):
    cliente, _, social, _, reloj, _ = google
    vencido = iniciar(cliente)
    reloj.ahora += VIGENCIA_FLUJO + 1
    assert estado(cliente, vencido) == {"estado": "expirado"}

    entregado = iniciar(cliente)
    cliente.get("/auth/social/google/callback", params={"state": entregado, "code": "codigo"})
    assert estado(cliente, entregado)["estado"] == "completado"

    reloj.ahora += RETENCION_FLUJO + 1
    assert estado(cliente, vencido) == {"estado": "desconocido"}
    assert estado(cliente, entregado) == {"estado": "desconocido"}
    assert social._flujos == {}


def test_un_token_no_leido_no_se_entrega_despues_de_vencer(google):
    cliente, _, _, _, reloj, _ = google
    state = iniciar(cliente)
    cliente.get("/auth/social/google/callback", params={"state": state, "code": "codigo"})

    reloj.ahora += VIGENCIA_FLUJO + 1

    assert estado(cliente, state) == {"estado": "expirado"}


necesita_node = pytest.mark.skipif(NODE is None, reason="Node.js no esta instalado")


@necesita_node
def test_web_muestra_el_mensaje_de_cancelacion():
    pagina = abrir_webapp("google_cancelado")

    assert pagina["loginMensaje"] == "Se cancelo el inicio de sesion con Google."
    assert pagina["urlLimpia"] is True
    assert pagina["consultasGoogle"] == 0


@necesita_node
def test_web_consume_solo_el_flujo_que_inicio():
    pagina = abrir_webapp("google_propio")

    assert pagina["consultasGoogle"] == 1
    assert pagina["token"] == "token-google"
    assert pagina["dashboardVisible"] is True
    assert pagina["googleStatePendiente"] is None


@necesita_node
def test_web_no_consume_el_token_de_un_flujo_del_juego():
    pagina = abrir_webapp("google_ajeno")

    assert pagina["consultasGoogle"] == 0
    assert pagina["token"] is None
    assert pagina["loginMensaje"] == "Inicio con Google completado. Vuelve al juego para continuar."


@necesita_node
def test_web_avisa_si_el_token_ya_fue_entregado():
    pagina = abrir_webapp("google_entregado")

    assert pagina["token"] is None
    assert pagina["dashboardVisible"] is False
    assert pagina["loginMensaje"] == "No se pudo completar el inicio de sesion con Google. Intentalo de nuevo."
