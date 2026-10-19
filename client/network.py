# Maneja la comunicación asíncrona entre el cliente y el servidor de juego.

import json
import queue
import socket
import threading
from typing import Any

# Clase que encapsula la conexión con el servidor y la gestión de entradas y estados.
class ConexionServidor:

    # Inicializa la conexión y los hilos de red.
    def __init__(self, host: str, port: int, timeout: float = 5.0):
        self._socket = socket.create_connection((host, port), timeout=timeout)
        self._socket.settimeout(None)
        self._lector = self._socket.makefile("r", encoding="utf-8", newline="\n")

        # Las entradas representan el estado más reciente del teclado; no se
        # necesita acumular entradas viejas si la red se retrasa.
        self._entradas: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)
        self._estados: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)
        self._cerrando = threading.Event()
        self._hilo = threading.Thread(target=self._procesar_red, daemon=True)
        self._hilo.start()
        self._encolar({"type": "state"})

    # Programa el último estado de controles de ambos jugadores.
    def enviar_entradas(self, entradas: dict[str, dict[str, int]]) -> None:
        self._encolar({"type": "input", "inputs": entradas})

    # Devuelve el estado más reciente recibido, si hay uno disponible.
    def obtener_estado(self) -> dict[str, Any] | None:
        estado = None
        while True:
            try:
                estado = self._estados.get_nowait()
            except queue.Empty:
                return estado

    # Detiene el trabajador y cierra el socket de forma ordenada.
    def cerrar(self) -> None:
        self._cerrando.set()
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self._hilo.join(timeout=1.0)
        self._lector.close()
        self._socket.close()

    # Reemplaza entradas pendientes para conservar solo la más reciente.
    def _encolar(self, mensaje: dict[str, Any]) -> None:
        try:
            self._entradas.put_nowait(mensaje)
        except queue.Full:
            try:
                self._entradas.get_nowait()
            except queue.Empty:
                pass
            self._entradas.put_nowait(mensaje)

    # Publica una respuesta sin retener snapshots que ya quedaron viejos.
    def _publicar_estado(self, estado: dict[str, Any]) -> None:
        try:
            self._estados.put_nowait(estado)
        except queue.Full:
            try:
                self._estados.get_nowait()
            except queue.Empty:
                pass
            self._estados.put_nowait(estado)

    # Bucle de red que envía entradas y recibe estados sin bloquear el hilo principal.
    def _procesar_red(self) -> None:
        # Procesa solicitudes y respuestas sin bloquear el ciclo gráfico.
        while not self._cerrando.is_set():
            try:
                mensaje = self._entradas.get(timeout=0.1)
            except queue.Empty:
                continue

            # Envía la entrada al servidor y espera la respuesta.
            try:
                datos = json.dumps(mensaje, separators=(",", ":")) + "\n"
                self._socket.sendall(datos.encode("utf-8"))
                linea = self._lector.readline()
                if not linea:
                    raise ConnectionError("El servidor cerró la conexión.")
                respuesta = json.loads(linea)
                if not isinstance(respuesta, dict):
                    raise ValueError("El servidor devolvió una respuesta inválida.")
                self._publicar_estado(respuesta)
            except (OSError, ValueError) as error:
                if not self._cerrando.is_set():
                    self._publicar_estado({"type": "error", "message": str(error)})
                return
