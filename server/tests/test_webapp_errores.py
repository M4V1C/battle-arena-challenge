"""Comportamiento de la webapp ante errores de red y de respuesta (se ejecuta app.js con Node)."""

import pytest

from tests.helpers import NODE, abrir_webapp

SIN_CONEXION = "No se pudo conectar con el servidor. Revisa la conexion e intenta de nuevo."
DATOS_INVALIDOS = "El servidor respondio con datos no validos. Intenta de nuevo mas tarde."
SESION_EXPIRADA = "Tu sesion expiro. Inicia sesion de nuevo."

pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js no esta instalado")


def test_con_respuestas_correctas_muestra_los_datos_sin_error():
    pagina = abrir_webapp("correcto")

    assert pagina["dashboardVisible"] is True
    assert pagina["datosMensajeVisible"] is False
    assert pagina["partidas"] == "3"
    assert pagina["historial"][0][1:] == ["abcdef12", "victoria", "20", "1:00"]


def test_sin_red_muestra_un_mensaje_claro_y_conserva_la_sesion():
    pagina = abrir_webapp("sin_red")

    assert pagina["dashboardVisible"] is True
    assert (pagina["datosMensaje"], pagina["datosMensajeVisible"]) == (SIN_CONEXION, True)
    assert pagina["token"] == "token-valido"


def test_token_vencido_vuelve_al_login_con_aviso():
    pagina = abrir_webapp("token_vencido")

    assert pagina["dashboardVisible"] is False
    assert pagina["loginMensaje"] == SESION_EXPIRADA
    assert pagina["token"] is None


def test_error_del_servidor_muestra_su_detalle():
    pagina = abrir_webapp("error_servidor")

    assert (pagina["datosMensaje"], pagina["datosMensajeVisible"]) == ("Error interno del servidor.", True)


@pytest.mark.parametrize("escenario", ["respuesta_no_json", "respuesta_incompleta"])
def test_respuesta_no_valida_muestra_un_mensaje_claro(escenario):
    pagina = abrir_webapp(escenario)

    assert (pagina["datosMensaje"], pagina["datosMensajeVisible"]) == (DATOS_INVALIDOS, True)
    assert pagina["dashboardVisible"] is True


def test_restaurar_sesion_sin_red_no_borra_el_token():
    pagina = abrir_webapp("validar_sin_red")

    assert pagina["dashboardVisible"] is False
    assert pagina["loginMensaje"] == SIN_CONEXION
    assert pagina["token"] == "token-valido"


def test_restaurar_sesion_con_token_invalido_lo_borra():
    pagina = abrir_webapp("validar_401")

    assert pagina["loginMensaje"] == SESION_EXPIRADA
    assert pagina["token"] is None
