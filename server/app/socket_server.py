"""Servidor TCP concurrente para procesar entradas y consultar el juego."""

import json
import os
import socket
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from app.game_state import EstadoJuego, Rechazo
from app.game_config import CONFIGURACION_INICIAL, AlmacenConfiguracion
from app.avatar_store import AlmacenAvatares
from app.resultados_store import AlmacenResultados

HOST = os.getenv("SOCKET_HOST", "0.0.0.0")
PORT = int(os.getenv("SOCKET_PORT", "9000"))
MAX_LINEA =  7 * 1024 * 1024 + 1
FRECUENCIA_SIMULACION = 60
DELTA_MAXIMO = 0.1
# Mensajes que modifican datos compartidos: exigen una conexión con join.
MENSAJES_CON_JOIN = ("save_config", "select_avatar", "upload_avatar")


# Datos propios de una conexión TCP: el puesto que ocupa tras hacer join.
@dataclass
class SesionCliente:
    puesto: str | None = None


# Sustituto de validar_sesion(token) mientras no exista la real (Persona 3).
# Trata el token como el nombre de usuario y devuelve None si no es válido.
# Con la real: servir(servidor, validar_sesion=auth.validar_sesion).
def validar_sesion_falsa(token: Any) -> str | None:
    if isinstance(token, str) and 0 < len(token.strip()) <= 64:
        return token.strip()
    return None


# Rechazo sin puesto al que dirigirlo (join fallido o mensaje antes del join).
def _rechazo(codigo: str, motivo: str) -> dict[str, Any]:
    return {"type": "reject", "code": codigo, "message": motivo}


# Atiende join: valida el token, asigna el puesto y lo guarda en la conexión.
def _unirse(
    mensaje: dict[str, Any],
    estado_juego: EstadoJuego,
    sesion: SesionCliente,
    validar_sesion: Callable[[Any], str | None],
) -> dict[str, Any]:
    if sesion.puesto is not None:
        return _rechazo("already_joined", "Esta conexión ya tiene un puesto asignado.")
    usuario = validar_sesion(mensaje.get("token"))
    if not usuario:
        return _rechazo("invalid_token", "La sesión no es válida. Inicia sesión de nuevo.")
    try:
        puesto = estado_juego.unir_jugador(usuario)
    except Rechazo as rechazo:
        return _rechazo(rechazo.codigo, rechazo.motivo)
    sesion.puesto = puesto
    return {
        "type": "joined",
        "slot": puesto,
        "username": usuario,
        "last_notification_id": estado_juego.ultima_notificacion(),
    }


# Atiende input y start. El puesto sale de la conexión, nunca del mensaje.
# Un rechazo con puesto viaja en state.notifications; sin puesto, como reject.
def _solicitud_de_puesto(
    tipo: str,
    mensaje: dict[str, Any],
    estado_juego: EstadoJuego,
    configuracion: AlmacenConfiguracion | None,
    sesion: SesionCliente,
) -> dict[str, Any]:
    puesto = sesion.puesto
    if puesto is None:
        return _rechazo("not_joined", "Primero debes unirte a la partida con join.")
    try:
        if tipo == "start":
            escenario = mensaje.get("scenario")
            ajustes = configuracion.obtener() if configuracion else CONFIGURACION_INICIAL
            return estado_juego.iniciar_por(puesto, ajustes, escenario)
        if mensaje.get("player", mensaje.get("slot", puesto)) != puesto:
            raise Rechazo(
                "wrong_slot", "Solo puedes enviar las entradas de tu propio puesto."
            )
        if "inputs" in mensaje:
            raise Rechazo(
                "invalid_input",
                "Formato obsoleto: envía x, y, interact y shoot solo de tu puesto.",
            )
        return estado_juego.aplicar_entrada(puesto, mensaje)
    except Rechazo as rechazo:
        return estado_juego.rechazar(puesto, rechazo.codigo, rechazo.motivo)
    except ValueError as error:
        if tipo == "input":
            return estado_juego.rechazar(puesto, "invalid_input", str(error))
        raise


# Agrega a cada jugador del state el avatar que eligió.
def _con_avatares(
    estado: dict[str, Any], avatares: AlmacenAvatares | None
) -> dict[str, Any]:
    if avatares is not None and estado.get("type") == "state":
        selecciones = avatares.obtener()["players"]
        for puesto, jugador in estado["players"].items():
            jugador["avatar"] = selecciones.get(puesto)
    return estado


