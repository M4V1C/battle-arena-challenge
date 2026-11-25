"""Control de acceso de la API: perfil, historial y resultados solo para su due\u00f1o."""

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.auth_store import AlmacenCuentas
from app.resultados_store import AlmacenResultados

RUTAS_PRIVADAS = ("/usuarios/ana/perfil", "/usuarios/ana/historial")


@pytest.fixture(scope="module")
def almacenes(tmp_path_factory):
    # Se crean una vez por m\u00f3dulo: el hash PBKDF2 de cada registro es lento.
    carpeta = tmp_path_factory.mktemp("acceso")
    cuentas = AlmacenCuentas(carpeta / "usuarios.json", carpeta / "sesiones.json")
    resultados = AlmacenResultados(carpeta / "resultados.json")
    tokens = {}
    for usuario in ("ana", "beto"):
        registro = cuentas.registrar(usuario, f"{usuario}@example.com", "Clave123")
        cuentas.verificar(usuario, registro["codigo_verificacion"])
        tokens[usuario] = cuentas.login(usuario, "Clave123")["token"]
    resultados.guardar_resultado("m1", {"red": {"usuario": "ana", "score": 7},
                                        "blue": {"usuario": "beto", "score": 2}}, "red", 60)
    resultados.guardar_resultado("m2", {"red": {"usuario": "carla", "score": 1},
                                        "blue": {"usuario": "dani", "score": 0}}, "red", 30)
    return cuentas, resultados, tokens


@pytest.fixture
def api(almacenes, monkeypatch):
    cuentas, resultados, tokens = almacenes
    monkeypatch.setattr(main, "cuentas", cuentas)
    monkeypatch.setattr(main, "resultados", resultados)
    return TestClient(main.app), tokens, resultados


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("ruta", RUTAS_PRIVADAS)
def test_el_duenio_consulta_sus_datos_con_su_token(api, ruta):
    cliente, tokens, _ = api
    respuesta = cliente.get(ruta, headers=bearer(tokens["ana"]))
    assert respuesta.status_code == 200
    assert respuesta.json()["usuario"] == "ana"


@pytest.mark.parametrize("ruta", RUTAS_PRIVADAS)
@pytest.mark.parametrize("cabeceras", [
    {},
    {"Authorization": "Bearer token-inventado"},
    {"Authorization": "Bearer "},
    {"Authorization": "Basic YW5hOkNsYXZlMTIz"},
])
def test_sin_token_o_con_token_invalido_responde_401(api, ruta, cabeceras):
    cliente, _, _ = api
    respuesta = cliente.get(ruta, headers=cabeceras)
    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"
    assert "ana@example.com" not in respuesta.text


@pytest.mark.parametrize("ruta", RUTAS_PRIVADAS)
def test_token_de_otro_usuario_responde_403(api, ruta):
    cliente, tokens, _ = api
    respuesta = cliente.get(ruta, headers=bearer(tokens["beto"]))
    assert respuesta.status_code == 403
    assert "ana@example.com" not in respuesta.text


def test_resultados_solo_muestran_partidas_propias(api):
    cliente, tokens, _ = api
    propias = cliente.get("/resultados", headers=bearer(tokens["ana"])).json()["partidas"]

    assert [p["match_id"] for p in propias] == ["m1"]
    assert cliente.get("/resultados/m1", headers=bearer(tokens["beto"])).status_code == 200
    assert cliente.get("/resultados/m2", headers=bearer(tokens["ana"])).status_code == 403
    assert cliente.get("/resultados/no-existe", headers=bearer(tokens["ana"])).status_code == 404
    assert cliente.get("/resultados").status_code == 401
    assert cliente.get("/resultados/m1", headers=bearer("token-inventado")).status_code == 401


def test_post_resultados_ya_no_existe_y_no_modifica_datos(api):
    cliente, tokens, resultados = api
    falsa = {"match_id": "falsa", "jugadores": {"red": {"usuario": "ana", "score": 9999}}, "winner": "red"}

    assert cliente.post("/resultados", json=falsa).status_code == 405
    assert cliente.post("/resultados", json=falsa, headers=bearer(tokens["ana"])).status_code == 405
    assert resultados.obtener("falsa") is None
    assert cliente.get("/ranking").json()["ranking"][0]["puntaje_total"] == 7


def test_lista_publica_de_usuarios_no_expone_correos(api):
    cliente, _, _ = api
    respuesta = cliente.get("/auth/usuarios")

    assert respuesta.status_code == 200
    assert {fila["usuario"] for fila in respuesta.json()["usuarios"]} == {"ana", "beto"}
    assert all("correo" not in fila for fila in respuesta.json()["usuarios"])
    assert "@" not in respuesta.text


def test_ranking_sigue_siendo_publico_y_sin_correos(api):
    cliente, _, _ = api
    respuesta = cliente.get("/ranking")

    assert respuesta.status_code == 200
    assert "@" not in respuesta.text
