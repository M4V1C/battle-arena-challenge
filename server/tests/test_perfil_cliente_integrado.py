"""El perfil de la API satisface el contrato de la pantalla de escritorio."""

import importlib
import re
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.auth_store import AlmacenCuentas
from app.resultados_store import AlmacenResultados

CARPETA_PERFIL = Path(__file__).resolve().parents[2] / "Epica 01-Gestion de usuarios"


def importar_perfil_datos(monkeypatch):
    monkeypatch.syspath_prepend(str(CARPETA_PERFIL))
    return importlib.import_module("perfil_datos")


def instalar_api_http(monkeypatch, main):
    """Sustituye api_servidor por llamadas HTTP reales a la app, con el mismo contrato de errores."""
    cliente = TestClient(main.app)

    def llamar(ruta, token=None):
        cabeceras = {"Authorization": f"Bearer {token}"} if token else {}
        respuesta = cliente.get(ruta, headers=cabeceras)
        if respuesta.status_code != 200:
            raise ValueError(respuesta.json()["detail"])
        return respuesta.json()

    api = types.ModuleType("api_servidor")
    api.perfil = lambda usuario, token=None: llamar(f"/usuarios/{usuario}/perfil", token)
    api.historial = lambda usuario, token=None: llamar(f"/usuarios/{usuario}/historial", token)
    api.ranking = lambda: llamar("/ranking")
    monkeypatch.setitem(sys.modules, "api_servidor", api)


def test_login_resultado_y_perfil_de_escritorio(tmp_path, monkeypatch):
    import app.main as main

    cuentas = AlmacenCuentas(tmp_path / "usuarios.json", tmp_path / "sesiones.json")
    registro = cuentas.registrar("ana", "ana@example.com", "Clave123")
    cuentas.verificar("ana", registro["codigo_verificacion"])
    token = cuentas.login("ana", "Clave123")["token"]

    resultados = AlmacenResultados(tmp_path / "resultados.json")
    resultados.guardar_resultado(
        "partida-1",
        {"red": {"usuario": "ana", "score": 10},
         "blue": {"usuario": "beto", "score": 5}},
        "red", 42,
    )
    monkeypatch.setattr(main, "cuentas", cuentas)
    monkeypatch.setattr(main, "resultados", resultados)
    instalar_api_http(monkeypatch, main)
    perfil_datos = importar_perfil_datos(monkeypatch)
    perfil = perfil_datos.obtener_perfil("ana", token)

    assert perfil["correo"] == "ana@example.com"
    assert perfil["correo_verificado"] is True
    assert perfil["estadisticas"]["partidas_jugadas"] == 1
    assert perfil["estadisticas"]["porcentaje_victorias"] == 100
    assert perfil["ranking"]["posicion"] == 1
    assert perfil["historial"][0]["puntaje"] == 10
    assert re.fullmatch(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", perfil["historial"][0]["fecha"])
    assert perfil["nivel"] >= 1
    assert perfil["logros"] and "desbloqueado" in perfil["logros"][0]
    assert perfil["logros"][0]["desbloqueado"] is True


def test_perfil_de_escritorio_sin_token_no_obtiene_datos_del_servidor(tmp_path, monkeypatch):
    import app.main as main

    cuentas = AlmacenCuentas(tmp_path / "usuarios.json", tmp_path / "sesiones.json")
    registro = cuentas.registrar("ana", "ana@example.com", "Clave123")
    cuentas.verificar("ana", registro["codigo_verificacion"])
    monkeypatch.setattr(main, "cuentas", cuentas)
    monkeypatch.setattr(main, "resultados", AlmacenResultados(tmp_path / "resultados.json"))
    instalar_api_http(monkeypatch, main)
    perfil_datos = importar_perfil_datos(monkeypatch)
    # Sin cuentas locales de respaldo, un 401 del servidor deja el perfil vacío.
    monkeypatch.setattr(perfil_datos, "cargar_usuarios", lambda: [])

    assert perfil_datos.obtener_perfil("ana") is None
    assert perfil_datos.obtener_perfil("ana", "token-inventado") is None


def test_fecha_del_historial_se_muestra_en_hora_local_o_sin_fecha(monkeypatch):
    perfil_datos = importar_perfil_datos(monkeypatch)
    esperado = datetime(2026, 11, 24, 21, 5, tzinfo=timezone.utc).astimezone().strftime("%d/%m/%Y %H:%M")

    assert perfil_datos.formatear_fecha("2026-11-24T21:05:00+00:00") == esperado
    assert perfil_datos.formatear_fecha(None) == "Sin fecha"
    assert perfil_datos.formatear_fecha("partida-1") == "Sin fecha"
