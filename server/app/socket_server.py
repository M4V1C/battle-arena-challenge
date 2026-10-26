"""Servidor TCP concurrente para procesar entradas y consultar el juego."""

import json
import os
import socket
import threading
import time

from app.game_state import EstadoJuego
from app.game_config import AlmacenConfiguracion
from app.avatar_store import AlmacenAvatares

HOST = os.getenv("SOCKET_HOST", "0.0.0.0")
PORT = int(os.getenv("SOCKET_PORT", "9000"))
MAX_LINEA =  7 * 1024 * 1024 + 1
FRECUENCIA_SIMULACION = 60
DELTA_MAXIMO = 0.1

# Procesa una solicitud JSON y devuelve estado o error en formato JSON.
def procesar_mensaje(
    texto: str,
    estado_juego: EstadoJuego,
    configuracion: AlmacenConfiguracion | None = None,
    avatares: AlmacenAvatares | None = None,
) -> str:
    try:
        mensaje = json.loads(texto)
        if not isinstance(mensaje, dict):
            raise ValueError("El mensaje debe ser un objeto JSON.")

        tipo = mensaje.get("type")
        if tipo == "state":
            respuesta = estado_juego.estado()
        elif tipo == "input":
            respuesta = estado_juego.actualizar_entradas(mensaje.get("inputs"))
        elif tipo == "start":
            from app.game_config import CONFIGURACION_INICIAL

            ajustes = configuracion.obtener() if configuracion else CONFIGURACION_INICIAL
            respuesta = estado_juego.iniciar_partida(ajustes)

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
    return json.dumps(respuesta, separators=(",", ":"))

# Procesa solicitudes de un cliente hasta que cierre su conexión
def manejar_cliente(
    conn: socket.socket,
    addr: tuple[str, int],
    estado_juego: EstadoJuego,
    configuracion: AlmacenConfiguracion | None = None,
    avatares: AlmacenAvatares | None = None,
) -> None:
    es_partida = False
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
                )
                try:
                    solicitud = json.loads(linea)
                    if isinstance(solicitud, dict) and solicitud.get("type") in ("start", "input"):
                        es_partida = True
                except ValueError:
                    pass
                conn.sendall((respuesta + "\n").encode("utf-8"))
    finally:
        if es_partida:
            estado_juego.reiniciar_partida()


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


def servir(servidor: socket.socket) -> None:
    """Acepta conexiones y crea un hilo por cliente sobre el mismo estado."""
    estado_juego = EstadoJuego()
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
            args=(conn, addr, estado_juego, configuracion, avatares),
            daemon=True,
        ).start()


if __name__ == "__main__":
    servidor = crear_socket_servidor()
    print(f"Servidor de juego escuchando en {HOST}:{PORT}", flush=True)
    servir(servidor)
