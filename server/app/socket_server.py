"""Servidor TCP concurrente para procesar entradas y consultar el juego."""

import json
import os
import socket
import threading
import time

from app.game_state import EstadoJuego

HOST = os.getenv("SOCKET_HOST", "0.0.0.0")
PORT = int(os.getenv("SOCKET_PORT", "9000"))
MAX_LINEA = 1024
FRECUENCIA_SIMULACION = 60
DELTA_MAXIMO = 0.1

# Procesa una solicitud JSON y devuelve estado o error en formato JSON.
def procesar_mensaje(texto: str, estado_juego: EstadoJuego) -> str:
    try:
        mensaje = json.loads(texto)
        if not isinstance(mensaje, dict):
            raise ValueError("El mensaje debe ser un objeto JSON.")

        tipo = mensaje.get("type")
        if tipo == "state":
            respuesta = estado_juego.estado()
        elif tipo == "input":
            respuesta = estado_juego.actualizar_entradas(mensaje.get("inputs"))
        else:
            raise ValueError("Tipo de mensaje desconocido.")
    except (json.JSONDecodeError, ValueError) as error:
        respuesta = {"type": "error", "message": str(error)}
    return json.dumps(respuesta, separators=(",", ":"))

# Procesa solicitudes de un cliente hasta que cierre su conexión
def manejar_cliente(
    conn: socket.socket,
    addr: tuple[str, int],
    estado_juego: EstadoJuego,
) -> None:
    try:
        with conn, conn.makefile("r", encoding="utf-8", newline="\n") as lector:
            for linea in iter(lambda: lector.readline(MAX_LINEA), ""):
                respuesta = procesar_mensaje(linea.strip(), estado_juego)
                conn.sendall((respuesta + "\n").encode("utf-8"))
    finally:
        # Evita que una entrada anterior mantenga movimiento tras desconectarse.
        estado_juego.detener_movimiento()


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
    detener_simulacion = threading.Event()

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
            args=(conn, addr, estado_juego),
            daemon=True,
        ).start()


if __name__ == "__main__":
    servidor = crear_socket_servidor()
    print(f"Servidor de juego escuchando en {HOST}:{PORT}", flush=True)
    servir(servidor)
