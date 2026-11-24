"""Dos sesiones de jugador para la ventana local de la partida."""

import json
import queue
import socket
import threading
from typing import Any


class ConexionPartidaLocal:
    def __init__(self, host: str, port: int, nombres: dict[str, str], escenario: str):
        self._host, self._port = host, port
        self._nombres = dict(nombres)
        self._escenario = escenario
        self._entradas: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)
        self._estados: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)
        self._cerrando = threading.Event()
        self._sockets: list[socket.socket] = []
        self._hilo = threading.Thread(target=self._procesar, daemon=True)
        self._hilo.start()

    def enviar_entradas(self, entradas: dict[str, dict[str, int]]) -> None:
        try:
            self._entradas.put_nowait(entradas)
        except queue.Full:
            try:
                self._entradas.get_nowait()
            except queue.Empty:
                pass
            self._entradas.put_nowait(entradas)

    def obtener_estado(self) -> dict[str, Any] | None:
        estado = None
        while True:
            try:
                estado = self._estados.get_nowait()
            except queue.Empty:
                return estado

    def cerrar(self) -> None:
        self._cerrando.set()
        for conexion in tuple(self._sockets):
            try:
                conexion.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        self._hilo.join(timeout=1)
        for conexion in tuple(self._sockets):
            conexion.close()

    def _publicar(self, estado: dict[str, Any]) -> None:
        try:
            self._estados.put_nowait(estado)
        except queue.Full:
            try:
                self._estados.get_nowait()
            except queue.Empty:
                pass
            self._estados.put_nowait(estado)

    @staticmethod
    def _solicitar(conexion: socket.socket, lector, mensaje: dict[str, Any]) -> dict[str, Any]:
        conexion.sendall((json.dumps(mensaje, separators=(",", ":")) + "\n").encode("utf-8"))
        linea = lector.readline()
        if not linea:
            raise ConnectionError("El servidor cerró la conexión.")
        respuesta = json.loads(linea)
        if not isinstance(respuesta, dict):
            raise ValueError("El servidor devolvió una respuesta inválida.")
        return respuesta

    def _procesar(self) -> None:
        lectores = []
        try:
            ultimo_aviso = 0
            for puesto in ("red", "blue"):
                if self._cerrando.is_set():
                    return
                conexion = socket.create_connection((self._host, self._port), timeout=5)
                conexion.settimeout(None)
                self._sockets.append(conexion)
                lector = conexion.makefile("r", encoding="utf-8", newline="\n")
                lectores.append(lector)
                respuesta = self._solicitar(conexion, lector,
                                            {"type": "join", "token": self._nombres[puesto]})
                if respuesta.get("type") != "joined" or respuesta.get("slot") != puesto:
                    raise ValueError(respuesta.get("message", "No se pudo unir el jugador."))
                if puesto == "red":
                    ultimo_aviso = respuesta.get("last_notification_id", 0)
            if self._cerrando.is_set():
                return
            inicio = self._solicitar(self._sockets[0], lectores[0],
                                     {"type": "start", "scenario": self._escenario})
            rechazos = [n for n in inicio.get("notifications", [])
                        if n["id"] > ultimo_aviso and n["kind"] == "reject"
                        and n["for"] == "red"]
            if rechazos:
                raise ValueError(rechazos[-1]["message"])
            if inicio.get("type") != "state" or not inicio.get("match", {}).get("started"):
                raise ValueError(inicio.get("message", "No se pudo iniciar la partida."))
            if inicio.get("scenario", {}).get("id") != self._escenario:
                raise ValueError("El servidor inició un escenario distinto al seleccionado.")
            self._publicar(inicio)
            while not self._cerrando.is_set():
                try:
                    entradas = self._entradas.get(timeout=0.1)
                except queue.Empty:
                    continue
                estado = None
                for indice, puesto in enumerate(("red", "blue")):
                    mensaje = {"type": "input", **entradas[puesto]}
                    estado = self._solicitar(self._sockets[indice], lectores[indice], mensaje)
                    if estado.get("type") != "state":
                        raise ValueError(estado.get("message", "Error al enviar controles."))
                self._publicar(estado)
        except (OSError, ValueError, KeyError, ConnectionError) as error:
            if not self._cerrando.is_set():
                self._publicar({"type": "error", "message": str(error)})
        finally:
            for lector in lectores:
                try:
                    lector.close()
                except OSError:
                    pass
            for conexion in tuple(self._sockets):
                conexion.close()
