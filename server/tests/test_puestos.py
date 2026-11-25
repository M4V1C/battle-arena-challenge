"""Puestos por usuario, entradas del propio puesto, inicio con start y reject."""

import json
import socket
import threading
import time

import pytest

from app.avatar_store import AlmacenAvatares
from app.game_state import MAX_NOTIFICACIONES, EstadoJuego, Rechazo
from app.socket_server import (
    SesionCliente,
    crear_socket_servidor,
    procesar_mensaje,
    servir,
)

CONFIG = {"condition": "points", "value": 20}


def enviar(juego, sesion, avatares=None, **mensaje) -> dict:
    """Envía un mensaje por el protocolo y devuelve la respuesta ya decodificada."""
    texto = json.dumps(mensaje)
    return json.loads(procesar_mensaje(texto, juego, avatares=avatares, sesion=sesion))


def ultimo_rechazo(estado: dict) -> dict:
    rechazos = [n for n in estado["notifications"] if n["kind"] == "reject"]
    assert rechazos, "El estado no trae ningún rechazo."
    return rechazos[-1]


@pytest.fixture
def sala():
    """Sala con ana (red, anfitrión) y beto (blue) conectados, sin iniciar."""
    juego = EstadoJuego(obstaculos=())
    rojo, azul = SesionCliente(), SesionCliente()
    assert enviar(juego, rojo, type="join", token="ana")["type"] == "joined"
    assert enviar(juego, azul, type="join", token="beto")["type"] == "joined"
    return juego, rojo, azul


@pytest.fixture
def partida(sala):
    juego, rojo, azul = sala
    assert enviar(juego, rojo, type="start")["match"]["started"] is True
    return juego, rojo, azul


# ---------- Puestos (motor) ----------


def test_primer_usuario_es_red_y_segundo_blue():
    juego = EstadoJuego()

    assert juego.unir_jugador("ana") == "red"
    assert juego.unir_jugador("beto") == "blue"


def test_tercer_usuario_es_rechazado_con_sala_llena():
    juego = EstadoJuego()
    juego.unir_jugador("ana")
    juego.unir_jugador("beto")

    with pytest.raises(Rechazo) as error:
        juego.unir_jugador("carla")

    assert error.value.codigo == "room_full"


def test_misma_cuenta_conectada_dos_veces_es_rechazada():
    juego = EstadoJuego()
    juego.unir_jugador("ana")

    with pytest.raises(Rechazo) as error:
        juego.unir_jugador("ana")

    assert error.value.codigo == "already_connected"


@pytest.mark.parametrize("usuario", [None, "", "   ", 5])
def test_usuario_invalido_es_rechazado(usuario):
    with pytest.raises(Rechazo) as error:
        EstadoJuego().unir_jugador(usuario)

    assert error.value.codigo == "invalid_user"


def test_state_expone_usuario_y_conexion_de_cada_puesto():
    juego = EstadoJuego()
    juego.unir_jugador("ana")

    jugadores = juego.estado()["players"]

    assert (jugadores["red"]["username"], jugadores["red"]["connected"]) == ("ana", True)
    assert (jugadores["blue"]["username"], jugadores["blue"]["connected"]) == (None, False)


def test_salir_antes_de_empezar_libera_el_puesto():
    juego = EstadoJuego()
    juego.unir_jugador("ana")
    juego.unir_jugador("beto")

    juego.liberar_puesto("red")

    assert juego.estado()["players"]["red"]["username"] is None
    assert juego.unir_jugador("carla") == "red"


def test_salir_en_plena_partida_reserva_el_puesto_para_el_mismo_usuario():
    juego = EstadoJuego()
    juego.unir_jugador("ana")
    juego.unir_jugador("beto")
    juego.iniciar_por("red", CONFIG)

    juego.liberar_puesto("blue")

    assert juego.estado()["players"]["blue"]["username"] == "beto"
    assert juego.estado()["players"]["blue"]["connected"] is False
    with pytest.raises(Rechazo) as error:
        juego.unir_jugador("carla")
    assert error.value.codigo == "room_full"
    assert juego.unir_jugador("beto") == "blue"
    assert juego.estado()["players"]["blue"]["connected"] is True


