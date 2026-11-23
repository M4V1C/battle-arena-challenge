import json

from fastapi.testclient import TestClient

from app.auth_store import AlmacenCuentas
from app.game_state import EstadoJuego
from app.main import app
from app.resultados_store import AlmacenResultados


def test_registro_login_y_sesion_en_servidor(tmp_path):
    cuentas = AlmacenCuentas(tmp_path / "usuarios.json", tmp_path / "sesiones.json")

    registro = cuentas.registrar("ana", "ana@example.com", "Clave123")
    assert registro["ok"]

    antes = cuentas.login("ana", "Clave123")
    assert antes["no_verificado"] is True

    cuentas.verificar("ana", registro["codigo_verificacion"])
    login = cuentas.login("ana", "Clave123")

    assert login["usuario"] == "ana"
    assert cuentas.validar_sesion(login["token"])


def test_resultado_es_idempotente_por_match_id(tmp_path):
    almacen = AlmacenResultados(tmp_path / "resultados.json")
    jugadores = {
        "red": {"usuario": "ana", "score": 10},
        "blue": {"usuario": "beto", "score": 5},
    }

    primero = almacen.guardar_resultado("match-1", jugadores, "red", 120, 0, "points", 10)
    segundo = almacen.guardar_resultado("match-1", jugadores, "blue", 999, 2, "time", 1)

    assert primero["duplicado"] is False
    assert segundo["duplicado"] is True
    assert segundo["resultado"]["winner"] == "red"
    assert len(almacen.listar()) == 1


def test_estado_final_incluye_match_id_y_game_over():
    juego = EstadoJuego()
    juego.iniciar_partida({"condition": "points", "value": 1})
    juego._jugadores["red"].puntos = 1

    estado = juego.avanzar(0.1)

    assert estado["match"]["finished"]
    assert estado["match"]["match_id"]
    assert estado["match"]["game_over"] is not None
    assert estado["match"]["game_over"]["match_id"] == estado["match"]["match_id"]


def test_endpoints_rest_principales(tmp_path, monkeypatch):
    import app.main as modulo

    monkeypatch.setattr(modulo, "cuentas", AlmacenCuentas(tmp_path / "usuarios.json", tmp_path / "sesiones.json"))
    monkeypatch.setattr(modulo, "resultados", AlmacenResultados(tmp_path / "resultados.json"))
    cliente = TestClient(modulo.app)

    assert cliente.get("/health").json() == {"status": "ok"}

    registro = cliente.post("/auth/register", json={
        "usuario": "rest",
        "correo": "rest@example.com",
        "clave": "Clave123",
    })
    assert registro.status_code == 200

    codigo = registro.json()["codigo_verificacion"]
    assert cliente.post("/auth/verify", json={"usuario": "rest", "codigo": codigo}).status_code == 200

    login = cliente.post("/auth/login", json={"identificador": "rest", "clave": "Clave123"})
    assert login.status_code == 200

    guardado = cliente.post("/resultados", json={
        "match_id": "rest-match",
        "jugadores": {"red": {"usuario": "rest", "score": 3}},
        "winner": "red",
        "elapsed": 20,
        "overtime": 0,
    })
    assert guardado.status_code == 200
    assert cliente.get("/resultados/rest-match").status_code == 200
