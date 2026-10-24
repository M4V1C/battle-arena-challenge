# Ventana Pygame y controles locales para los dos jugadores.

import pygame

from keybindings import cargar_keybindings
from network import ConexionServidor
from avatar_repository import RepositorioAvatares
from avatar_renderer import RenderizadorAvatares

ANCHO, ALTO = 1600, 900             # Dimensiones de la ventana de juego
TAMANO_JUGADOR = 40                 # Tamaño visual de cada jugador en la ventana
FONDO = (30, 30, 40)                # Color de fondo de la ventana de juego
COLOR_ROJO = (220, 55, 55)          # Color del jugador rojo
COLOR_AZUL = (55, 110, 230)         # Color del jugador azul
COLOR_OBSTACULO = (110, 110, 125)   # Color de los obstáculos
COLOR_INTERACCION = (250, 220, 50)  # Color del círculo de interacción
COLOR_PROYECTIL = (255, 240, 150)   # Color de los disparos
COLOR_REACTOR = (250, 210, 40)      # Color del reactor y su anillo
COLOR_CONGELADO = (170, 230, 255)   # Contorno de un jugador congelado en el reactor
COLOR_TEXTO = (240, 240, 240)       # Color del texto en la ventana de juego
COLOR_ERROR = (255, 150, 150)       # Color de los mensajes de error en la ventana de juego
COLOR_DIRECCION_DESEADA = (185, 195, 205)
INTERVALO_ENTRADAS = 1 / 60         # Intervalo de tiempo entre envíos de entradas al servidor (segundos)

