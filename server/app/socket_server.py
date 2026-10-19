import os
import socket
import threading

HOST = os.getenv("SOCKET_HOST", "0.0.0.0")
PORT = int(os.getenv("SOCKET_PORT", "9000"))
MENSAJES_VALIDOS = {"prueba", "boton 1", "boton 2", "boton 3", "boton 4"}
MAX_LINEA = 1024


def procesar_mensaje(texto: str) -> str:
    if texto in MENSAJES_VALIDOS:
        return f"OK {texto}"
    return "ERROR mensaje invalido"


def manejar_cliente(conn: socket.socket, addr) -> None:
    with conn, conn.makefile("r", encoding="utf-8", newline="\n") as lector:
        # Mensajes delimitados por salto de linea; limita el tamano leido.
        for linea in iter(lambda: lector.readline(MAX_LINEA), ""):
            respuesta = procesar_mensaje(linea.strip())
            print(f"[{addr[0]}:{addr[1]}] recibido={linea.strip()!r} respuesta={respuesta!r}", flush=True)
            conn.sendall((respuesta + "\n").encode("utf-8"))


def crear_socket_servidor(host: str = HOST, port: int = PORT) -> socket.socket:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # En Windows SO_REUSEADDR permite que dos procesos compartan el puerto.
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    else:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen()
    return srv


def servir(srv: socket.socket) -> None:
    while True:
        try:
            conn, addr = srv.accept()
        except OSError:
            return  # socket del servidor cerrado
        threading.Thread(target=manejar_cliente, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    servidor = crear_socket_servidor()
    print(f"Servidor de sockets escuchando en {HOST}:{PORT}", flush=True)
    servir(servidor)