def test_sala_se_vacia_cuando_nadie_sigue_conectado():
    juego = EstadoJuego()
    juego.unir_jugador("ana")
    juego.unir_jugador("beto")
    juego.iniciar_por("red", CONFIG)
    juego.avanzar(1)

    juego.liberar_puesto("red")
    juego.liberar_puesto("blue")

    estado = juego.estado()
    assert estado["match"]["started"] is False
    assert estado["match"]["elapsed"] == 0
    assert [j["username"] for j in estado["players"].values()] == [None, None]
    assert juego.unir_jugador("carla") == "red"


def test_liberar_puesto_ajeno_o_repetido_no_hace_nada():
    juego = EstadoJuego()
    juego.unir_jugador("ana")

    juego.liberar_puesto("blue")
    juego.liberar_puesto("inexistente")
    juego.liberar_puesto("red")
    juego.liberar_puesto("red")

    assert juego.estado()["players"]["red"]["username"] is None


# ---------- Inicio solo con start ----------


def test_una_entrada_no_inicia_la_partida(sala):
    juego, rojo, _ = sala

    estado = enviar(juego, rojo, type="input", x=1, y=0, interact=0, shoot=0)
    despues = juego.avanzar(1)

    assert estado["match"]["started"] is False
    assert despues["match"]["started"] is False
    assert despues["match"]["elapsed"] == 0
    assert despues["players"]["red"]["x"] == 100


def test_start_inicia_la_partida(sala):
    juego, rojo, _ = sala

    estado = enviar(juego, rojo, type="start")

    assert estado["type"] == "state"
    assert estado["match"]["started"] is True
    assert juego.avanzar(0.5)["match"]["elapsed"] == pytest.approx(0.5)


def test_solo_el_anfitrion_puede_iniciar(sala):
    juego, _, azul = sala

    estado = enviar(juego, azul, type="start")

    assert estado["match"]["started"] is False
    rechazo = ultimo_rechazo(estado)
    assert (rechazo["code"], rechazo["for"]) == ("not_host", "blue")
    assert rechazo["message"]


def test_no_se_inicia_sin_el_segundo_jugador():
    juego = EstadoJuego()
    rojo = SesionCliente()
    enviar(juego, rojo, type="join", token="ana")

    estado = enviar(juego, rojo, type="start")

    assert estado["match"]["started"] is False
    assert ultimo_rechazo(estado)["code"] == "waiting_for_players"


def test_start_con_la_partida_en_curso_es_rechazado(partida):
    juego, rojo, _ = partida
    juego.avanzar(1)

    estado = enviar(juego, rojo, type="start")

    assert ultimo_rechazo(estado)["code"] == "match_in_progress"
    assert estado["match"]["elapsed"] == pytest.approx(1)


def test_start_despues_de_terminar_permite_la_revancha(partida):
    juego, rojo, _ = partida
    juego._jugadores["red"].puntos = 20
    assert juego.avanzar(0.1)["match"]["finished"] is True

    estado = enviar(juego, rojo, type="start")

    assert estado["match"]["finished"] is False
    assert estado["match"]["started"] is True
    assert estado["players"]["red"]["score"] == 0


def test_start_sin_join_es_rechazado():
    juego = EstadoJuego()

    respuesta = enviar(juego, SesionCliente(), type="start")

    assert respuesta == {
        "type": "reject",
        "code": "not_joined",
        "message": respuesta["message"],
    }
    assert juego.estado()["match"]["started"] is False


# ---------- Entradas solo del propio puesto ----------


