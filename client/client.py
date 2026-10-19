import os
import socket
import sys

import pygame

HOST = os.getenv("SERVER_HOST", "127.0.0.1")
PORT = int(os.getenv("SERVER_PORT", "9000"))

ANCHO, ALTO = 800, 600
BOTON_ANCHO, BOTON_ALTO, SEPARACION = 200, 80, 20
FONDO = (30, 30, 40)
COLOR_BOTON = (70, 110, 180)
COLOR_BOTON_HOVER = (100, 140, 210)
COLOR_TEXTO = (240, 240, 240)
COLOR_OK = (120, 220, 120)
COLOR_ERROR = (230, 100, 100)


class Conexion:
    def __init__(self, host: str, port: int, timeout: float = 5.0):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.lector = self.sock.makefile("r", encoding="utf-8", newline="\n")

    def enviar(self, mensaje: str) -> str:
        self.sock.sendall((mensaje + "\n").encode("utf-8"))
        return self.lector.readline().strip()

    def cerrar(self) -> None:
        self.lector.close()
        self.sock.close()


def crear_botones() -> list[tuple[pygame.Rect, str]]:
    # Rejilla 2x2 centrada en la ventana.
    total_ancho = 2 * BOTON_ANCHO + SEPARACION
    total_alto = 2 * BOTON_ALTO + SEPARACION
    x0 = (ANCHO - total_ancho) // 2
    y0 = (ALTO - total_alto) // 2
    botones = []
    for i in range(4):
        fila, col = divmod(i, 2)
        rect = pygame.Rect(
            x0 + col * (BOTON_ANCHO + SEPARACION),
            y0 + fila * (BOTON_ALTO + SEPARACION),
            BOTON_ANCHO,
            BOTON_ALTO,
        )
        botones.append((rect, f"boton {i + 1}"))
    return botones


def main() -> int:
    host = sys.argv[1] if len(sys.argv) > 1 else HOST
    try:
        conexion = Conexion(host, PORT)
    except OSError as e:
        print(f"No se pudo conectar a {host}:{PORT}: {e}")
        return 1

    pygame.init()
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    pygame.display.set_caption("Battle Arena - Cliente")
    fuente = pygame.font.SysFont(None, 36)
    reloj = pygame.time.Clock()
    botones = crear_botones()
    estado, color_estado = f"Conectado a {host}:{PORT}", COLOR_TEXTO

    corriendo = True
    while corriendo:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                corriendo = False
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                for rect, mensaje in botones:
                    if rect.collidepoint(evento.pos):
                        try:
                            respuesta = conexion.enviar(mensaje)
                        except OSError as e:
                            respuesta = f"ERROR conexion: {e}"
                        ok = respuesta == f"OK {mensaje}"
                        estado = f"{mensaje} -> {respuesta}"
                        color_estado = COLOR_OK if ok else COLOR_ERROR
                        print(estado)

        pantalla.fill(FONDO)
        raton = pygame.mouse.get_pos()
        for rect, mensaje in botones:
            color = COLOR_BOTON_HOVER if rect.collidepoint(raton) else COLOR_BOTON
            pygame.draw.rect(pantalla, color, rect, border_radius=10)
            texto = fuente.render(mensaje.capitalize(), True, COLOR_TEXTO)
            pantalla.blit(texto, texto.get_rect(center=rect.center))

        texto_estado = fuente.render(estado, True, color_estado)
        pantalla.blit(texto_estado, texto_estado.get_rect(center=(ANCHO // 2, ALTO - 60)))

        pygame.display.flip()
        reloj.tick(60)

    conexion.cerrar()
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
