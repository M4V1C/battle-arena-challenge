import pytest

from app.game_state import EstadoJuego, Obstaculo


def entradas(red=(0, 0, 0, 0), blue=(0, 0, 0, 0)) -> dict:
    """(x, y, shoot, interact) por jugador."""
    return {
        nombre: {"x": v[0], "y": v[1], "shoot": v[2], "interact": v[3]}
        for nombre, v in (("red", red), ("blue", blue))
    }


def avanzar(juego: EstadoJuego, segundos: float) -> dict:
    for _ in range(round(segundos * 60)):
        juego.avanzar(1 / 60)
    return juego.estado()


def test_direccion_sigue_al_movimiento_y_se_conserva_al_detenerse():
    juego = EstadoJuego(obstaculos=())
    juego.actualizar_entradas(entradas(red=(0, 1, 0, 0)))
    juego.actualizar_entradas(entradas(red=(-1, -1, 0, 0)))
    juego.actualizar_entradas(entradas())

    rojo = juego.estado()["players"]["red"]
    assert rojo["dir_x"] == pytest.approx(-0.7071, abs=1e-4)
    assert rojo["dir_y"] == pytest.approx(-0.7071, abs=1e-4)


def test_disparo_avanza_en_la_direccion_del_jugador():
    juego = EstadoJuego(obstaculos=())
    juego.actualizar_entradas(entradas(red=(0, 0, 1, 0)))

    estado = avanzar(juego, 0.1)

    (proyectil,) = estado["projectiles"]
    assert proyectil["x"] == pytest.approx(116 + 90)
    assert proyectil["y"] == pytest.approx(116)


def test_mismo_contador_no_dispara_dos_veces():
    juego = EstadoJuego(obstaculos=())
    juego.actualizar_entradas(entradas(red=(0, 0, 1, 0)))
    juego.actualizar_entradas(entradas(red=(0, 0, 1, 0)))

    assert len(juego.estado()["projectiles"]) == 1


def test_disparo_desaparece_al_chocar_con_obstaculo():
    juego = EstadoJuego(obstaculos=(Obstaculo(300, 0, 5, 900),))
    juego.actualizar_entradas(entradas(red=(0, 0, 1, 0)))

    assert avanzar(juego, 0.5)["projectiles"] == []


def test_disparo_desaparece_al_salir_del_mapa():
    juego = EstadoJuego(obstaculos=())
    juego.actualizar_entradas(entradas(red=(-1, 0, 1, 0)))

    assert avanzar(juego, 0.5)["projectiles"] == []


def test_disparo_desaparece_al_impactar_otro_jugador_pero_no_al_tirador():
    juego = EstadoJuego(obstaculos=())
    juego._jugadores["blue"].x, juego._jugadores["blue"].y = 400, 100
    juego.actualizar_entradas(entradas(red=(0, 0, 1, 0)))

    assert len(avanzar(juego, 1 / 60)["projectiles"]) == 1
    assert avanzar(juego, 0.5)["projectiles"] == []


def test_interactuar_muestra_circulo_brevemente():
    juego = EstadoJuego()
    juego.actualizar_entradas(entradas(red=(0, 0, 0, 1)))

    assert juego.estado()["players"]["red"]["interacting"] is True
    assert avanzar(juego, 0.5)["players"]["red"]["interacting"] is False


@pytest.mark.parametrize("valor", [-1, 1.5, True, "1"])
def test_contador_invalido_es_rechazado(valor):
    juego = EstadoJuego()
    datos = entradas()
    datos["red"]["shoot"] = valor

    with pytest.raises(ValueError):
        juego.actualizar_entradas(datos)
