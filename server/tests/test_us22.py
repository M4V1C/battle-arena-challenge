"""Pruebas de los eventos autoritativos de US-22."""

import json

import pytest

from app.game_state import EstadoJuego
from app.guardianes import Guardian
from app.socket_server import SesionCliente, procesar_mensaje


def partida(guardianes=()):
    juego = EstadoJuego(obstaculos=(), guardianes=guardianes, eventos=True, semilla=7)
    juego.iniciar_partida({"condition": "time", "value": 1})
    return juego


def entrada(interact=0, x=0):
    return {"red": {"x": x, "y": 0, "interact": interact},
            "blue": {"x": 0, "y": 0}}


def evento(estado, tipo):
    return next(e for e in estado["events"] if e["type"] == tipo)


def test_calendario_tiene_todas_las_activaciones_y_ids_unicos():
    estado = partida().estado()
    eventos = estado["events"]
    assert len({e["id"] for e in eventos}) == len(eventos)
    assert [e["type"] for e in eventos].count("energy") == 3
    assert [e["type"] for e in eventos].count("overload") >= 2
    assert [e["type"] for e in eventos].count("extra_guardians") == 1
    assert [e["type"] for e in eventos].count("speed_boost") == 1
    assert [e["type"] for e in eventos].count("guardian_truce") == 1
    energias = [e for e in eventos if e["type"] == "energy"]
    assert all(a["start"] < b["start"] for a, b in zip(energias, energias[1:]))


def test_energia_aparece_y_solo_el_primer_jugador_cobra():
    juego = partida()
    aparicion = evento(juego.estado(), "energy")["start"]
    estado = juego.avanzar(aparicion)
    item = estado["energy_items"][0]
    assert item["points"] == 3
    juego._jugadores["red"].x, juego._jugadores["red"].y = item["x"], item["y"]
    cobro = juego.avanzar(0)
    assert cobro["players"]["red"]["score"] == 3
    assert cobro["energy_items"] == []
    juego._jugadores["blue"].x, juego._jugadores["blue"].y = item["x"], item["y"]
    assert juego.avanzar(0)["players"]["blue"]["score"] == 0
    assert len([n for n in juego.estado()["notifications"] if n["kind"] == "energy_claimed"]) == 1


def test_energia_se_recoge_al_cruzar_el_icono_en_movimiento():
    juego = partida()
    aparicion = evento(juego.estado(), "energy")["start"]
    item = juego.avanzar(aparicion)["energy_items"][0]
    juego._jugadores["red"].x = item["x"] - juego.TAMANO_JUGADOR - 1
    juego._jugadores["red"].y = item["y"]
    juego.actualizar_entradas(entrada(x=1))
    estado = juego.avanzar(0.05)
    assert estado["players"]["red"]["score"] == item["points"]
    assert estado["energy_items"] == []


def test_guardianes_extra_aparecen_y_desaparecen():
    juego = partida()
    extra = evento(juego.estado(), "extra_guardians")
    activos = juego.avanzar(extra["start"])
    assert len(activos["guardians"]) == 5
    assert all(g["temporary"] for g in activos["guardians"])
    assert all(0 <= g["x"] <= juego.ANCHO - g["size"] for g in activos["guardians"])
    final = juego.avanzar(extra["duration"])
    assert final["guardians"] == []
    assert evento(final, "extra_guardians")["status"] == "ended"


def test_sobrecarga_corta_y_rechaza_extraccion_luego_se_restaura():
    juego = partida()
    sobrecarga = evento(juego.estado(), "overload")
    juego._jugadores["red"].x, juego._jugadores["red"].y = 740, 430
    juego.actualizar_entradas(entrada(interact=1))
    assert juego.estado()["reactor"]["operator"] == "red"
    activo = juego.avanzar(sobrecarga["start"])
    puntos = activo["players"]["red"]["score"]
    assert activo["reactor"]["status"] == "overload"
    assert activo["reactor"]["operator"] is None
    juego.actualizar_entradas(entrada(interact=2))
    assert juego.estado()["notifications"][-1]["code"] == "reactor_overload"
    assert juego.avanzar(sobrecarga["duration"])["players"]["red"]["score"] == puntos
    juego.actualizar_entradas(entrada(interact=3))
    assert juego.avanzar(0.5)["players"]["red"]["score"] == puntos + 1


