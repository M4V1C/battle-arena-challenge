"""Ventana Pygame y controles locales para los dos jugadores."""

import pygame

from network import ConexionServidor

# Dimensiones visuales compartidas con el estado de juego del servidor.
ANCHO, ALTO = 1600, 900         # Dimensiones de la ventana de juego
TAMANO_JUGADOR = 40             # Tamaño visual de cada jugador en la ventana
FONDO = (30, 30, 40)            # Color de fondo de la ventana de juego
COLOR_ROJO = (220, 55, 55)      # Color del jugador rojo
COLOR_AZUL = (55, 110, 230)     # Color del jugador azul
COLOR_TEXTO = (240, 240, 240)   # Color del texto en la ventana de juego
COLOR_ERROR = (255, 150, 150)   # Color de los mensajes de error en la ventana de juego
INTERVALO_ENTRADAS = 1 / 60     # Intervalo de tiempo entre envíos de entradas al servidor (segundos)

# Clase principal que maneja la lógica del juego y la interacción con el servidor.
class Juego:

    # Inicializa la conexión con el servidor y el estado visual del juego.
    def __init__(self, host: str, port: int):
        self._conexion = ConexionServidor(host, port)
        self._estado = {
            "players": {
                "red": {"x": 100, "y": 100},
                "blue": {"x": 660, "y": 460},
            }
        }
        self._mensaje = f"Rojo: WASD    Azul: flechas    Servidor: {host}:{port}"

    # Ejecuta el ciclo principal de Pygame y gestiona la comunicación con el servidor.
    def ejecutar(self) -> None:
        pygame.init()
        pantalla = pygame.display.set_mode((ANCHO, ALTO))
        pygame.display.set_caption("Battle Arena - Dos jugadores")
        fuente = pygame.font.SysFont(None, 28)
        reloj = pygame.time.Clock()
        activo = True
        tiempo_ultima_entrada = 0.0

        # Bucle principal de Pygame con control de entradas y actualización de estado.
        try:
            while activo:
                for evento in pygame.event.get():
                    if evento.type == pygame.QUIT:
                        activo = False

                ahora = pygame.time.get_ticks() / 1000
                if ahora - tiempo_ultima_entrada >= INTERVALO_ENTRADAS:
                    self._conexion.enviar_entradas(self._leer_controles())
                    tiempo_ultima_entrada = ahora

                respuesta = self._conexion.obtener_estado()
                if respuesta is not None:
                    if respuesta.get("type") == "state":
                        self._estado = respuesta
                    elif respuesta.get("type") == "error":
                        self._mensaje = f"Error de conexión: {respuesta.get('message', '')}"

                self._dibujar(pantalla, fuente)
                pygame.display.flip()
                reloj.tick(60)
        finally:
            self._conexion.cerrar()
            pygame.quit()

    # Convierte el teclado en direcciones discretas para el servidor.
    def _leer_controles(self) -> dict[str, dict[str, int]]:
        teclas = pygame.key.get_pressed()
        return {
            "red": {
                "x": int(teclas[pygame.K_d]) - int(teclas[pygame.K_a]),
                "y": int(teclas[pygame.K_s]) - int(teclas[pygame.K_w]),
            },
            "blue": {
                "x": int(teclas[pygame.K_RIGHT]) - int(teclas[pygame.K_LEFT]),
                "y": int(teclas[pygame.K_DOWN]) - int(teclas[pygame.K_UP]),
            },
        }

    # Dibuja la arena y los jugadores según el estado actual.
    def _dibujar(self, pantalla: pygame.Surface, fuente: pygame.font.Font) -> None:
        pantalla.fill(FONDO)
        jugadores = self._estado.get("players", {})
        for nombre, color in (("red", COLOR_ROJO), ("blue", COLOR_AZUL)):
            posicion = jugadores.get(nombre)
            if posicion is None:
                continue
            rectangulo = pygame.Rect(
                int(posicion["x"]),
                int(posicion["y"]),
                TAMANO_JUGADOR,
                TAMANO_JUGADOR,
            )
            pygame.draw.rect(pantalla, color, rectangulo)

        texto = fuente.render(self._mensaje, True, COLOR_TEXTO)
        pantalla.blit(texto, (20, ALTO - 35))