def test_cada_cliente_mueve_solo_su_puesto(partida):
    juego, rojo, azul = partida

    enviar(juego, rojo, type="input", x=0, y=1, interact=0, shoot=0)
    estado = juego.avanzar(0.5)

    assert estado["players"]["red"]["y"] > 100
    assert (estado["players"]["blue"]["x"], estado["players"]["blue"]["y"]) == (1460, 760)

    enviar(juego, azul, type="input", x=0, y=-1, interact=0, shoot=0)
    estado = juego.avanzar(0.5)

    assert estado["players"]["blue"]["y"] < 760


def test_no_se_puede_enviar_la_entrada_de_otro_puesto(partida):
    juego, _, azul = partida

    estado = enviar(juego, azul, type="input", player="red", x=1, y=0, interact=0, shoot=0)
    despues = juego.avanzar(1)

    rechazo = ultimo_rechazo(estado)
    assert (rechazo["code"], rechazo["for"]) == ("wrong_slot", "blue")
    assert despues["players"]["red"]["x"] == 100
    assert despues["players"]["blue"]["x"] == 1460


def test_formato_antiguo_con_inputs_es_rechazado(partida):
    juego, rojo, _ = partida

    estado = enviar(
        juego, rojo, type="input",
        inputs={"red": {"x": 1, "y": 0}, "blue": {"x": -1, "y": 0}},
    )

    assert ultimo_rechazo(estado)["code"] == "invalid_input"
    assert juego.avanzar(1)["players"]["blue"]["x"] == 1460


@pytest.mark.parametrize(
    "campos",
    [
        {"x": 2, "y": 0},
        {"x": True, "y": 0},
        {"x": "1", "y": 0},
        {"y": 0},
        {"x": 0, "y": 0, "shoot": -1},
        {"x": 0, "y": 0, "interact": 1.5},
    ],
)
def test_entrada_invalida_es_rechazada_con_motivo_y_no_cambia_el_estado(partida, campos):
    juego, rojo, _ = partida

    estado = enviar(juego, rojo, type="input", **campos)

    rechazo = ultimo_rechazo(estado)
    assert (rechazo["code"], rechazo["for"]) == ("invalid_input", "red")
    assert rechazo["message"]
    assert juego.avanzar(1)["players"]["red"]["x"] == 100


def test_input_sin_join_es_rechazado(partida):
    juego, _, _ = partida

    respuesta = enviar(juego, SesionCliente(), type="input", x=1, y=0)

    assert respuesta["type"] == "reject"
    assert respuesta["code"] == "not_joined"
    assert juego.avanzar(1)["players"]["red"]["x"] == 100


def test_pulsacion_previa_al_inicio_no_se_ejecuta_al_empezar(sala):
    juego, rojo, _ = sala
    enviar(juego, rojo, type="input", x=0, y=0, interact=0, shoot=1)
    enviar(juego, rojo, type="start")

    estado = enviar(juego, rojo, type="input", x=0, y=0, interact=0, shoot=1)

    assert estado["projectiles"] == []
    estado = enviar(juego, rojo, type="input", x=0, y=0, interact=0, shoot=2)
    assert len(estado["projectiles"]) == 1


def test_contador_repetido_o_menor_no_se_cuenta_dos_veces(partida):
    juego, rojo, _ = partida

    enviar(juego, rojo, type="input", x=0, y=0, interact=0, shoot=2)
    enviar(juego, rojo, type="input", x=0, y=0, interact=0, shoot=1)
    estado = enviar(juego, rojo, type="input", x=0, y=0, interact=0, shoot=2)

    assert len(estado["projectiles"]) == 1


def test_reiniciar_la_partida_conserva_los_contadores_del_cliente(partida):
    juego, rojo, _ = partida
    enviar(juego, rojo, type="input", x=0, y=0, interact=0, shoot=1)
    juego.iniciar_partida(CONFIG)

    estado = enviar(juego, rojo, type="input", x=0, y=0, interact=0, shoot=1)

    assert estado["projectiles"] == []


