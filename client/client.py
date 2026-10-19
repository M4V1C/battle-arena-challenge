import os
import socket
import sys

HOST = os.getenv("SERVER_HOST", "127.0.0.1")
PORT = int(os.getenv("SERVER_PORT", "9000"))
MENSAJE = "prueba"


def enviar(mensaje: str, host: str = HOST, port: int = PORT, timeout: float = 5.0) -> str:
    with socket.create_connection((host, port), timeout=timeout) as conn:
        conn.sendall((mensaje + "\n").encode("utf-8"))
        with conn.makefile("r", encoding="utf-8", newline="\n") as lector:
            return lector.readline().strip()


def main() -> int:
    host = sys.argv[1] if len(sys.argv) > 1 else HOST
    respuesta = enviar(MENSAJE, host=host)
    print(f"Enviado: {MENSAJE!r} -> Respuesta: {respuesta!r}")
    if respuesta == f"OK {MENSAJE}":
        print("Confirmacion recibida correctamente.")
        return 0
    print("El servidor no confirmo el mensaje.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
