from victory_screen import PantallaVictoria


def crear_estado(ganador="red", duracion=332, prorrogas=0):
    return {
        "match": {
            "finished": True,
            "winner": ganador,
            "elapsed": duracion,
            "condition": "points",
            "value": 20,
            "overtime": prorrogas,
        },
        "players": {
            "red": {"score": 20},
            "blue": {"score": 15},
        },
    }


def crear_pantalla(estado):
    return PantallaVictoria(
        estado=estado,
        avatares={"red": "avatar_1", "blue": "avatar_1"},
        nombres={"red": "Jugador Rojo", "blue": "Jugador Azul"},
    )


def test_podio_ganador_rojo():
    pantalla = crear_pantalla(crear_estado("red"))

    assert pantalla._ganador == "red"
    assert pantalla._podio == [("red", 1), ("blue", 2)]


def test_podio_ganador_azul():
    pantalla = crear_pantalla(crear_estado("blue"))

    assert pantalla._ganador == "blue"
    assert pantalla._podio == [("blue", 1), ("red", 2)]


def test_duracion_partida():
    pantalla = crear_pantalla(crear_estado(duracion=332))

    assert pantalla._minutos == 5
    assert pantalla._segundos == 32


def test_prorrogas():
    pantalla = crear_pantalla(crear_estado(prorrogas=2))

    assert pantalla._prorrogas == 2


def test_puntuaciones_finales():
    pantalla = crear_pantalla(crear_estado())

    assert pantalla._puntos_rojo == 20
    assert pantalla._puntos_azul == 15