# Clase principal que maneja la lógica del juego y la interacción con el servidor.
class Juego:

    # Inicializa la conexión con el servidor y el estado visual del juego.
    def __init__(self, host: str, port: int):
        self._conexion = ConexionServidor(host, port)
        self._estado = {
            "players": {
                "red": {"x": 100, "y": 100, "dir_x": 1, "dir_y": 0},
                "blue": {"x": ANCHO - TAMANO_JUGADOR - 100, "y": ALTO - TAMANO_JUGADOR - 100, "dir_x": -1, "dir_y": 0},
            }
        }
        # Contadores acumulados de pulsaciones que se envían al servidor.
        self._contadores = {
            jugador: {"shoot": 0, "interact": 0} for jugador in ("red", "blue")
        }
        self._teclas: dict[str, dict[str, int]] = {}
        self._mensaje = f"Servidor: {host}:{port}"

        self._avatares = RepositorioAvatares().obtener()
        self._renderizador_avatares = RenderizadorAvatares()

    # Ejecuta el ciclo principal de Pygame y gestiona la comunicación con el servidor.
    def ejecutar(self) -> bool:
        from screens import VOLVER, dibujar_volver

        pygame.init()
        try:
            self._teclas = cargar_keybindings()
        except (OSError, ValueError):
            self._conexion.cerrar()
            raise
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
                        return False
                    elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                        if VOLVER.collidepoint(evento.pos):
                            return True
                    elif evento.type == pygame.KEYDOWN:
                        self._registrar_accion(evento.key)

                ahora = pygame.time.get_ticks() / 1000
                if ahora - tiempo_ultima_entrada >= INTERVALO_ENTRADAS:
                    self._conexion.enviar_entradas(self._leer_controles())
                    tiempo_ultima_entrada = ahora

                respuesta = self._conexion.obtener_estado()
                if respuesta is not None:
                    if respuesta.get("type") == "state":
                        self._estado = respuesta
                        if respuesta.get("match", {}).get("finished"):
                            return True
                    elif respuesta.get("type") == "error":
                        self._mensaje = f"Error de conexión: {respuesta.get('message', '')}"

                self._dibujar(pantalla, fuente)
                dibujar_volver(pantalla)
                pygame.display.flip()
                reloj.tick(60)
        finally:
            self._conexion.cerrar()

    # Cuenta las pulsaciones de disparo e interacción de cada jugador.
    def _registrar_accion(self, tecla: int) -> None:
        for jugador, teclas in self._teclas.items():
            for accion in ("shoot", "interact"):
                if tecla == teclas[accion]:
                    self._contadores[jugador][accion] += 1

    # Convierte el teclado en direcciones discretas y acciones para el servidor.
    def _leer_controles(self) -> dict[str, dict[str, int]]:
        presionadas = pygame.key.get_pressed()
        return {
            jugador: {
                "x": int(presionadas[t["right"]]) - int(presionadas[t["left"]]),
                "y": int(presionadas[t["down"]]) - int(presionadas[t["up"]]),
                **self._contadores[jugador],
            }
            for jugador, t in self._teclas.items()
        }

    # Dibuja la arena y los jugadores según el estado actual.
    def _dibujar(self, pantalla: pygame.Surface, fuente: pygame.font.Font) -> None:
        pantalla.fill(FONDO)
        for obstaculo in self._estado.get("obstacles", []):
            rectangulo = pygame.Rect(
                int(obstaculo["x"]),
                int(obstaculo["y"]),
                int(obstaculo["width"]),
                int(obstaculo["height"]),
            )
            pygame.draw.rect(pantalla, COLOR_OBSTACULO, rectangulo)

        colores = {"red": COLOR_ROJO, "blue": COLOR_AZUL}
        reactor = self._estado.get("reactor")
        if reactor is not None:
            tamano = reactor["size"]
            rect_reactor = pygame.Rect(int(reactor["x"]), int(reactor["y"]), tamano, tamano)
            # El anillo toma el color del jugador que lo está operando.
            color_anillo = colores.get(reactor.get("operator"), COLOR_REACTOR)
            pygame.draw.circle(
                pantalla, color_anillo, rect_reactor.center, int(reactor["ring_radius"]), 2
            )
            pygame.draw.rect(pantalla, COLOR_REACTOR, rect_reactor)

        jugadores = self._estado.get("players", {})
        for nombre, color in colores.items():
            jugador = jugadores.get(nombre)
            if jugador is None:
                continue
            centro = pygame.Vector2(
                jugador["x"] + TAMANO_JUGADOR / 2,
                jugador["y"] + TAMANO_JUGADOR / 2,
            )
            direccion = pygame.Vector2(jugador.get("dir_x", 1), jugador.get("dir_y", 0))
            self._renderizador_avatares.dibujar(pantalla=pantalla,centro=centro,direccion=direccion,avatar=self._avatares.get(nombre, "avatar_1"), tamano=TAMANO_JUGADOR,)
            deseada = pygame.Vector2(jugador.get("move_x", 0), jugador.get("move_y", 0))
            if deseada.length_squared():
                deseada = deseada.normalize()
                punta = centro + deseada * (TAMANO_JUGADOR * 0.8)
                lateral = pygame.Vector2(-deseada.y, deseada.x)
                pygame.draw.line(pantalla, COLOR_DIRECCION_DESEADA, centro, punta, 1)
                pygame.draw.polygon(pantalla, COLOR_DIRECCION_DESEADA, [
                    punta, punta - deseada * 8 + lateral * 4,
                    punta - deseada * 8 - lateral * 4,
                ])
            if jugador.get("frozen"):
                contorno = pygame.Rect(0, 0, TAMANO_JUGADOR, TAMANO_JUGADOR)
                contorno.center = (int(centro.x), int(centro.y))
                pygame.draw.rect(pantalla, COLOR_CONGELADO, contorno, 2)
            if jugador.get("interacting"):
                # Diámetro = 2x el tamaño del jugador.
                pygame.draw.circle(pantalla, COLOR_INTERACCION, centro, TAMANO_JUGADOR, 3)

        tamano_proyectil = self._estado.get("projectile_size", 8)
        for proyectil in self._estado.get("projectiles", []):
            pygame.draw.rect(
                pantalla,
                COLOR_PROYECTIL,
                pygame.Rect(
                    int(proyectil["x"]), int(proyectil["y"]), tamano_proyectil, tamano_proyectil
                ),
            )

        texto = fuente.render(self._mensaje, True, COLOR_TEXTO)
        pantalla.blit(texto, (20, ALTO - 35))

        x = 20
        for nombre, etiqueta in (("red", "Rojo"), ("blue", "Azul")):
            puntos = jugadores.get(nombre, {}).get("score", 0)
            marcador = fuente.render(f"{etiqueta}: {puntos}", True, colores[nombre])
            pantalla.blit(marcador, (x, 15))
            x += marcador.get_width() + 40

        partida = self._estado.get("match")
        if partida is not None:
            if partida["condition"] == "time":
                segundos = max(0, int(partida["value"] * 60 - partida["elapsed"] + 0.999))
                limite = f"Tiempo: {segundos // 60}:{segundos % 60:02d}"
            else:
                limite = f"Objetivo: {partida['value']} puntos"
            texto_limite = fuente.render(limite, True, COLOR_TEXTO)
            pantalla.blit(texto_limite, texto_limite.get_rect(midtop=(ANCHO // 2, 15)))

    # Dibuja una flecha centrada en el jugador que apunta según su vector de dirección.
    @staticmethod
    def _dibujar_flecha(
        pantalla: pygame.Surface,
        centro: pygame.Vector2,
        direccion: pygame.Vector2,
        color: tuple[int, int, int],
    ) -> None:
        if direccion.length_squared() == 0:
            direccion = pygame.Vector2(1, 0)
        d = direccion.normalize() * (TAMANO_JUGADOR / 2)
        p = pygame.Vector2(-d.y, d.x)
        puntos = [
            centro + d,
            centro - d * 0.8 + p * 0.8,
            centro - d * 0.3,
            centro - d * 0.8 - p * 0.8,
        ]
        pygame.draw.polygon(pantalla, color, puntos)
