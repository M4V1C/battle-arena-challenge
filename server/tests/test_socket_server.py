import socket
import threading

from app.socket_server import crear_socket_servidor, procesar_mensaje, servir


def test_procesar_mensaje_valido():
    assert procesar_mensaje("prueba") == "OK prueba"


def test_procesar_mensaje_botones():
    for i in range(1, 5):
        assert procesar_mensaje(f"boton {i}") == f"OK boton {i}"


def test_procesar_mensaje_invalido():
    assert procesar_mensaje("otra cosa") == "ERROR mensaje invalido"


def test_intercambio_por_socket():
    srv = crear_socket_servidor("127.0.0.1", 0)
    port = srv.getsockname()[1]
    threading.Thread(target=servir, args=(srv,), daemon=True).start()

    with socket.create_connection(("127.0.0.1", port), timeout=5) as conn:
        conn.sendall(b"prueba\n")
        with conn.makefile("r", encoding="utf-8") as lector:
            assert lector.readline().strip() == "OK prueba"
    srv.close()
