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


def test_login_social_google_vincula_o_crea_cuenta(tmp_path):
    from app.auth_store import AlmacenCuentas

    cuentas = AlmacenCuentas(tmp_path / "usuarios.json", tmp_path / "sesiones.json")

    login_nuevo = cuentas.login_social_google(
        google_subject="google-123",
        correo="persona@example.com",
        nombre="Persona Uno",
    )
    login_vinculado = cuentas.login_social_google(
        google_subject="google-123",
        correo="persona@example.com",
        nombre="Persona Uno",
    )

    assert login_nuevo["usuario"]
    assert login_nuevo["proveedor"] == "google"
    assert login_vinculado["token"]


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


def test_ranking_contiene_todos_los_usuarios_y_desempata(tmp_path, monkeypatch):
    import app.main as modulo

    almacen = AlmacenResultados(tmp_path / "resultados.json")
    monkeypatch.setattr(modulo, "resultados", almacen)
    almacen.guardar_resultado("m1", {
        "red": {"usuario": "ana", "score": 10},
        "blue": {"usuario": "beto", "score": 5},
    }, "red", 60)
    almacen.guardar_resultado("m2", {
        "red": {"usuario": "ana", "score": 3},
        "blue": {"usuario": "beto", "score": 8},
    }, "blue", 60)

    cliente = TestClient(modulo.app)
    ranking = cliente.get("/ranking").json()["ranking"]

    assert [fila["usuario"] for fila in ranking] == ["ana", "beto"]
    assert ranking[0]["puntaje_total"] == 13
    assert ranking[0]["victorias"] == 1


def test_historial_pertenece_al_usuario_consultado(tmp_path, monkeypatch):
    import app.main as modulo

    almacen = AlmacenResultados(tmp_path / "resultados.json")
    monkeypatch.setattr(modulo, "resultados", almacen)
    almacen.guardar_resultado("m1", {
        "red": {"usuario": "ana", "score": 10},
        "blue": {"usuario": "beto", "score": 5},
    }, "red", 60)

    cliente = TestClient(modulo.app)

    historial_ana = cliente.get("/usuarios/ana/historial").json()["historial"]
    historial_beto = cliente.get("/usuarios/beto/historial").json()["historial"]

    assert [fila["match_id"] for fila in historial_ana] == ["m1"]
    assert historial_ana[0]["resultado"] == "victoria"
    assert [fila["match_id"] for fila in historial_beto] == ["m1"]
    assert historial_beto[0]["resultado"] == "derrota"


def test_perfil_expone_resumen_de_historial(tmp_path, monkeypatch):
    import app.main as modulo

    cuentas = AlmacenCuentas(tmp_path / "usuarios.json", tmp_path / "sesiones.json")
    cuentas.registrar("ana", "ana@example.com", "Clave123")
    cuentas.verificar("ana", cuentas.listar()[0]["usuario"] if False else "000000") if False else None

    almacen = AlmacenResultados(tmp_path / "resultados.json")
    almacen.guardar_resultado("m1", {
        "red": {"usuario": "ana", "score": 10},
        "blue": {"usuario": "beto", "score": 5},
    }, "red", 60)

    monkeypatch.setattr(modulo, "cuentas", cuentas)
    monkeypatch.setattr(modulo, "resultados", almacen)
    cliente = TestClient(modulo.app)

    perfil = cliente.get("/usuarios/ana/perfil").json()

    assert perfil["usuario"] == "ana"
    assert perfil["estadisticas"]["partidas_jugadas"] == 1
    assert perfil["estadisticas"]["victorias"] == 1
    assert perfil["estadisticas"]["puntaje_total"] == 10
