import json
import socket
import threading

from fastapi.testclient import TestClient

from app.auth_store import AlmacenCuentas
from app.main import app
from app.resultados_store import AlmacenResultados
from app.socket_server import crear_socket_servidor, guardar_resultado_final, servir


def test_aceptacion_registro_login_resultado_ranking_e_historial(tmp_path, monkeypatch):
    import app.main as modulo

    cuentas = AlmacenCuentas(tmp_path / "usuarios.json", tmp_path / "sesiones.json")
    resultados = AlmacenResultados(tmp_path / "resultados.json")
    monkeypatch.setattr(modulo, "cuentas", cuentas)
    monkeypatch.setattr(modulo, "resultados", resultados)
    cliente = TestClient(modulo.app)

    registro = cliente.post("/auth/register", json={
        "usuario": "ana",
        "correo": "ana@example.com",
        "clave": "Clave123",
    })
    assert registro.status_code == 200
    codigo = registro.json()["codigo_verificacion"]
    assert cliente.post("/auth/verify", json={"usuario": "ana", "codigo": codigo}).status_code == 200

    login = cliente.post("/auth/login", json={"identificador": "ana", "clave": "Clave123"})
    assert login.status_code == 200
    cabecera = {"Authorization": f"Bearer {login.json()['token']}"}

    # El resultado lo guarda el servidor de juego en proceso, no un cliente HTTP.
    assert guardar_resultado_final(resultados, {
        "id": "aceptacion-1", "winner": "red", "elapsed": 95, "overtime": 0,
        "condition": "points", "value": 10,
        "players": {"red": {"username": "ana", "score": 12},
                    "blue": {"username": "beto", "score": 8}},
    })
    assert cliente.post("/resultados", json={"match_id": "falsa", "jugadores": {}}).status_code == 405

    ranking = cliente.get("/ranking").json()["ranking"]
    assert ranking[0]["usuario"] == "ana"
    assert ranking[0]["puntaje_total"] == 12

    historial = cliente.get("/usuarios/ana/historial", headers=cabecera).json()["historial"]
    assert historial[0]["match_id"] == "aceptacion-1"
    assert historial[0]["resultado"] == "victoria"
    assert cliente.get("/usuarios/ana/historial").status_code == 401


def test_aceptacion_google_sin_o_con_configuracion(monkeypatch):
    import app.main as modulo

    cliente = TestClient(modulo.app)
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)

    respuesta_sin_configuracion = cliente.post("/auth/social/google/start", json={"redirect_uri": "http://127.0.0.1:8000/auth/social/google/callback"})
    assert respuesta_sin_configuracion.status_code == 503

    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cliente-prueba")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secreto-prueba")

    respuesta_con_configuracion = cliente.post("/auth/social/google/start", json={"redirect_uri": "http://127.0.0.1:8000/auth/social/google/callback"})
    assert respuesta_con_configuracion.status_code == 200
    assert "accounts.google.com" in respuesta_con_configuracion.json()["authorization_url"]


class ClienteTCP:
    def __init__(self, puerto: int):
        self.conn = socket.create_connection(("127.0.0.1", puerto), timeout=5)
        self.lector = self.conn.makefile("r", encoding="utf-8", newline="\n")

    def enviar(self, **mensaje):
        self.conn.sendall((json.dumps(mensaje) + "\n").encode("utf-8"))
        return json.loads(self.lector.readline())

    def cerrar(self):
        self.lector.close()
        self.conn.close()


def test_aceptacion_dos_clientes_join_start_e_input():
    servidor = crear_socket_servidor("127.0.0.1", 0)
    puerto = servidor.getsockname()[1]
    threading.Thread(target=servir, args=(servidor,), daemon=True).start()

    ana = ClienteTCP(puerto)
    beto = ClienteTCP(puerto)
    try:
        primero = ana.enviar(type="join", token="ana")
        segundo = beto.enviar(type="join", token="beto")

        assert primero["slot"] == "red"
        assert segundo["slot"] == "blue"
        assert beto.enviar(type="start")["match"]["started"] is False
        assert ana.enviar(type="start", scenario="arena_clasica")["match"]["started"] is True

        ana.enviar(type="input", x=1, y=0, interact=0, shoot=0)
        beto.enviar(type="input", x=-1, y=0, interact=0, shoot=0)

        estado = ana.enviar(type="state")
        assert estado["players"]["red"]["username"] == "ana"
        assert estado["players"]["blue"]["username"] == "beto"
    finally:
        ana.cerrar()
        beto.cerrar()
        servidor.close()
