"""Contratos entre el motor US-21/22/25 y la API de develop."""

import json

from app.auth_store import AlmacenCuentas
from app.game_state import EstadoJuego, Rechazo
from app.resultados_store import AlmacenResultados
from app.socket_server import SesionCliente, guardar_resultado_final, procesar_mensaje


def test_resultado_del_motor_persiste_una_vez_y_alimenta_ranking(tmp_path):
    almacen = AlmacenResultados(tmp_path / "resultados.json")
    llamadas = []

    def guardar(resultado):
        llamadas.append(resultado["id"])
        return guardar_resultado_final(almacen, resultado)

    juego = EstadoJuego(guardianes=(), eventos=False, guardar_resultado=guardar)
    juego.unir_jugador("ana")
    juego.unir_jugador("beto")
    juego.iniciar_partida({"condition": "points", "value": 1})
    juego._jugadores["red"].puntos = 1
    final = juego.avanzar(0)
    juego.avanzar(5)

    assert final["match"]["game_over"]["match_id"] == final["match"]["match_id"]
    assert final["match"]["result_saved"] is True
    assert llamadas == [final["match"]["match_id"]]
    assert len(almacen.listar()) == 1
    assert almacen.ranking()[0]["usuario"] == "ana"
    assert almacen.historial("beto")[0]["resultado"] == "derrota"


def test_prorroga_conserva_match_id_y_guarda_solo_al_final(tmp_path):
    almacen = AlmacenResultados(tmp_path / "resultados.json")
    juego = EstadoJuego(
        guardianes=(), eventos=False,
        guardar_resultado=lambda resultado: guardar_resultado_final(almacen, resultado),
    )
    juego.unir_jugador("ana")
    juego.unir_jugador("beto")
    inicial = juego.iniciar_partida({"condition": "time", "value": 1})
    empate = juego.avanzar(60)

    assert empate["match"]["overtime"] == 1
    assert empate["match"]["match_id"] == inicial["match"]["match_id"]
    assert almacen.listar() == []

    juego._jugadores["blue"].puntos = 2
    final = juego.avanzar(120)
    assert final["match"]["finished"] is True
    assert final["match"]["match_id"] == inicial["match"]["match_id"]
    assert len(almacen.listar()) == 1


def test_escenario_cargado_no_cambia_durante_partida():
    juego = EstadoJuego()
    juego.iniciar_partida({"condition": "time", "value": 1}, "laberinto")
    assert juego.estado()["scenario"]["id"] == "laberinto"
    try:
        juego._seleccionar_escenario("arena_clasica")
    except Rechazo as error:
        assert error.codigo == "match_in_progress"
    else:
        raise AssertionError("El escenario cambió durante la partida.")
    assert juego.estado()["scenario"]["id"] == "laberinto"


def test_dos_sesiones_autenticadas_comparten_resultado_y_ranking(tmp_path):
    cuentas = AlmacenCuentas(tmp_path / "usuarios.json", tmp_path / "sesiones.json")
    sesiones = []
    for usuario in ("ana", "beto"):
        registro = cuentas.registrar(usuario, f"{usuario}@example.com", "Clave123")
        cuentas.verificar(usuario, registro["codigo_verificacion"])
        sesiones.append(cuentas.login(usuario, "Clave123")["token"])
    almacen = AlmacenResultados(tmp_path / "resultados.json")
    juego = EstadoJuego(
        guardar_resultado=lambda resultado: guardar_resultado_final(almacen, resultado),
        semilla=3,
    )
    rojo, azul = SesionCliente(), SesionCliente()
    for sesion, token in zip((rojo, azul), sesiones):
        respuesta = json.loads(procesar_mensaje(
            json.dumps({"type": "join", "token": token}), juego,
            sesion=sesion, validar_sesion=cuentas.validar_sesion,
        ))
        assert respuesta["type"] == "joined"
    inicio = json.loads(procesar_mensaje(
        '{"type":"start","scenario":"laberinto"}', juego, sesion=rojo,
        validar_sesion=cuentas.validar_sesion,
    ))
    assert inicio["scenario"]["id"] == "laberinto"
    assert inicio["match"]["game_over"] is None
    juego._jugadores["red"].puntos = 20
    juego.avanzar(0)
    vistas = [json.loads(procesar_mensaje('{"type":"state"}', juego, sesion=s))
              for s in (rojo, azul)]
    assert vistas[0]["match"]["game_over"] == vistas[1]["match"]["game_over"]
    assert vistas[0]["match"]["game_over"]["winner"] == "red"
    assert almacen.ranking()[0]["usuario"] == "ana"


def test_resultados_anteriores_se_leen_sin_perder_historial(tmp_path):
    ruta = tmp_path / "resultados.json"
    ruta.write_text(json.dumps([{
        "id": "partida-antigua", "winner": "red", "elapsed": 15,
        "overtime": 0, "condition": "points", "value": 20,
        "players": {"red": {"username": "ana", "score": 20},
                    "blue": {"username": "beto", "score": 5}},
    }]), encoding="utf-8")
    almacen = AlmacenResultados(ruta)
    assert almacen.historial("ana")[0]["match_id"] == "partida-antigua"
    almacen.guardar_resultado("partida-nueva", {
        "red": {"usuario": "ana", "score": 1},
    }, "red", 8)
    almacen_reabierto = AlmacenResultados(ruta)
    assert len(almacen_reabierto.listar()) == 2
