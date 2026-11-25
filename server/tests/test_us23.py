"""Selección y sincronización de escenarios con el esquema JSON de develop."""

import json
from pathlib import Path

import pytest

from app.escenarios import DIRECTORIO_ESCENARIOS, cargar_escenario, validar_escenario
from app.game_config import AlmacenConfiguracion
from app.game_state import EstadoJuego
from app.socket_server import SesionCliente, procesar_mensaje


def sala():
    juego = EstadoJuego(semilla=3)
    rojo, azul = SesionCliente(), SesionCliente()
    for sesion, usuario in ((rojo, "ana"), (azul, "beto")):
        respuesta = json.loads(procesar_mensaje(
            json.dumps({"type": "join", "token": usuario}), juego, sesion=sesion))
        assert respuesta["type"] == "joined"
    return juego, rojo, azul


def enviar(juego, sesion, **mensaje):
    return json.loads(procesar_mensaje(json.dumps(mensaje), juego, sesion=sesion))


def test_json_definen_dos_arenas_visibles_y_funcionalmente_distintas():
    clasica = cargar_escenario("arena_clasica")
    laberinto = cargar_escenario("laberinto")
    assert clasica.obstaculos != laberinto.obstaculos
    assert clasica.puertas != laberinto.puertas
    assert clasica.tema != laberinto.tema
    for mapa in (clasica, laberinto):
        assert mapa.zonas_transitables
        assert len(mapa.guardianes) >= 4
        assert len(mapa.trampas) == 3
        for x, y in mapa.posiciones.values():
            assert 0 <= x <= mapa.ancho - 40
            assert 0 <= y <= mapa.alto - 40


@pytest.mark.parametrize("posicion", [(1600, 100), (300, 200), (780, 430)])
def test_rechaza_apariciones_fuera_o_sobre_solidos(posicion):
    datos = json.loads((DIRECTORIO_ESCENARIOS / "laberinto.json").read_text(encoding="utf-8"))
    datos["posiciones_iniciales"]["red"] = {"x": posicion[0], "y": posicion[1]}
    with pytest.raises(ValueError):
        validar_escenario(datos)


def test_rechaza_id_desconocido_y_ruta_insegura():
    with pytest.raises(ValueError):
        cargar_escenario("inexistente")
    with pytest.raises(ValueError):
        cargar_escenario("../reglas")


def test_ambos_jugadores_ven_mismo_escenario():
    juego, rojo, azul = sala()
    inicio = enviar(juego, rojo, type="start", scenario="laberinto")
    vista_azul = enviar(juego, azul, type="state")
    for clave in ("scenario", "obstacles", "doors", "traps", "guardians", "events"):
        assert inicio[clave] == vista_azul[clave]
    assert inicio["scenario"]["id"] == "laberinto"
    assert (inicio["players"]["red"]["x"], inicio["players"]["red"]["y"]) == (100, 100)
    assert (inicio["reactor"]["x"], inicio["reactor"]["y"]) == (780, 430)


def test_laberinto_bloquea_pared_y_puerta_abierta_deja_pasar():
    juego, rojo, _ = sala()
    enviar(juego, rojo, type="start", scenario="laberinto")
    juego._jugadores["red"].x, juego._jugadores["red"].y = 260, 200
    enviar(juego, rojo, type="input", x=1, y=0)
    assert juego.avanzar(0.2)["players"]["red"]["x"] == 260
    juego._jugadores["red"].x, juego._jugadores["red"].y = 740, 300
    abierto = enviar(juego, rojo, type="input", x=1, y=0, interact=1)
    assert next(p for p in abierto["doors"] if p["id"] == "puerta_laberinto_1")["open"]
    assert juego.avanzar(0.3)["players"]["red"]["x"] > 780


def test_extraccion_y_eventos_funcionan_en_laberinto():
    juego, rojo, _ = sala()
    estado = enviar(juego, rojo, type="start", scenario="laberinto")
    assert len([e for e in estado["events"] if e["type"] == "energy"]) == 3
    juego._jugadores["red"].x, juego._jugadores["red"].y = 740, 430
    enviar(juego, rojo, type="input", x=0, y=0, interact=1)
    assert juego.avanzar(0.5)["players"]["red"]["score"] == 1


def test_no_cambia_escenario_durante_partida_y_si_en_revancha():
    juego, rojo, _ = sala()
    enviar(juego, rojo, type="start", scenario="laberinto")
    anterior = juego.estado()
    rechazo = enviar(juego, rojo, type="start", scenario="arena_clasica")
    assert rechazo["scenario"]["id"] == "laberinto"
    assert rechazo["players"] == anterior["players"]
    assert rechazo["notifications"][-1]["code"] == "match_in_progress"
    juego._jugadores["red"].puntos = 20
    assert juego.avanzar(0)["match"]["finished"]
    revancha = enviar(juego, rojo, type="start", scenario="arena_clasica")
    assert revancha["scenario"]["id"] == "arena_clasica"


def test_escenario_invalido_no_inicia_ni_modifica_mapa():
    juego, rojo, _ = sala()
    respuesta = enviar(juego, rojo, type="start", scenario="desconocido")
    assert respuesta["notifications"][-1]["code"] == "invalid_scenario"
    assert juego.estado()["match"]["started"] is False
    assert juego.estado()["scenario"]["id"] == "arena_clasica"


def test_inicio_conserva_configuracion_de_tiempo(tmp_path):
    juego, rojo, _ = sala()
    almacen = AlmacenConfiguracion(tmp_path / "config.json")
    almacen.guardar({"condition": "time", "value": 2})
    inicio = json.loads(procesar_mensaje('{"type":"start","scenario":"laberinto"}',
                                         juego, configuracion=almacen, sesion=rojo))
    assert inicio["match"]["condition"] == "time"
    assert inicio["match"]["time_limit"] == 120
    assert inicio["scenario"]["id"] == "laberinto"
