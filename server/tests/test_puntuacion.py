"""US-18 y US-19: estado del reactor, reglas.json y puntos solo competitivos."""

import json

import pytest

from app.game_state import EstadoJuego
from app.reglas import ARCHIVO_REGLAS, Reglas, cargar_reglas, validar_reglas
from tests.helpers import partida_iniciada

# Reactor en (780, 430): rojo a su izquierda (en rango) y azul a su derecha.
EN_RANGO_ROJO = (740, 430)
EN_RANGO_AZUL = (820, 430)


def entrada(x=0, y=0, shoot=0, interact=0) -> dict:
    return {"x": x, "y": y, "shoot": shoot, "interact": interact}


def entradas(red=None, blue=None) -> dict:
    return {"red": red or entrada(), "blue": blue or entrada()}


def juego_junto_al_reactor(**kwargs) -> EstadoJuego:
    juego = partida_iniciada(obstaculos=(), **kwargs)
    juego._jugadores["red"].x, juego._jugadores["red"].y = EN_RANGO_ROJO
    juego._jugadores["blue"].x, juego._jugadores["blue"].y = EN_RANGO_AZUL
    return juego


def avanzar(juego: EstadoJuego, segundos: float) -> dict:
    for _ in range(round(segundos * 60)):
        juego.avanzar(1 / 60)
    return juego.estado()


def rechazos(estado: dict, puesto: str) -> list[str]:
    return [
        n["code"]
        for n in estado["notifications"]
        if n["kind"] == "reject" and n["for"] == puesto
    ]


# ---------- reglas.json ----------


def test_reglas_del_archivo_son_las_documentadas():
    assert cargar_reglas() == Reglas(puntos_por_energia=1, intervalo_extraccion=0.5)
    assert ARCHIVO_REGLAS.name == "reglas.json"


def test_reglas_ignoran_claves_que_agregan_otras_funciones(tmp_path):
    ruta = tmp_path / "reglas.json"
    ruta.write_text(
        json.dumps({"puntos_por_energia": 2, "intervalo_extraccion": 1, "otra": 9}),
        encoding="utf-8",
    )

    assert cargar_reglas(ruta) == Reglas(2, 1.0)


@pytest.mark.parametrize(
    "datos",
    [
        [],
        {},
        {"puntos_por_energia": 1},
        {"intervalo_extraccion": 0.5},
        {"puntos_por_energia": 0, "intervalo_extraccion": 0.5},
        {"puntos_por_energia": -1, "intervalo_extraccion": 0.5},
        {"puntos_por_energia": 1.5, "intervalo_extraccion": 0.5},
        {"puntos_por_energia": True, "intervalo_extraccion": 0.5},
        {"puntos_por_energia": "1", "intervalo_extraccion": 0.5},
        {"puntos_por_energia": 1, "intervalo_extraccion": 0},
        {"puntos_por_energia": 1, "intervalo_extraccion": -0.5},
        {"puntos_por_energia": 1, "intervalo_extraccion": float("nan")},
        {"puntos_por_energia": 1, "intervalo_extraccion": float("inf")},
        {"puntos_por_energia": 1, "intervalo_extraccion": "0.5"},
        {"puntos_por_energia": 1, "intervalo_extraccion": True},
    ],
)
def test_reglas_invalidas_son_rechazadas(datos):
    with pytest.raises(ValueError):
        validar_reglas(datos)


def test_reglas_inexistentes_fallan_al_cargar(tmp_path):
    with pytest.raises(OSError):
        cargar_reglas(tmp_path / "no_existe.json")


def test_puntos_e_intervalo_salen_de_las_reglas():
    juego = juego_junto_al_reactor(reglas=Reglas(puntos_por_energia=3, intervalo_extraccion=1.0))
    juego.actualizar_entradas(entradas(red=entrada(interact=1)))

    assert avanzar(juego, 2.05)["players"]["red"]["score"] == 6


