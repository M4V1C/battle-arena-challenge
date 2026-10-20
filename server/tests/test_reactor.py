import pytest

from app.game_state import EstadoJuego


def entradas(red=(0, 0, 0, 0), blue=(0, 0, 0, 0)) -> dict:
    """(x, y, shoot, interact) por jugador."""
    return {
        nombre: {"x": v[0], "y": v[1], "shoot": v[2], "interact": v[3]}
        for nombre, v in (("red", red), ("blue", blue))
    }


def juego_junto_al_reactor() -> EstadoJuego:
    juego = EstadoJuego(obstaculos=())
    # Reactor en (780, 430); rojo a su izquierda y azul a su derecha.
    juego._jugadores["red"].x, juego._jugadores["red"].y = 740, 430
    juego._jugadores["blue"].x, juego._jugadores["blue"].y = 820, 430
    return juego


def avanzar(juego: EstadoJuego, segundos: float) -> dict:
    for _ in range(round(segundos * 60)):
        juego.avanzar(1 / 60)
    return juego.estado()


def test_reactor_esta_en_el_centro_y_es_solido():
    juego = EstadoJuego(obstaculos=())
    reactor = juego.estado()["reactor"]
    assert (reactor["x"], reactor["y"], reactor["size"]) == (780, 430, 40)
    assert reactor["ring_radius"] == 60

    juego._jugadores["red"].x, juego._jugadores["red"].y = 600, 430
    juego.actualizar_entradas(entradas(red=(1, 0, 0, 0)))
    assert avanzar(juego, 2)["players"]["red"]["x"] == pytest.approx(740)


def test_interactuar_en_rango_congela_y_volver_a_interactuar_libera():
    juego = juego_junto_al_reactor()
    juego.actualizar_entradas(entradas(red=(-1, 0, 0, 1)))
    juego.actualizar_entradas(entradas(red=(-1, 0, 1, 1)))

    estado = avanzar(juego, 0.5)
    assert estado["players"]["red"]["frozen"] is True
    assert estado["reactor"]["operator"] == "red"
    assert estado["players"]["red"]["x"] == 740
    assert estado["projectiles"] == []

    juego.actualizar_entradas(entradas(red=(-1, 0, 1, 2)))
    estado = avanzar(juego, 0.5)
    assert estado["players"]["red"]["frozen"] is False
    assert estado["reactor"]["operator"] is None
    assert estado["players"]["red"]["x"] < 740


def test_interactuar_fuera_de_rango_no_congela():
    juego = EstadoJuego()
    estado = juego.actualizar_entradas(entradas(red=(0, 0, 0, 1)))

    assert estado["players"]["red"]["frozen"] is False
    assert estado["reactor"]["operator"] is None


def test_solo_un_jugador_puede_operar_el_reactor():
    juego = juego_junto_al_reactor()
    juego.actualizar_entradas(entradas(red=(0, 0, 0, 1)))
    estado = juego.actualizar_entradas(entradas(red=(0, 0, 0, 1), blue=(0, 0, 0, 1)))

    assert estado["reactor"]["operator"] == "red"
    assert estado["players"]["blue"]["frozen"] is False


def test_operar_el_reactor_suma_un_punto_cada_medio_segundo():
    juego = juego_junto_al_reactor()
    juego.actualizar_entradas(entradas(red=(0, 0, 0, 1)))

    estado = avanzar(juego, 2.05)

    assert estado["players"]["red"]["score"] == 4
    assert estado["players"]["blue"]["score"] == 0


def test_puntaje_se_conserva_al_liberar_el_reactor():
    juego = juego_junto_al_reactor()
    juego.actualizar_entradas(entradas(red=(0, 0, 0, 1)))
    avanzar(juego, 1.05)
    juego.actualizar_entradas(entradas(red=(0, 0, 0, 2)))

    estado = avanzar(juego, 1)

    assert estado["players"]["red"]["score"] == 2


def test_terminar_partida_reinicia_todo_el_estado():
    juego = juego_junto_al_reactor()
    juego.actualizar_entradas(entradas(red=(0, 0, 0, 1)))
    avanzar(juego, 1.05)
    juego.actualizar_entradas(entradas(red=(0, 0, 0, 1), blue=(0, 0, 1, 0)))

    juego.reiniciar_partida()

    assert juego.estado() == EstadoJuego(obstaculos=()).estado()
    assert juego.avanzar(0.5) == EstadoJuego(obstaculos=()).estado()
