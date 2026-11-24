"""El perfil de la API satisface el contrato de la pantalla de escritorio."""

import importlib
import sys
import types
from pathlib import Path

from app.auth_store import AlmacenCuentas
from app.resultados_store import AlmacenResultados


def test_login_resultado_y_perfil_de_escritorio(tmp_path, monkeypatch):
    import app.main as main

    cuentas = AlmacenCuentas(tmp_path / "usuarios.json", tmp_path / "sesiones.json")
    registro = cuentas.registrar("ana", "ana@example.com", "Clave123")
    cuentas.verificar("ana", registro["codigo_verificacion"])
    assert cuentas.login("ana", "Clave123")["token"]

    resultados = AlmacenResultados(tmp_path / "resultados.json")
    resultados.guardar_resultado(
        "partida-1",
        {"red": {"usuario": "ana", "score": 10},
         "blue": {"usuario": "beto", "score": 5}},
        "red", 42,
    )
    monkeypatch.setattr(main, "cuentas", cuentas)
    monkeypatch.setattr(main, "resultados", resultados)

    api = types.ModuleType("api_servidor")
    api.perfil = main.perfil_usuario
    api.ranking = main.ranking
    api.historial = main.historial_usuario
    monkeypatch.setitem(sys.modules, "api_servidor", api)
    carpeta_perfil = Path(__file__).resolve().parents[2] / "Epica 01-Gestion de usuarios"
    monkeypatch.syspath_prepend(str(carpeta_perfil))
    perfil_datos = importlib.import_module("perfil_datos")
    perfil = perfil_datos.obtener_perfil("ana")

    assert perfil["correo"] == "ana@example.com"
    assert perfil["correo_verificado"] is True
    assert perfil["estadisticas"]["partidas_jugadas"] == 1
    assert perfil["estadisticas"]["porcentaje_victorias"] == 100
    assert perfil["ranking"]["posicion"] == 1
    assert perfil["historial"][0]["puntaje"] == 10
    assert perfil["nivel"] >= 1
    assert perfil["logros"] and "desbloqueado" in perfil["logros"][0]
    assert perfil["logros"][0]["desbloqueado"] is True
