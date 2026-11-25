"""R\u00e9cords al cerrar la partida: se comparan con lo guardado antes de ella (US-26)."""

from app.game_state import EstadoJuego
from app.resultados_store import AlmacenResultados
from app.socket_server import guardar_resultado_final, records_previos


def resultado(rojo, azul):
    return {"players": {"red": {"username": "ana", "score": rojo},
                        "blue": {"username": "beto", "score": azul}}}


def almacen_con_historia(tmp_path):
    almacen = AlmacenResultados(tmp_path / "resultados.json")
    almacen.guardar_resultado("previa", {"red": {"usuario": "ana", "score": 10},
                                         "blue": {"usuario": "beto", "score": 5}}, "red", 60)
    return almacen


def test_superar_el_mejor_puntaje_marca_record_personal_y_global(tmp_path):
    records = records_previos(almacen_con_historia(tmp_path), resultado(12, 3))

    assert records["red"] == {"previous_best": 10, "personal_best": True, "global_best": True}
    assert records["blue"] == {"previous_best": 5, "personal_best": False, "global_best": False}


def test_record_personal_sin_superar_el_global(tmp_path):
    records = records_previos(almacen_con_historia(tmp_path), resultado(8, 6))

    assert records["red"]["personal_best"] is False
    assert records["blue"] == {"previous_best": 5, "personal_best": True, "global_best": False}


def test_sin_puntos_no_hay_records(tmp_path):
    records = records_previos(AlmacenResultados(tmp_path / "resultados.json"), resultado(0, 0))

    assert not any(r["personal_best"] or r["global_best"] for r in records.values())


def test_solo_el_maximo_de_la_partida_puede_ser_record_global(tmp_path):
    records = records_previos(almacen_con_historia(tmp_path), resultado(15, 11))

    assert records["red"]["global_best"] is True
    assert records["blue"]["global_best"] is False
    assert records["blue"]["personal_best"] is True


def cerrar_partida(juego, rojo, azul):
    juego.unir_jugador("ana")
    juego.unir_jugador("beto")
    juego.iniciar_por("red", {"condition": "points", "value": 20})
    juego._jugadores["red"].puntos = rojo
    juego._jugadores["blue"].puntos = azul
    juego.avanzar(0.1)
    return juego.estado()["match"]


def test_el_estado_final_trae_los_records_calculados_antes_de_guardar(tmp_path):
    almacen = almacen_con_historia(tmp_path)
    juego = EstadoJuego(
        guardianes=(), eventos=False,
        guardar_resultado=lambda r: guardar_resultado_final(almacen, r),
        calcular_records=lambda r: records_previos(almacen, r),
    )

    partida = cerrar_partida(juego, 20, 4)

    assert partida["result_saved"] is True
    # Si se calculara despu\u00e9s de guardar, el mejor previo ya ser\u00eda 20 y no habr\u00eda r\u00e9cord.
    assert partida["result"]["records"]["red"] == {"previous_best": 10, "personal_best": True, "global_best": True}


def test_un_fallo_al_calcular_records_no_impide_cerrar_ni_guardar(tmp_path):
    almacen = AlmacenResultados(tmp_path / "resultados.json")

    def fallar(_):
        raise ValueError("almacen corrupto")

    juego = EstadoJuego(
        guardianes=(), eventos=False,
        guardar_resultado=lambda r: guardar_resultado_final(almacen, r),
        calcular_records=fallar,
    )

    partida = cerrar_partida(juego, 20, 4)

    assert partida["finished"] is True
    assert partida["result_saved"] is True
    assert "records" not in partida["result"]
