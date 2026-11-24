from fastapi.testclient import TestClient

from app.auth_store import AlmacenCuentas
from app.main import app
from app.resultados_store import AlmacenResultados


def test_webapp_es_servida(monkeypatch, tmp_path):
    import app.main as modulo

    monkeypatch.setattr(modulo, "cuentas", AlmacenCuentas(tmp_path / "usuarios.json", tmp_path / "sesiones.json"))
    monkeypatch.setattr(modulo, "resultados", AlmacenResultados(tmp_path / "resultados.json"))
    cliente = TestClient(modulo.app)

    respuesta = cliente.get("/webapp/")

    assert respuesta.status_code == 200
    assert "Battle Arena" in respuesta.text
    assert "app.js" in respuesta.text


def test_webapp_login_y_perfil(monkeypatch, tmp_path):
    import app.main as modulo

    cuentas = AlmacenCuentas(tmp_path / "usuarios.json", tmp_path / "sesiones.json")
    resultados = AlmacenResultados(tmp_path / "resultados.json")
    registro = cuentas.registrar("ana", "ana@example.com", "Clave123")
    cuentas.verificar("ana", registro["codigo_verificacion"])
    resultados.guardar_resultado(
        "partida-web",
        {"red": {"usuario": "ana", "score": 12}, "blue": {"usuario": "beto", "score": 8}},
        "red",
        90,
    )

    monkeypatch.setattr(modulo, "cuentas", cuentas)
    monkeypatch.setattr(modulo, "resultados", resultados)
    cliente = TestClient(modulo.app)

    login = cliente.post("/auth/login", json={"identificador": "ana", "clave": "Clave123"})
    assert login.status_code == 200
    cabecera = {"Authorization": f"Bearer {login.json()['token']}"}

    perfil = cliente.get("/usuarios/ana/perfil", headers=cabecera)
    assert perfil.status_code == 200
    assert perfil.json()["usuario"] == "ana"
    assert perfil.json()["estadisticas"]["puntaje_total"] == 12

    historial = cliente.get("/usuarios/ana/historial", headers=cabecera)
    assert historial.status_code == 200
    assert historial.json()["historial"][0]["match_id"] == "partida-web"


def test_google_sin_configuracion_retorna_error_controlado(monkeypatch):
    import app.main as modulo

    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    cliente = TestClient(modulo.app)

    respuesta = cliente.post("/auth/social/google/start", json={"redirect_uri": "http://127.0.0.1:8000/auth/social/google/callback"})

    assert respuesta.status_code == 503


def test_historial_web_muestra_la_fecha_de_cada_partida():
    import app.main as modulo

    html = (modulo.WEB_DIR / "index.html").read_text(encoding="utf-8")
    script = (modulo.WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert "<th>Fecha</th>" in html
    assert "fechaLegible(partida.fecha)" in script


def test_web_envia_token_y_no_confia_en_el_usuario_guardado():
    import app.main as modulo

    script = (modulo.WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert "cabeceras.Authorization = `Bearer ${token}`" in script
    assert "/auth/validate" in script
    assert 'localStorage.getItem("usuario")' not in script
    assert 'localStorage.setItem("usuario"' not in script
