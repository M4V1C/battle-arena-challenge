import math

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


def test_rotacion_separa_objetivo_y_orientacion_real():
    juego = EstadoJuego(obstaculos=())
    estado = juego.actualizar_entradas(entradas(red=(0, 1, 0, 0)))
    rojo = estado["players"]["red"]
    assert (rojo["dir_x"], rojo["dir_y"]) == (1, 0)
    assert (rojo["move_x"], rojo["move_y"]) == (0, 1)
    rojo = juego.avanzar(0.125)["players"]["red"]
    assert math.atan2(rojo["dir_y"], rojo["dir_x"]) == pytest.approx(math.pi / 4)
    assert rojo["x"] > 100 and rojo["y"] > 100


def test_rotacion_alineada_continua_movimiento_mientras_hay_entrada():
    juego = EstadoJuego(obstaculos=())
    juego.actualizar_entradas(entradas(red=(0, 1, 0, 0)))
    estado = juego.avanzar(0.25)["players"]["red"]
    assert (estado["dir_x"], estado["dir_y"]) == (0, 1)
    siguiente = juego.avanzar(1)["players"]["red"]
    assert siguiente["x"] == pytest.approx(estado["x"])
    assert siguiente["y"] == pytest.approx(estado["y"] + juego.VELOCIDAD)
    juego.actualizar_entradas(entradas())
    detenido = juego.estado()["players"]["red"]
    assert juego.avanzar(1)["players"]["red"] == detenido


def test_movimiento_empieza_con_entrada_alineada_y_no_es_automatico():
    juego = EstadoJuego(obstaculos=())
    juego.actualizar_entradas(entradas())
    assert juego.avanzar(0.1)["players"]["red"]["x"] == 100
    juego.actualizar_entradas(entradas(red=(1, 0, 0, 0)))
    assert juego.avanzar(0.1)["players"]["red"]["x"] == pytest.approx(124)


def test_tick_incluye_movimiento_recto_despues_de_terminar_el_giro():
    juego = EstadoJuego(obstaculos=())
    juego.actualizar_entradas(entradas(red=(0, 1, 0, 0)))
    rojo = juego.avanzar(0.5)["players"]["red"]
    radio = juego.VELOCIDAD / juego.VELOCIDAD_GIRO
    assert rojo["x"] == pytest.approx(100 + radio)
    assert rojo["y"] == pytest.approx(100 + radio + juego.VELOCIDAD * 0.25)


def test_rotacion_no_depende_de_los_paquetes_ni_del_tick():
    posiciones = []
    for frecuencia in (30, 60, 120):
        juego = EstadoJuego(obstaculos=())
        for _ in range(frecuencia // 2):
            juego.actualizar_entradas(entradas(red=(-1, 0, 0, 0)))
            juego.avanzar(1 / frecuencia)
        posiciones.append(juego.estado()["players"]["red"])
    for posicion in posiciones[1:]:
        assert posicion == pytest.approx(posiciones[0])


def test_rotacion_de_media_vuelta_no_anula_el_vector():
    juego = EstadoJuego(obstaculos=())
    juego.actualizar_entradas(entradas(red=(-1, 0, 0, 0)))
    rojo = juego.avanzar(0.25)["players"]["red"]
    assert math.hypot(rojo["dir_x"], rojo["dir_y"]) == pytest.approx(1)
    assert abs(rojo["dir_y"]) == pytest.approx(1)
    rojo = juego.avanzar(0.25)["players"]["red"]
    assert (rojo["dir_x"], rojo["dir_y"]) == (-1, 0)


def test_rotacion_toma_el_camino_corto_al_cruzar_pi():
    juego = EstadoJuego(obstaculos=())
    angulo = math.radians(179)
    juego._jugadores["red"].dir_x = math.cos(angulo)
    juego._jugadores["red"].dir_y = math.sin(angulo)
    objetivo = math.radians(-179)
    juego.actualizar_entradas(entradas(red=(math.cos(objetivo), math.sin(objetivo), 0, 0)))
    rojo = juego.avanzar(1 / 360)["players"]["red"]
    assert rojo["dir_x"] == pytest.approx(-1)
    assert rojo["dir_y"] == pytest.approx(0, abs=1e-9)


def test_soltar_entrada_detiene_giro_y_desplazamiento():
    juego = EstadoJuego(obstaculos=())
    juego.actualizar_entradas(entradas(red=(0, 1, 0, 0)))
    juego.avanzar(0.05)
    rojo = juego.actualizar_entradas(entradas())["players"]["red"]
    assert (rojo["move_x"], rojo["move_y"]) == (0, 0)
    assert juego.avanzar(0.5)["players"]["red"] == rojo


def test_disparo_durante_giro_sigue_orientacion_real_no_objetivo():
    juego = EstadoJuego(obstaculos=())
    juego.actualizar_entradas(entradas(red=(0, 1, 0, 0)))
    juego.avanzar(0.125)
    juego.actualizar_entradas(entradas(red=(0, -1, 1, 0)))
    proyectil = juego._proyectiles[0]
    assert proyectil.vx == pytest.approx(juego.VELOCIDAD_PROYECTIL / math.sqrt(2))
    assert proyectil.vy == pytest.approx(juego.VELOCIDAD_PROYECTIL / math.sqrt(2))


def test_entrada_analogica_modula_desplazamiento_pero_no_velocidad_de_giro():
    resultados = []
    for intensidad in (0.5, 1.0):
        juego = EstadoJuego(obstaculos=())
        juego.actualizar_entradas(entradas(red=(0, intensidad, 0, 0)))
        resultados.append(juego.avanzar(0.125)["players"]["red"])
    medio, completo = resultados
    assert medio["dir_x"] == pytest.approx(completo["dir_x"])
    assert medio["dir_y"] == pytest.approx(completo["dir_y"])
    assert medio["x"] - 100 == pytest.approx((completo["x"] - 100) / 2)
    assert medio["y"] - 100 == pytest.approx((completo["y"] - 100) / 2)


def test_ruido_analogico_no_produce_giro_ni_movimiento():
    juego = EstadoJuego()
    juego.actualizar_entradas(entradas(red=(0.05, -0.05, 0, 0)))
    rojo = juego.avanzar(1)["players"]["red"]
    assert (rojo["x"], rojo["y"], rojo["dir_x"], rojo["dir_y"]) == (100, 100, 1, 0)
    assert (rojo["move_x"], rojo["move_y"]) == (0, 0)


@pytest.mark.parametrize("valor", [float("nan"), float("inf"), -1.1, "0.5", True])
def test_entrada_analogica_invalida_no_cambia_estado(valor):
    juego = EstadoJuego()
    anterior = juego.estado()
    with pytest.raises(ValueError):
        juego.actualizar_entradas(entradas(red=(valor, 0, 0, 0)))
    assert juego.estado() == anterior


def test_direccion_sigue_al_movimiento_y_se_conserva_al_detenerse():
    juego = EstadoJuego(obstaculos=())
    juego.actualizar_entradas(entradas(red=(0, 1, 0, 0)))
    juego.actualizar_entradas(entradas(red=(-1, -1, 0, 0)))
    avanzar(juego, 0.5)
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
    juego.actualizar_entradas(entradas(red=(-1, 0, 0, 0)))
    avanzar(juego, 0.5)
    juego.actualizar_entradas(entradas(red=(0, 0, 1, 0)))

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