# Procesa una solicitud JSON y devuelve estado o error en formato JSON.
def procesar_mensaje(
    texto: str,
    estado_juego: EstadoJuego,
    configuracion: AlmacenConfiguracion | None = None,
    avatares: AlmacenAvatares | None = None,
    sesion: SesionCliente | None = None,
    validar_sesion: Callable[[Any], str | None] = validar_sesion_falsa,
) -> str:
    sesion = sesion if sesion is not None else SesionCliente()
    try:
        mensaje = json.loads(texto)
        if not isinstance(mensaje, dict):
            raise ValueError("El mensaje debe ser un objeto JSON.")

        tipo = mensaje.get("type")
        if tipo == "join":
            respuesta = _unirse(mensaje, estado_juego, sesion, validar_sesion)
        elif tipo == "state":
            respuesta = estado_juego.estado()
        elif tipo in ("input", "start"):
            respuesta = _solicitud_de_puesto(
                tipo, mensaje, estado_juego, configuracion, sesion
            )
        elif tipo in MENSAJES_CON_JOIN and sesion.puesto is None:
            respuesta = _rechazo(
                "not_joined",
                "Debes unirte a la sala con join antes de cambiar la configuración o el avatar.",
            )
        elif tipo == "get_avatars":
            if avatares is None:
                raise ValueError("El almacén de avatares no está disponible.")

            respuesta = avatares.obtener()

        elif tipo == "select_avatar":
            if avatares is None:
                raise ValueError("El almacén de avatares no está disponible.")

            respuesta = avatares.seleccionar(
                mensaje.get("player"),
                mensaje.get("avatar"),
            )

        elif tipo == "upload_avatar":
            if avatares is None:
                raise ValueError("El almacén de avatares no está disponible.")

            respuesta = avatares.importar(
                mensaje.get("player"),
                mensaje.get("image"),
            )

        elif tipo == "get_avatar_image":
            if avatares is None:
                raise ValueError("El almacén de avatares no está disponible.")

            respuesta = avatares.obtener_imagen(
                mensaje.get("avatar"),
            )

        elif tipo in ("get_config", "save_config"):
            if configuracion is None:
                raise ValueError("El almacen de configuracion no esta disponible.")
            ajustes = (
                configuracion.guardar(mensaje.get("config"))
                if tipo == "save_config" else configuracion.obtener()
            )
            respuesta = {"type": "config", "config": ajustes}
        else:
            raise ValueError("Tipo de mensaje desconocido.")
    except (ValueError, OSError) as error:
        respuesta = {"type": "error", "message": str(error)}
    return json.dumps(_con_avatares(respuesta, avatares), separators=(",", ":"))

# Procesa solicitudes de un cliente hasta que cierre su conexión
def manejar_cliente(
    conn: socket.socket,
    addr: tuple[str, int],
    estado_juego: EstadoJuego,
    configuracion: AlmacenConfiguracion | None = None,
    avatares: AlmacenAvatares | None = None,
    validar_sesion: Callable[[Any], str | None] = validar_sesion_falsa,
) -> None:
    sesion = SesionCliente()
    try:
        with conn, conn.makefile("r", encoding="utf-8", newline="\n") as lector:
            for linea in iter(lambda: lector.readline(MAX_LINEA), ""):

                if not linea.endswith("\n"):
                    respuesta = json.dumps({
                        "type": "error",
                        "message": "Mensaje demasiado grande o incompleto.",
                    })

                    conn.sendall((respuesta + "\n").encode("utf-8"))
                    break

                respuesta = procesar_mensaje(
                    linea.strip(),
                    estado_juego,
                    configuracion,
                    avatares,
                    sesion,
                    validar_sesion,
                )
                conn.sendall((respuesta + "\n").encode("utf-8"))
    finally:
        # Solo quien hizo join ocupa un puesto; las conexiones de configuración
        # o avatares no tocan la partida al cerrarse.
        if sesion.puesto is not None:
            estado_juego.liberar_puesto(sesion.puesto)


def crear_socket_servidor(host: str = HOST, port: int = PORT) -> socket.socket:
    """Crea y deja escuchando un socket TCP en la dirección indicada."""
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # SO_EXCLUSIVEADDRUSE evita compartir el puerto accidentalmente en Windows.
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    else:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((host, port))
    servidor.listen()
    return servidor


def guardar_resultado_final(resultados: AlmacenResultados, resultado: dict[str, Any]) -> bool:
    """Adapta el resultado autoritativo al formato usado por perfil y ranking."""
    jugadores = {
        puesto: {
            "usuario": datos["username"],
            "score": datos["score"],
        }
        for puesto, datos in resultado["players"].items()
    }
    respuesta = resultados.guardar_resultado(
        resultado["id"], jugadores, resultado["winner"],
        resultado["elapsed"], resultado["overtime"],
        resultado["condition"], resultado["value"],
    )
    return bool(respuesta["ok"])


def servir(
    servidor: socket.socket,
    validar_sesion: Callable[[Any], str | None] = validar_sesion_falsa,
    resultados: AlmacenResultados | None = None,
    estado_juego: EstadoJuego | None = None,
) -> None:
    """Acepta conexiones y crea un hilo por cliente sobre el mismo estado."""
    resultados = resultados if resultados is not None else AlmacenResultados()

    if estado_juego is None:
        estado_juego = EstadoJuego(
            guardar_resultado=lambda resultado: guardar_resultado_final(resultados, resultado)
        )
    configuracion = AlmacenConfiguracion()
    detener_simulacion = threading.Event()
    avatares = AlmacenAvatares()

    def simular() -> None:
        """Avanza el mundo a 60 Hz usando tiempo real transcurrido."""
        ultimo_tick = time.monotonic()
        intervalo = 1 / FRECUENCIA_SIMULACION
        while not detener_simulacion.is_set():
            ahora = time.monotonic()
            # Limita la corrección de pausa; no teletransporta jugadores al reanudar.
            delta_t = min(ahora - ultimo_tick, DELTA_MAXIMO)
            estado_juego.avanzar(delta_t)
            ultimo_tick = ahora
            detener_simulacion.wait(intervalo)

    hilo_simulacion = threading.Thread(target=simular, daemon=True)
    hilo_simulacion.start()
    while True:
        try:
            conn, addr = servidor.accept()
        except OSError:
            detener_simulacion.set()
            hilo_simulacion.join(timeout=1.0)
            return
        threading.Thread(
            target=manejar_cliente,
            args=(conn, addr, estado_juego, configuracion, avatares, validar_sesion),
            daemon=True,
        ).start()


if __name__ == "__main__":
    servidor = crear_socket_servidor()
    print(f"Servidor de juego escuchando en {HOST}:{PORT}", flush=True)
    servir(servidor)