def test_objetivo_por_puntos_respeta_las_reglas():
    juego = juego_junto_al_reactor(reglas=Reglas(puntos_por_energia=3, intervalo_extraccion=1.0))
    juego.iniciar_partida({"condition": "points", "value": 20})
    juego._jugadores["red"].x, juego._jugadores["red"].y = EN_RANGO_ROJO
    juego.actualizar_entradas(entradas(red=entrada(interact=1)))

    assert not avanzar(juego, 6.5)["match"]["finished"]
    estado = avanzar(juego, 1)

    # 7 extracciones de 3 puntos: 21 >= 20, y termina justo en el segundo 7.
    assert estado["match"]["finished"] is True
    assert estado["players"]["red"]["score"] == 21
    assert estado["match"]["elapsed"] == pytest.approx(7)


# ---------- Estado del reactor ----------


def test_reactor_empieza_disponible():
    reactor = EstadoJuego().estado()["reactor"]

    assert reactor["status"] == "available"
    assert reactor["operator"] is None


def test_reactor_pasa_a_en_uso_y_vuelve_a_disponible():
    juego = juego_junto_al_reactor()

    juego.actualizar_entradas(entradas(red=entrada(interact=1)))
    en_uso = avanzar(juego, 0.2)
    juego.actualizar_entradas(entradas(red=entrada(interact=2)))
    libre = avanzar(juego, 0.2)

    assert (en_uso["reactor"]["status"], en_uso["reactor"]["operator"]) == ("in_use", "red")
    assert (libre["reactor"]["status"], libre["reactor"]["operator"]) == ("available", None)


def test_extracting_marca_solo_al_operador_y_frozen_ya_no_significa_operar():
    juego = juego_junto_al_reactor()
    juego.actualizar_entradas(entradas(red=entrada(interact=1)))

    jugadores = avanzar(juego, 0.2)["players"]

    assert (jugadores["red"]["extracting"], jugadores["red"]["frozen"]) == (True, False)
    assert (jugadores["blue"]["extracting"], jugadores["blue"]["frozen"]) == (False, False)


# ---------- Rechazos de la extracción (CA-18.5) ----------


def test_extraer_fuera_de_rango_se_rechaza_con_motivo():
    juego = partida_iniciada(obstaculos=())

    estado = juego.actualizar_entradas(entradas(red=entrada(interact=1)))

    assert estado["reactor"]["operator"] is None
    assert rechazos(estado, "red") == ["out_of_range"]
    assert rechazos(estado, "blue") == []
    aviso = estado["notifications"][-1]
    assert aviso["message"] and aviso["severity"] == "warning"


def test_extraer_con_el_reactor_ocupado_se_rechaza():
    juego = juego_junto_al_reactor()
    juego.actualizar_entradas(entradas(red=entrada(interact=1)))

    estado = juego.actualizar_entradas(
        entradas(red=entrada(interact=1), blue=entrada(interact=1))
    )

    assert estado["reactor"]["operator"] == "red"
    assert rechazos(estado, "blue") == ["reactor_busy"]


def test_extraer_antes_de_iniciar_la_partida_se_rechaza():
    juego = EstadoJuego(obstaculos=())
    juego._jugadores["red"].x, juego._jugadores["red"].y = EN_RANGO_ROJO

    estado = juego.actualizar_entradas(entradas(red=entrada(interact=1)))

    assert estado["reactor"]["operator"] is None
    assert rechazos(estado, "red") == ["match_not_active"]


def test_extraer_despues_de_terminar_se_rechaza():
    juego = juego_junto_al_reactor()
    juego._jugadores["blue"].puntos = 20
    assert juego.avanzar(0.1)["match"]["finished"] is True

    estado = juego.actualizar_entradas(entradas(red=entrada(interact=1)))

    assert estado["reactor"]["operator"] is None
    assert rechazos(estado, "red") == ["match_not_active"]


def test_extraccion_valida_no_genera_rechazos():
    juego = juego_junto_al_reactor()

    estado = juego.actualizar_entradas(entradas(red=entrada(interact=1)))

    assert estado["reactor"]["operator"] == "red"
    assert estado["notifications"] == []


