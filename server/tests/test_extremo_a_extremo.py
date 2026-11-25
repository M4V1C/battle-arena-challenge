"""Escenario de extremo a extremo: cuentas por la API, partida por TCP real, guardado y consulta posterior."""

import json
import socket
import time

import pytest
from fastapi.testclient import TestClient

import app.main as main
import app.socket_server as socket_server
from app.auth_store import AlmacenCuentas
from app.game_config import AlmacenConfiguracion
from app.game_state import EstadoJuego
from app.resultados_store import AlmacenResultados


class ClienteTCP:
    def __init__(self, puerto):
        self.conn = socket.create_connection(("127.0.0.1", puerto), timeout=5)
        self.lector = self.conn.makefile("r", encoding="utf-8", newline="\n")

    def enviar(self, **mensaje):
        self.conn.sendall((json.dumps(mensaje) + "\n").encode("utf-8"))
        return json.loads(self.lector.readline())

    def cerrar(self):
        self.lector.close()
        self.conn.close()


@pytest.fixture
def servidor(tmp_path, monkeypatch):
    """La app real con su lifespan (API + TCP en el mismo proceso) sobre datos temporales."""
    monkeypatch.setenv("EXPOSE_CODES", "1")
    monkeypatch.setattr(main, "cuentas", AlmacenCuentas(tmp_path / "usuarios.json", tmp_path / "sesiones.json"))
    monkeypatch.setattr(main, "resultados", AlmacenResultados(tmp_path / "resultados.json"))
    monkeypatch.setattr(main, "partida", EstadoJuego(
        obstaculos=(), guardianes=(), trampas=(), eventos=False,
        guardar_resultado=lambda r: socket_server.guardar_resultado_final(main.resultados, r),
        calcular_records=lambda r: socket_server.records_previos(main.resultados, r),
    ))
    monkeypatch.setattr(socket_server, "AlmacenConfiguracion",
                        lambda: AlmacenConfiguracion(tmp_path / "game_config.json"))
    sockets = []
    monkeypatch.setattr(main, "crear_socket_servidor",
                        lambda host, port: sockets.append(socket_server.crear_socket_servidor("127.0.0.1", 0))
                        or sockets[-1])
    with TestClient(main.app) as api:
        yield api, sockets[0].getsockname()[1], tmp_path


def registrar(api, usuario):
    registro = api.post("/auth/register", json={"usuario": usuario, "correo": f"{usuario}@example.com",
                                                "clave": "Clave123"}).json()
    api.post("/auth/verify", json={"usuario": usuario, "codigo": registro["codigo_verificacion"]})
    return api.post("/auth/login", json={"identificador": usuario, "clave": "Clave123"}).json()["token"]


def esperar(condicion, segundos=5.0):
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if condicion():
            return True
        time.sleep(0.05)
    return False


def test_partida_completa_de_extremo_a_extremo(servidor):
    api, puerto, carpeta = servidor
    tokens = {usuario: registrar(api, usuario) for usuario in ("ana", "beto")}
    cabecera = {"Authorization": f"Bearer {tokens['ana']}"}
    ana, beto = ClienteTCP(puerto), ClienteTCP(puerto)
    try:
        assert ana.enviar(type="join", token="token-inventado")["code"] == "invalid_token"
        assert ana.enviar(type="join", token=tokens["ana"])["slot"] == "red"
        assert beto.enviar(type="join", token=tokens["beto"])["slot"] == "blue"
        assert ana.enviar(type="save_config", config={"condition": "points", "value": 2})["type"] == "config"
        assert ana.enviar(type="start")["match"]["started"] is True

        with main.partida._bloqueo:
            # Atajo de la prueba: el operador empieza junto al reactor.
            main.partida._jugadores["red"].x, main.partida._jugadores["red"].y = 740, 430
        assert ana.enviar(type="input", x=0, y=0, interact=1, shoot=0)["reactor"]["operator"] == "red"
        assert esperar(lambda: beto.enviar(type="state")["match"]["finished"])

        final = beto.enviar(type="state")["match"]
        assert (final["winner"], final["result_saved"]) == ("red", True)
        assert final["result"]["records"]["red"]["personal_best"] is True
        publico = api.get("/partida/estado").json()
        assert (publico["finalizada"], publico["ganador"]) == (True, "red")
    finally:
        ana.cerrar()
        beto.cerrar()

    assert api.get("/ranking").json()["ranking"][0]["usuario"] == "ana"
    historial = api.get("/usuarios/ana/historial", headers=cabecera).json()["historial"]
    assert (historial[0]["resultado"], historial[0]["score"]) == ("victoria", 2)
    assert historial[0]["fecha"]
    assert api.get("/usuarios/beto/historial", headers=cabecera).status_code == 403
    guardado = json.loads((carpeta / "resultados.json").read_text(encoding="utf-8"))
    assert [p["match_id"] for p in guardado["partidas"]] == [final["match_id"]]