def test_impulso_aumenta_velocidad_y_luego_la_restaura():
    juego = partida()
    impulso = evento(juego.estado(), "speed_boost")
    juego.avanzar(impulso["start"])
    juego._jugadores["red"].bloqueo_restante = 0
    juego._jugadores["red"].aturdimiento_restante = 0
    juego._jugadores["red"].x, juego._jugadores["red"].y = 100, 100
    juego.actualizar_entradas(entrada(x=1))
    x0 = juego.estado()["players"]["red"]["x"]
    x1 = juego.avanzar(0.1)["players"]["red"]["x"]
    assert x1 - x0 == pytest.approx(36)
    juego.actualizar_entradas(entrada())
    juego.avanzar(impulso["duration"])
    juego.actualizar_entradas(entrada(x=1))
    x2 = juego.estado()["players"]["red"]["x"]
    assert juego.avanzar(0.1)["players"]["red"]["x"] - x2 == pytest.approx(24)


def test_tregua_detiene_guardianes_solo_durante_evento():
    juego = partida((Guardian("g", 500, 500),))
    tregua = evento(juego.estado(), "guardian_truce")
    juego.avanzar(tregua["start"])
    juego._guardianes[0].x, juego._guardianes[0].y = 500, 500
    parado = juego.avanzar(0.5)["guardians"][0]
    assert (parado["x"], parado["y"]) == (500, 500)
    juego.avanzar(tregua["duration"])
    juego._guardianes[0].x, juego._guardianes[0].y = 500, 500
    moviendo = juego.avanzar(0.5)["guardians"][0]
    assert (moviendo["x"], moviendo["y"]) != (500, 500)


def test_no_quedan_eventos_activos_tras_finalizar_y_no_se_reactivan():
    juego = partida()
    juego._jugadores["red"].puntos = 1
    final = juego.avanzar(60)
    assert final["match"]["finished"]
    assert all(e["status"] != "active" for e in final["events"])
    assert final["energy_items"] == []
    assert all(not g["temporary"] for g in final["guardians"])
    assert juego.avanzar(10) == final


def test_eventos_se_activan_y_terminan_una_sola_vez():
    juego = partida()
    juego._jugadores["red"].puntos = 1
    calendario = juego.estado()["events"]
    avisos = []
    ultimo = 0
    for _ in range(240):
        estado = juego.avanzar(0.25)
        nuevos = [n for n in estado["notifications"] if n["id"] > ultimo]
        avisos.extend(nuevos)
        ultimo = max([ultimo] + [n["id"] for n in nuevos])
    for e in calendario:
        assert sum(n.get("code") == e["id"] and n["kind"] == "event_start"
                   for n in avisos) == 1
        assert sum(n.get("code") == e["id"] and n["kind"] == "event_end"
                   for n in avisos) == 1
    assert all(e["status"] == "ended" for e in estado["events"])


def test_dos_clientes_reciben_el_mismo_evento_y_sus_efectos():
    juego = EstadoJuego(obstaculos=(), guardianes=(), eventos=True, semilla=9)
    rojo, azul = SesionCliente(), SesionCliente()
    for sesion, nombre in ((rojo, "ana"), (azul, "beto")):
        procesar_mensaje(json.dumps({"type": "join", "token": nombre}), juego, sesion=sesion)
    procesar_mensaje('{"type":"start"}', juego, sesion=rojo)
    juego.avanzar(evento(juego.estado(), "energy")["start"])
    vista_roja = json.loads(procesar_mensaje('{"type":"state"}', juego, sesion=rojo))
    vista_azul = json.loads(procesar_mensaje('{"type":"state"}', juego, sesion=azul))
    assert vista_roja["events"] == vista_azul["events"]
    assert vista_roja["energy_items"] == vista_azul["energy_items"]
