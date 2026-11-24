"""US-21: persecución, contacto, estados y autoridad del servidor."""

import json

import pytest

from app.game_state import EstadoJuego, Obstaculo, Trampa
from app.guardianes import Guardian
from app.reglas import Reglas, validar_reglas
from app.socket_server import SesionCliente, procesar_mensaje
from tests.helpers import partida_iniciada


def test_mapa_inicial_tiene_cuatro_guardianes_en_extremos():
    estado = EstadoJuego(semilla=1).estado()
    guardianes = estado["guardians"]
    assert len(guardianes) == 4
    assert {g["id"] for g in guardianes} == {"noroeste", "noreste", "suroeste", "sureste"}
    assert all(g["size"] == 40 for g in guardianes)
    assert all(g["x"] < 80 or g["x"] > 1500 for g in guardianes)
    assert all(g["y"] < 80 or g["y"] > 800 for g in guardianes)


def test_guardian_persigue_al_mas_cercano_que_no_este_congelado():
    juego = partida_iniciada(obstaculos=(), guardianes=(Guardian("g", 100, 200),))
    primero = juego.avanzar(0.1)["guardians"][0]
    assert primero["target"] == "red"
    assert primero["y"] < 200
    juego._jugadores["red"].bloqueo_restante = 5
    segundo = juego.avanzar(0.1)["guardians"][0]
    assert segundo["target"] == "blue"
    assert segundo["x"] > primero["x"]
    assert ((segundo["x"] - primero["x"]) ** 2 +
            (segundo["y"] - primero["y"]) ** 2) ** 0.5 <= 12.01


def test_guardian_espera_si_ambos_estan_congelados():
    juego = partida_iniciada(obstaculos=(), guardianes=(Guardian("g", 500, 500),))
    for jugador in juego._jugadores.values():
        jugador.bloqueo_restante = 5
    guardian = juego.avanzar(1)["guardians"][0]
    assert (guardian["x"], guardian["y"], guardian["target"]) == (500, 500, None)


def test_contacto_aturde_bloquea_acciones_y_no_suma_puntos():
    juego = partida_iniciada(obstaculos=(), guardianes=(Guardian("g", 100, 100),))
    impacto = juego.avanzar(0)["players"]["red"]
    assert (impacto["status"], impacto["frozen"], impacto["score"]) == ("stunned", True, 0)
    assert impacto["stun_remaining"] == pytest.approx(2)
    juego.actualizar_entradas({"red": {"x": 1, "y": 0, "interact": 1, "shoot": 1},
                              "blue": {"x": 0, "y": 0}})
    estado = juego.avanzar(1)
    assert estado["players"]["red"]["x"] == 100
    assert estado["projectiles"] == []
    assert estado["reactor"]["operator"] is None
    assert [n["code"] for n in estado["notifications"][-2:]] == ["player_stunned"] * 2
    assert estado["players"]["red"]["stun_remaining"] == pytest.approx(1)
    # Aislar el vencimiento del temporizador de un segundo contacto nuevo.
    juego._guardianes[0].x, juego._guardianes[0].y = 500, 500
    liberado = juego.avanzar(1)["players"]["red"]
    assert liberado["status"] == "normal"
    assert liberado["frozen"] is False
    assert juego.avanzar(0.1)["players"]["red"]["x"] > 100


def test_contacto_suma_tiempo_a_una_trampa_sin_repetirse_cada_tick():
    juego = partida_iniciada(
        obstaculos=(),
        trampas=(Trampa("t", "jaula", Obstaculo(100, 100, 64, 64), 2.5),),
        guardianes=(Guardian("g", 100, 100),),
    )
    impacto = juego.avanzar(0)["players"]["red"]
    assert impacto["status"] == "stunned"
    assert impacto["trap"] == "jaula"
    assert impacto["stun_remaining"] == pytest.approx(4.5)
    assert juego.avanzar(0.1)["players"]["red"]["stun_remaining"] == pytest.approx(4.4)
    assert juego.avanzar(4.4)["players"]["red"]["status"] == "normal"


def test_impacto_interrumpe_extraccion_sin_dar_puntos():
    juego = partida_iniciada(obstaculos=(), guardianes=(Guardian("g", 740, 430),))
    juego._jugadores["red"].x, juego._jugadores["red"].y = 740, 430
    juego.actualizar_entradas({"red": {"x": 0, "y": 0, "interact": 1},
                              "blue": {"x": 0, "y": 0}})
    assert juego.estado()["reactor"]["operator"] == "red"
    impacto = juego.avanzar(0)
    assert impacto["reactor"]["operator"] is None
    assert juego.avanzar(1)["players"]["red"]["score"] == 0


def test_estado_no_se_puede_modificar_desde_un_input_y_ambos_lo_ven():
    juego = EstadoJuego(obstaculos=(), guardianes=(Guardian("g", 100, 100),))
    rojo, azul = SesionCliente(), SesionCliente()
    for sesion, nombre in ((rojo, "ana"), (azul, "beto")):
        procesar_mensaje(json.dumps({"type": "join", "token": nombre}), juego, sesion=sesion)
    procesar_mensaje('{"type":"start"}', juego, sesion=rojo)
    juego.avanzar(0)
    respuesta = json.loads(procesar_mensaje(json.dumps({
        "type": "input", "x": 1, "y": 0, "status": "normal", "frozen": False
    }), juego, sesion=rojo))
    observador = json.loads(procesar_mensaje('{"type":"state"}', juego, sesion=azul))
    assert respuesta["players"]["red"] == observador["players"]["red"]
    assert observador["players"]["red"]["status"] == "stunned"


def test_guardian_respeta_barrera_y_limites():
    pared = Obstaculo(160, 0, 40, 900)
    juego = partida_iniciada(obstaculos=(pared,), guardianes=(Guardian("g", 100, 300),))
    juego._jugadores["red"].bloqueo_restante = 20
    estado = juego.avanzar(5)
    guardian = estado["guardians"][0]
    assert guardian["x"] <= 120
    assert 0 <= guardian["y"] <= juego.ALTO - guardian["size"]


def test_duracion_y_velocidad_son_reglas_configurables():
    reglas = validar_reglas({"puntos_por_energia": 1, "intervalo_extraccion": 0.5,
                            "duracion_aturdimiento": 3, "velocidad_guardian": 60})
    assert reglas == Reglas(1, 0.5, 3, 60)
    juego = partida_iniciada(obstaculos=(), guardianes=(Guardian("g", 100, 100),), reglas=reglas)
    assert juego.avanzar(0)["players"]["red"]["stun_remaining"] == 3
    for clave in ("duracion_aturdimiento", "velocidad_guardian"):
        with pytest.raises(ValueError):
            validar_reglas({"puntos_por_energia": 1, "intervalo_extraccion": 0.5, clave: 0})