"""GET /partida/estado: resumen p\u00fablico de la partida que comparte la API con el servidor TCP."""

import threading

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.game_state import EstadoJuego
from app.resultados_store import AlmacenResultados

CLAVES = {"match_id", "iniciada", "finalizada", "en_curso", "escenario", "condicion", "objetivo",
          "tiempo", "ganador", "reactor", "jugadores", "eventos_activos"}
CLAVES_JUGADOR = {"usuario", "puntaje", "conectado", "estado"}


@pytest.fixture
def consultar(monkeypatch):
    def consultar_partida(juego):
        monkeypatch.setattr(main, "partida", juego)
        respuesta = TestClient(main.app).get("/partida/estado")
        assert respuesta.status_code == 200
        return respuesta.json()
    return consultar_partida


def partida_en_curso(**kwargs) -> EstadoJuego:
    juego = EstadoJuego(**kwargs)
    juego.unir_jugador("ana")
    juego.unir_jugador("beto")
    return juego


def test_sin_partida_responde_un_estado_vacio_valido(consultar):
    estado = consultar(EstadoJuego())

    assert set(estado) == CLAVES
    assert estado["match_id"] is None
    assert (estado["iniciada"], estado["finalizada"], estado["en_curso"]) == (False, False, False)
    assert estado["ganador"] is None
    assert estado["eventos_activos"] == []
    assert estado["jugadores"] == {
        puesto: {"usuario": None, "puntaje": 0, "conectado": False, "estado": "normal"}
        for puesto in ("red", "blue")
    }


def test_con_partida_activa_muestra_jugadores_puntaje_y_tiempo(consultar):
    juego = partida_en_curso(guardianes=(), eventos=False)
    juego.iniciar_por("red", {"condition": "time", "value": 2})
    juego._jugadores["red"].puntos = 7
    juego.avanzar(0.5)

    estado = consultar(juego)

    assert estado["en_curso"] is True
    assert estado["match_id"]
    assert estado["condicion"] == "time"
    assert estado["tiempo"]["limite"] == 120
    assert estado["tiempo"]["restante"] == pytest.approx(119.5)
    assert estado["jugadores"]["red"] == {"usuario": "ana", "puntaje": 7, "conectado": True, "estado": "normal"}
    assert estado["jugadores"]["blue"]["usuario"] == "beto"
    assert estado["reactor"] == {"estado": "available", "operador": None}


def test_partida_terminada_informa_al_ganador(consultar):
    juego = partida_en_curso(guardianes=(), eventos=False)
    juego.iniciar_por("red", {"condition": "points", "value": 20})
    juego._jugadores["red"].puntos = 20
    juego.avanzar(0.1)

    estado = consultar(juego)

    assert (estado["finalizada"], estado["en_curso"], estado["ganador"]) == (True, False, "red")
    assert estado["tiempo"]["restante"] is None


def test_no_expone_posiciones_tokens_ni_correos(consultar):
    juego = partida_en_curso()
    juego.iniciar_por("red", {"condition": "time", "value": 1})

    estado = consultar(juego)

    assert set(estado) == CLAVES
    assert all(set(jugador) == CLAVES_JUGADOR for jugador in estado["jugadores"].values())
    assert set(estado["reactor"]) == {"estado", "operador"}
    assert set(estado["tiempo"]) == {"transcurrido", "limite", "restante", "prorrogas"}


def test_el_servidor_tcp_usa_la_misma_partida_que_la_api(monkeypatch):
    recibido = {}
    listo = threading.Event()

    class SocketFalso:
        def close(self):
            pass

    def servir_falso(servidor, **kwargs):
        recibido.update(kwargs)
        listo.set()

    monkeypatch.setattr(main, "crear_socket_servidor", lambda host, port: SocketFalso())
    monkeypatch.setattr(main, "servir", servir_falso)
    with TestClient(main.app):
        assert listo.wait(2)

    assert recibido["estado_juego"] is main.partida


def test_la_partida_compartida_guarda_en_el_almacen_de_la_api(monkeypatch, tmp_path):
    almacen = AlmacenResultados(tmp_path / "resultados.json")
    monkeypatch.setattr(main, "resultados", almacen)
    juego = main.partida
    try:
        juego.unir_jugador("ana")
        juego.unir_jugador("beto")
        juego.iniciar_por("red", {"condition": "points", "value": 20})
        juego._jugadores["red"].puntos = 20
        juego.avanzar(0.1)

        assert juego.estado()["match"]["result_saved"] is True
        assert almacen.ranking()[0]["usuario"] == "ana"
    finally:
        juego.liberar_puesto("red")
        juego.liberar_puesto("blue")
