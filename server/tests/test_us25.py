"""Cierre único, prórroga y persistencia del resultado."""

import json
from concurrent.futures import ThreadPoolExecutor

from app.game_state import EstadoJuego
from app.resultados_store import AlmacenResultados
from app.socket_server import SesionCliente, procesar_mensaje
from app.socket_server import guardar_resultado_final


def juego_con_guardado(guardados):
    juego = EstadoJuego(obstaculos=(), guardianes=(), eventos=False,
                       guardar_resultado=lambda resultado: guardados.append(resultado) or True)
    juego.unir_jugador("ana")
    juego.unir_jugador("beto")
    return juego


def test_meta_de_puntos_emite_game_over_y_guarda_una_vez():
    guardados = []
    juego = juego_con_guardado(guardados)
    juego.iniciar_partida({"condition": "points", "value": 2})
    juego._jugadores["red"].x, juego._jugadores["red"].y = 740, 430
    juego.actualizar_entradas({"red": {"x": 0, "y": 0, "interact": 1},
                               "blue": {"x": 0, "y": 0}})
    final = juego.avanzar(1)
    assert final["match"]["finished"]
    assert final["match"]["event"] == "game_over"
    assert final["match"]["result_saved"]
    assert final["players"]["red"]["score"] == 2
    assert final["match"]["result"]["players"]["red"]["position"] == 1
    assert final["match"]["result"]["players"]["blue"]["position"] == 2
    assert len([n for n in final["notifications"] if n["kind"] == "game_over"]) == 1
    assert len(guardados) == 1
    juego.avanzar(10)
    juego.actualizar_entradas({"red": {"x": 1, "y": 0, "interact": 2, "shoot": 1},
                               "blue": {"x": 0, "y": 0}})
    assert juego.estado()["match"]["result"] == final["match"]["result"]
    assert juego.estado()["players"]["red"]["score"] == 2
    assert len(guardados) == 1


def test_tiempo_finaliza_exactamente_en_limite():
    guardados = []
    juego = juego_con_guardado(guardados)
    juego.iniciar_partida({"condition": "time", "value": 1})
    juego._jugadores["blue"].puntos = 3
    assert not juego.avanzar(59.9)["match"]["finished"]
    final = juego.avanzar(1)
    assert final["match"]["finished"]
    assert final["match"]["elapsed"] == 60
    assert final["match"]["winner"] == "blue"
    assert guardados[0]["players"]["blue"]["score"] == 3


def test_empate_conserva_puntos_y_suma_dos_minutos_antes_de_guardar():
    guardados = []
    juego = juego_con_guardado(guardados)
    juego.iniciar_partida({"condition": "time", "value": 1})
    juego._jugadores["red"].puntos = juego._jugadores["blue"].puntos = 4
    prorroga = juego.avanzar(60)
    assert not prorroga["match"]["finished"]
    assert prorroga["match"]["time_limit"] == 180
    assert (prorroga["players"]["red"]["score"], prorroga["players"]["blue"]["score"]) == (4, 4)
    assert guardados == []
    juego._jugadores["red"].puntos = 5
    final = juego.avanzar(120)
    assert final["match"]["winner"] == "red"
    assert final["match"]["overtime"] == 1
    assert len(guardados) == 1


def test_resultado_persiste_tras_salir_ambos_clientes(tmp_path):
    ruta = tmp_path / "resultados.json"
    almacen = AlmacenResultados(ruta)
    juego = EstadoJuego(obstaculos=(), guardianes=(), eventos=False,
                       guardar_resultado=lambda datos: guardar_resultado_final(almacen, datos))
    juego.unir_jugador("ana")
    juego.unir_jugador("beto")
    juego.iniciar_partida({"condition": "points", "value": 1})
    juego._jugadores["red"].puntos = 1
    final = juego.avanzar(0)
    juego.liberar_puesto("red")
    juego.liberar_puesto("blue")
    with ruta.open(encoding="utf-8") as archivo:
        persistidos = json.load(archivo)
    assert len(persistidos["partidas"]) == 1
    assert persistidos["partidas"][0]["match_id"] == final["match"]["match_id"]
    assert AlmacenResultados(ruta).historial("ana")[0]["resultado"] == "victoria"


def test_evento_de_energia_puede_cerrar_partida_y_no_reaparece():
    guardados = []
    juego = EstadoJuego(obstaculos=(), guardianes=(), eventos=True, semilla=1,
                       guardar_resultado=lambda r: guardados.append(r) or True)
    juego.iniciar_partida({"condition": "points", "value": 3})
    inicio = next(e["start"] for e in juego.estado()["events"] if e["type"] == "energy")
    item = juego.avanzar(inicio)["energy_items"][0]
    juego._jugadores["red"].x, juego._jugadores["red"].y = item["x"], item["y"]
    final = juego.avanzar(0)
    assert final["match"]["finished"]
    assert final["players"]["red"]["score"] == 3
    assert final["energy_items"] == []
    assert not any(e["status"] == "active" for e in final["events"])
    assert juego.avanzar(10) == final
    assert len(guardados) == 1


def test_ambos_clientes_ven_mismo_resultado_final():
    juego = EstadoJuego(obstaculos=(), guardianes=(), eventos=False)
    rojo, azul = SesionCliente(), SesionCliente()
    for sesion, usuario in ((rojo, "ana"), (azul, "beto")):
        procesar_mensaje(json.dumps({"type": "join", "token": usuario}), juego, sesion=sesion)
    procesar_mensaje('{"type":"start"}', juego, sesion=rojo)
    juego._jugadores["red"].puntos = 20
    juego.avanzar(0)
    vistas = [json.loads(procesar_mensaje('{"type":"state"}', juego, sesion=s))
              for s in (rojo, azul)]
    assert vistas[0]["match"] == vistas[1]["match"]
    assert vistas[0]["match"]["result"]["winner"] == "red"
    assert [n for n in vistas[0]["notifications"] if n["kind"] == "game_over"] == [
        n for n in vistas[1]["notifications"] if n["kind"] == "game_over"
    ]


def test_tics_simultaneos_no_guardan_ni_emiten_dos_veces():
    guardados = []
    juego = juego_con_guardado(guardados)
    juego.iniciar_partida({"condition": "points", "value": 1})
    juego._jugadores["red"].puntos = 1
    with ThreadPoolExecutor(max_workers=8) as executor:
        estados = list(executor.map(juego.avanzar, [0] * 16))
    assert all(e["match"]["finished"] for e in estados)
    assert len(guardados) == 1
    assert len([n for n in juego.estado()["notifications"] if n["kind"] == "game_over"]) == 1


def test_el_servidor_actualiza_ambos_historiales_con_el_resultado_final(tmp_path):
    almacen = AlmacenResultados(tmp_path / "resultados.json")
    assert guardar_resultado_final(almacen, {
        "id": "partida-1", "winner": "red", "elapsed": 12.8,
        "overtime": 0, "condition": "points", "value": 10,
        "players": {"red": {"username": "ana", "score": 7},
                    "blue": {"username": "beto", "score": 4}},
    })
    assert almacen.historial("ana")[0]["resultado"] == "victoria"
    assert almacen.historial("beto")[0]["resultado"] == "derrota"
