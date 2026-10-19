"""Punto de entrada del cliente local de Battle Arena."""

import os
import sys

from game import Juego

HOST = os.getenv("SERVER_HOST", "127.0.0.1")
PORT = int(os.getenv("SERVER_PORT", "9000"))

# Función principal del cliente local de Battle Arena
def main() -> int:
    """Conecta el cliente al servidor y ejecuta el juego."""
    host = sys.argv[1] if len(sys.argv) > 1 else HOST
    try:
        juego = Juego(host, PORT)
        juego.ejecutar()
    except OSError as error:
        print(f"No se pudo conectar a {host}:{PORT}: {error}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
