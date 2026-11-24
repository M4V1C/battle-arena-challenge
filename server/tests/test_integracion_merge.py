"""Contratos entre el motor US-21/22/25 y la API de develop."""

from app.game_state import EstadoJuego, Rechazo
from app.resultados_store import AlmacenResultados
from app.socket_server import guardar_resultado_final


def test_resultado_del_motor_persiste_una_vez_y_alimenta_ranking(tmp_path):
    almacen = AlmacenResultados(tmp_path / "resultados.json")
    llamadas = []

    def guardar(resultado):
        llamadas.append(resultado["id"])
        return guardar_resultado_final(almacen, resultado)

    juego = EstadoJuego(guardianes=(), eventos=False, guardar_resultado=guardar)
    juego.unir_jugador("ana")
    juego.unir_jugador("beto")
    juego.iniciar_partida({"condition": "points", "value": 1})
    juego._jugadores["red"].puntos = 1
    final = juego.avanzar(0)
    juego.avanzar(5)

    assert final["match"]["game_over"]["match_id"] == final["match"]["match_id"]
    assert final["match"]["result_saved"] is True
    assert llamadas == [final["match"]["match_id"]]
    assert len(almacen.listar()) == 1
    assert almacen.ranking()[0]["usuario"] == "ana"
    assert almacen.historial("beto")[0]["resultado"] == "derrota"


def test_prorroga_conserva_match_id_y_guarda_solo_al_final(tmp_path):
    almacen = AlmacenResultados(tmp_path / "resultados.json")
    juego = EstadoJuego(
        guardianes=(), eventos=False,
        guardar_resultado=lambda resultado: guardar_resultado_final(almacen, resultado),
    )
    juego.unir_jugador("ana")
    juego.unir_jugador("beto")
    inicial = juego.iniciar_partida({"condition": "time", "value": 1})
    empate = juego.avanzar(60)

    assert empate["match"]["overtime"] == 1
    assert empate["match"]["match_id"] == inicial["match"]["match_id"]
    assert almacen.listar() == []

    juego._jugadores["blue"].puntos = 2
    final = juego.avanzar(120)
    assert final["match"]["finished"] is True
    assert final["match"]["match_id"] == inicial["match"]["match_id"]
    assert len(almacen.listar()) == 1


def test_escenario_cargado_no_cambia_durante_partida():
    juego = EstadoJuego()
    juego.iniciar_partida({"condition": "time", "value": 1}, "laberinto")
    assert juego.estado()["scenario"]["id"] == "laberinto"
    try:
        juego._seleccionar_escenario("arena_clasica")
    except Rechazo as error:
        assert error.codigo == "match_in_progress"
    else:
        raise AssertionError("El escenario cambió durante la partida.")
    assert juego.estado()["scenario"]["id"] == "laberinto"