def test_cliente_nuevo_en_el_puesto_empieza_sus_contadores_desde_cero(partida):
    juego, rojo, _ = partida
    previos = len(
        enviar(juego, rojo, type="input", x=0, y=0, interact=0, shoot=5)["projectiles"]
    )
    juego.liberar_puesto("red")
    nuevo = SesionCliente()
    assert enviar(juego, nuevo, type="join", token="ana")["slot"] == "red"

    # El cliente nuevo cuenta desde cero: su primera pulsación sí debe disparar.
    estado = enviar(juego, nuevo, type="input", x=0, y=0, interact=0, shoot=1)

    assert len(estado["projectiles"]) == previos + 1


def test_al_desconectarse_el_jugador_se_detiene(partida):
    juego, rojo, _ = partida
    enviar(juego, rojo, type="input", x=0, y=1, interact=0, shoot=0)
    juego.avanzar(0.2)
    juego.liberar_puesto("red")
    antes = juego.estado()["players"]["red"]

    despues = juego.avanzar(1)["players"]["red"]

    assert (despues["x"], despues["y"]) == (antes["x"], antes["y"])


# ---------- join y reject por el protocolo ----------


def test_join_responde_joined_con_puesto_y_usuario():
    juego = EstadoJuego()

    primero = enviar(juego, SesionCliente(), type="join", token="ana")
    segundo = enviar(juego, SesionCliente(), type="join", token="beto")

    assert primero["type"] == "joined"
    assert (primero["slot"], primero["username"]) == ("red", "ana")
    assert (segundo["slot"], segundo["username"]) == ("blue", "beto")
    assert primero["last_notification_id"] == 0


@pytest.mark.parametrize("mensaje", [{}, {"token": ""}, {"token": None}, {"token": 7}])
def test_join_con_token_invalido_es_rechazado_sin_asignar_puesto(mensaje):
    juego = EstadoJuego()

    respuesta = enviar(juego, SesionCliente(), type="join", **mensaje)

    assert respuesta["type"] == "reject"
    assert respuesta["code"] == "invalid_token"
    assert respuesta["message"]
    assert juego.estado()["players"]["red"]["username"] is None


def test_join_usa_la_funcion_validar_sesion_recibida():
    juego = EstadoJuego()

    def validar(token):
        return {"abc123": "ana"}.get(token)

    texto = json.dumps({"type": "join", "token": "abc123"})
    aceptado = json.loads(procesar_mensaje(texto, juego, validar_sesion=validar))
    texto = json.dumps({"type": "join", "token": "falso"})
    rechazado = json.loads(procesar_mensaje(texto, juego, validar_sesion=validar))

    assert (aceptado["type"], aceptado["username"]) == ("joined", "ana")
    assert rechazado["code"] == "invalid_token"


def test_join_con_sala_llena_responde_reject(sala):
    juego, _, _ = sala

    respuesta = enviar(juego, SesionCliente(), type="join", token="carla")

    assert respuesta["type"] == "reject"
    assert respuesta["code"] == "room_full"


def test_join_repetido_en_la_misma_conexion_es_rechazado(sala):
    juego, rojo, _ = sala

    respuesta = enviar(juego, rojo, type="join", token="otra")

    assert respuesta["code"] == "already_joined"
    assert juego.estado()["players"]["red"]["username"] == "ana"


def test_state_trae_el_avatar_de_cada_puesto(sala):
    juego, rojo, _ = sala
    avatares = AlmacenAvatares()
    avatares.seleccionar("blue", "avatar_4")

    estado = enviar(juego, rojo, avatares=avatares, type="state")

    assert estado["players"]["red"]["avatar"] == "avatar_1"
    assert estado["players"]["blue"]["avatar"] == "avatar_4"