def test_una_pulsacion_repetida_se_rechaza_una_sola_vez():
    juego = partida_iniciada(obstaculos=())
    for _ in range(10):
        estado = juego.actualizar_entradas(entradas(red=entrada(interact=1)))

    assert rechazos(estado, "red") == ["out_of_range"]


# ---------- Solo hay puntos competitivos (CA-19.4 / CA-19.5) ----------


def test_moverse_por_la_arena_no_da_puntos():
    juego = partida_iniciada()
    juego.actualizar_entradas(entradas(red=entrada(x=1, y=1), blue=entrada(x=-1, y=-1)))

    estado = avanzar(juego, 10)

    assert [j["score"] for j in estado["players"].values()] == [0, 0]


def test_estar_junto_al_reactor_sin_extraer_no_da_puntos():
    juego = juego_junto_al_reactor()

    estado = avanzar(juego, 5)

    assert [j["score"] for j in estado["players"].values()] == [0, 0]


def test_disparar_o_pulsar_fuera_de_rango_no_da_puntos():
    juego = partida_iniciada()
    for n in range(1, 6):
        juego.actualizar_entradas(entradas(red=entrada(shoot=n, interact=n)))
        juego.avanzar(0.5)

    estado = avanzar(juego, 3)

    assert [j["score"] for j in estado["players"].values()] == [0, 0]


def test_solo_puntua_el_operador():
    juego = juego_junto_al_reactor()
    juego.actualizar_entradas(entradas(red=entrada(interact=1)))
    juego.actualizar_entradas(entradas(red=entrada(interact=1), blue=entrada(interact=1)))

    estado = avanzar(juego, 2.05)

    assert (estado["players"]["red"]["score"], estado["players"]["blue"]["score"]) == (4, 0)


def test_mensajes_duplicados_no_suman_ni_alternan_la_extraccion():
    juego = juego_junto_al_reactor()
    for _ in range(20):
        juego.actualizar_entradas(entradas(red=entrada(interact=1)))

    estado = avanzar(juego, 1.05)

    assert estado["reactor"]["operator"] == "red"
    assert estado["players"]["red"]["score"] == 2


def test_al_soltar_el_reactor_dejan_de_sumar_puntos():
    juego = juego_junto_al_reactor()
    juego.actualizar_entradas(entradas(red=entrada(interact=1)))
    avanzar(juego, 1.05)
    juego.actualizar_entradas(entradas(red=entrada(interact=2)))

    assert avanzar(juego, 3)["players"]["red"]["score"] == 2


def test_al_desconectarse_el_operador_dejan_de_sumar_puntos():
    juego = partida_iniciada(obstaculos=())
    juego.unir_jugador("ana")
    juego.unir_jugador("beto")
    juego._jugadores["red"].x, juego._jugadores["red"].y = EN_RANGO_ROJO
    juego.actualizar_entradas(entradas(red=entrada(interact=1)))
    avanzar(juego, 1.05)

    juego.liberar_puesto("red")
    estado = avanzar(juego, 3)

    assert estado["players"]["red"]["score"] == 2
    assert estado["reactor"]["status"] == "available"


def test_no_se_suman_puntos_antes_de_iniciar_ni_despues_de_terminar():
    sin_iniciar = EstadoJuego(obstaculos=())
    sin_iniciar._jugadores["red"].x, sin_iniciar._jugadores["red"].y = EN_RANGO_ROJO
    sin_iniciar.actualizar_entradas(entradas(red=entrada(interact=1)))
    assert avanzar(sin_iniciar, 3)["players"]["red"]["score"] == 0

    juego = juego_junto_al_reactor()
    juego.iniciar_partida({"condition": "points", "value": 2})
    juego._jugadores["red"].x, juego._jugadores["red"].y = EN_RANGO_ROJO
    juego.actualizar_entradas(entradas(red=entrada(interact=1)))
    final = avanzar(juego, 5)
    assert final["match"]["finished"] is True
    assert final["players"]["red"]["score"] == 2
    assert avanzar(juego, 5) == final
