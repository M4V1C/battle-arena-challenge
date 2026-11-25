"""Los c\u00f3digos de un solo uso solo viajan en la respuesta HTTP en modo demo."""

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.auth_store import AlmacenCuentas


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    cuentas = AlmacenCuentas(tmp_path / "usuarios.json", tmp_path / "sesiones.json")
    monkeypatch.setattr(main, "cuentas", cuentas)
    return TestClient(main.app), cuentas


def registrar(cliente):
    return cliente.post("/auth/register", json={
        "usuario": "ana", "correo": "ana@example.com", "clave": "Clave123",
    })


@pytest.mark.parametrize("valor", [None, "0", "true", "si", ""])
def test_por_defecto_no_se_devuelven_codigos(cliente, monkeypatch, valor):
    http, cuentas = cliente
    if valor is None:
        monkeypatch.delenv("EXPOSE_CODES", raising=False)
    else:
        monkeypatch.setenv("EXPOSE_CODES", valor)

    registro = registrar(http)
    reenvio = http.post("/auth/verify/resend", json={"usuario": "ana"})
    recuperacion = http.post("/auth/recovery/request", json={"correo": "ana@example.com"})

    assert registro.status_code == reenvio.status_code == recuperacion.status_code == 200
    assert registro.json() == {"ok": True, "usuario": "ana"}
    assert "codigo_verificacion" not in reenvio.json()
    assert recuperacion.json() == {"ok": True}
    # El c\u00f3digo sigue existiendo en el servidor: la verificaci\u00f3n no se rompe.
    codigo = next(u for u in cuentas._usuarios if u["usuario"] == "ana")["codigo_verificacion"]
    assert http.post("/auth/verify", json={"usuario": "ana", "codigo": codigo}).status_code == 200


def test_en_modo_demo_se_devuelven_y_funcionan(cliente, monkeypatch):
    http, _ = cliente
    monkeypatch.setenv("EXPOSE_CODES", "1")

    codigo = registrar(http).json()["codigo_verificacion"]
    assert http.post("/auth/verify", json={"usuario": "ana", "codigo": codigo}).status_code == 200

    recuperacion = http.post("/auth/recovery/request", json={"correo": "ana@example.com"}).json()
    restablecer = http.post("/auth/recovery/reset", json={
        "correo": "ana@example.com", "codigo": recuperacion["codigo_recuperacion"], "clave_nueva": "Nueva1234",
    })
    assert restablecer.status_code == 200
    assert http.post("/auth/login", json={"identificador": "ana", "clave": "Nueva1234"}).status_code == 200


def test_sin_codigo_no_se_puede_restablecer_la_clave_ajena(cliente, monkeypatch):
    http, _ = cliente
    monkeypatch.delenv("EXPOSE_CODES", raising=False)
    registrar(http)

    http.post("/auth/recovery/request", json={"correo": "ana@example.com"})
    intento = http.post("/auth/recovery/reset", json={
        "correo": "ana@example.com", "codigo": "000000", "clave_nueva": "Atacante99",
    })

    assert intento.status_code == 400
    assert http.post("/auth/login", json={"identificador": "ana", "clave": "Atacante99"}).status_code == 401