def test_notificaciones_tienen_id_creciente_y_la_lista_esta_acotada(partida):
    juego, rojo, _ = partida
    ids = []
    for _ in range(MAX_NOTIFICACIONES + 5):
        estado = enviar(juego, rojo, type="input", x=9, y=0)
        ids.append(estado["notifications"][-1]["id"])

    assert ids == sorted(set(ids))
    assert len(estado["notifications"]) == MAX_NOTIFICACIONES
    assert estado["notifications"][0]["id"] == ids[-1] - MAX_NOTIFICACIONES + 1
    assert set(estado["notifications"][-1]) == {
        "id", "kind", "code", "message", "severity", "for",
    }
    assert estado["notifications"][-1]["severity"] == "warning"


def test_join_informa_el_ultimo_id_para_no_repetir_avisos_viejos(partida):
    juego, rojo, _ = partida
    enviar(juego, rojo, type="input", x=9, y=0)
    juego.liberar_puesto("blue")

    respuesta = enviar(juego, SesionCliente(), type="join", token="beto")

    assert respuesta["last_notification_id"] == 1


# ---------- Dos conexiones TCP reales ----------


class ClienteTCP:
    def __init__(self, puerto: int):
        self.conn = socket.create_connection(("127.0.0.1", puerto), timeout=5)
        self.lector = self.conn.makefile("r", encoding="utf-8", newline="\n")

    def enviar(self, **mensaje) -> dict:
        self.conn.sendall((json.dumps(mensaje) + "\n").encode("utf-8"))
        return json.loads(self.lector.readline())

    def cerrar(self) -> None:
        self.lector.close()
        self.conn.close()


@pytest.fixture
def puerto():
    servidor = crear_socket_servidor("127.0.0.1", 0)
    threading.Thread(target=servir, args=(servidor,), daemon=True).start()
    try:
        yield servidor.getsockname()[1]
    finally:
        servidor.close()


def esperar(condicion, segundos: float = 3.0) -> bool:
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        if condicion():
            return True
        time.sleep(0.02)
    return False


def test_dos_computadoras_juegan_en_puestos_distintos(puerto):
    ana, beto, carla = ClienteTCP(puerto), ClienteTCP(puerto), ClienteTCP(puerto)
    try:
        assert ana.enviar(type="join", token="ana")["slot"] == "red"
        assert beto.enviar(type="join", token="beto")["slot"] == "blue"
        assert carla.enviar(type="join", token="carla")["code"] == "room_full"

        assert beto.enviar(type="start")["match"]["started"] is False
        assert ana.enviar(type="start")["match"]["started"] is True

        ana.enviar(type="input", x=1, y=0, interact=0, shoot=0)
        beto.enviar(type="input", x=-1, y=0, interact=0, shoot=0)
        assert esperar(
            lambda: ana.enviar(type="state")["players"]["red"]["x"] > 100
        )
        estado = beto.enviar(type="state")
        assert estado["players"]["red"]["username"] == "ana"
        assert estado["players"]["blue"]["username"] == "beto"
        assert estado["players"]["blue"]["x"] < 1460
    finally:
        for cliente in (ana, beto, carla):
            cliente.cerrar()


def test_cerrar_la_conexion_libera_el_puesto(puerto):
    ana, beto = ClienteTCP(puerto), ClienteTCP(puerto)
    try:
        ana.enviar(type="join", token="ana")
        beto.enviar(type="join", token="beto")

        ana.cerrar()

        assert esperar(
            lambda: beto.enviar(type="state")["players"]["red"]["username"] is None
        )
        nueva = ClienteTCP(puerto)
        try:
            assert nueva.enviar(type="join", token="carla")["slot"] == "red"
        finally:
            nueva.cerrar()
    finally:
        beto.cerrar()


def test_conexion_sin_join_no_ocupa_ni_libera_puestos(puerto):
    ana = ClienteTCP(puerto)
    try:
        ana.enviar(type="join", token="ana")
        espectador = ClienteTCP(puerto)
        espectador.enviar(type="state")
        espectador.cerrar()
        time.sleep(0.2)

        jugadores = ana.enviar(type="state")["players"]

        assert (jugadores["red"]["username"], jugadores["red"]["connected"]) == ("ana", True)
    finally:
        ana.cerrar()
