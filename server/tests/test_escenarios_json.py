import pytest

from app.game_state import EstadoJuego, Rechazo


def test_arena_clasica_desde_json():
    juego = EstadoJuego()

    juego._seleccionar_escenario("arena_clasica")

    assert len(juego._obstaculos) == 4
    assert len(juego._puertas) == 1
    assert juego._reactor.x == 780
    assert juego._reactor.y == 430


def test_laberinto_desde_json():
    juego = EstadoJuego()

    juego._seleccionar_escenario("laberinto")

    assert len(juego._obstaculos) == 8
    assert len(juego._puertas) == 2


def test_posiciones_iniciales_desde_json():
    juego = EstadoJuego()

    juego._seleccionar_escenario("laberinto")
    juego._reiniciar_estado()

    assert juego._jugadores["red"].x == 100
    assert juego._jugadores["red"].y == 100
    assert juego._jugadores["blue"].x == 1460
    assert juego._jugadores["blue"].y == 760


def test_escenario_inexistente():
    juego = EstadoJuego()

    with pytest.raises(Rechazo) as error:
        juego._seleccionar_escenario("escenario_inexistente")

    assert error.value.codigo == "invalid_scenario"
