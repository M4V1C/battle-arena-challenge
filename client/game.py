# Ventana Pygame y controles locales para los dos jugadores.

from importlib import import_module
from pathlib import Path
import sys

import pygame

from controller import ControlSDL
from keybindings import cargar_keybindings
from network import ConexionServidor
from avatar_repository import RepositorioAvatares
from avatar_renderer import RenderizadorAvatares
from victory_screen import PantallaVictoria
from hud_notifications import NotificacionesHUD

ANCHO, ALTO = 1600, 900             # Dimensiones de la ventana de juego
TAMANO_JUGADOR = 40                 # Tamaño visual de cada jugador en la ventana
FONDO = (30, 30, 40)                # Color de fondo de la ventana de juego
COLOR_ROJO = (220, 55, 55)          # Color del jugador rojo
COLOR_AZUL = (55, 110, 230)         # Color del jugador azul
COLOR_OBSTACULO = (110, 110, 125)   # Color de los obstáculos
COLOR_PUERTA_CERRADA = (230, 145, 65)
COLOR_PUERTA_ABIERTA = (90, 215, 130)
COLORES_TRAMPA = {"jaula": (215, 75, 80), "arenas": (180, 145, 65), "inversion": (145, 95, 220)}
LETRAS_TRAMPA = {"jaula": "J", "arenas": "A", "inversion": "I"}
COLOR_INTERACCION = (250, 220, 50)  # Color del círculo de interacción
COLOR_PROYECTIL = (255, 240, 150)   # Color de los disparos
COLOR_REACTOR = (250, 210, 40)      # Color del reactor y su anillo
COLOR_CONGELADO = (170, 230, 255)   # Contorno de un jugador congelado en el reactor
COLOR_TEXTO = (240, 240, 240)       # Color del texto en la ventana de juego
COLOR_ERROR = (255, 150, 150)       # Color de los mensajes de error en la ventana de juego
COLOR_DIRECCION_DESEADA = (185, 195, 205)
COLOR_NORMAL = (120, 220, 150)
COLOR_INMOVILIZADO = (255, 160, 100)
COLOR_EXTRAYENDO = (250, 220, 50)
INTERVALO_ENTRADAS = 1 / 60         # Intervalo de tiempo entre envíos de entradas al servidor (segundos)

# Clase principal que maneja la lógica del juego y la interacción con el servidor.
class Juego:

    # Inicializa la conexión con el servidor y el estado visual del juego.
    def __init__(
        self,
        host: str,
        port: int,
        jugador_rojo: str | None = None,
        jugador_azul: str | None = None,
        token: str | None = None,
        escenario: str = "arena_clasica",
    ):
        if not token:
            raise ValueError("Se necesita iniciar sesión para conectarse al servidor.")

        self._conexion = ConexionServidor(
            host,
            port,
            solicitud_inicial={"type": "join", "token": token},
        )
        self._escenario = escenario
        self._nombres = {"red": jugador_rojo or "Rojo","blue": jugador_azul or "Azul",
}
        self._estado = {
            "players": {
                "red": {"x": 100, "y": 100, "dir_x": 1, "dir_y": 0},
                "blue": {"x": ANCHO - TAMANO_JUGADOR - 100, "y": ALTO - TAMANO_JUGADOR - 100, "dir_x": -1, "dir_y": 0},
            }
        }
        # Contadores acumulados de pulsaciones que se envían al servidor.
        self._contadores = {"shoot": 0, "interact": 0}
        self._teclas: dict[str, dict[str, int]] = {}
        self._control: ControlSDL | None = None
        self._mensaje = f"Servidor: {host}:{port}"
        self._notificaciones = NotificacionesHUD()
        self._ultima_notificacion_id = 0
        self._puesto: str | None = None
        self._inicio_solicitado = False

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
        try:
            self._control = ControlSDL()
        except pygame.error as error:
            self._control = None
            self._mensaje = f"Control no disponible; se usa teclado: {error}"
        pygame.display.set_caption("Battle Arena Challenge - Cliente multijugador")
        fuente = pygame.font.SysFont(None, 28)
        reloj = pygame.time.Clock()
        activo = True
        tiempo_ultima_entrada = 0.0

        # Bucle principal de Pygame con control de entradas y actualización de estado.
        try:
            while activo:
                for evento in pygame.event.get():
                    if self._control is not None:
                        self._control.procesar_evento(evento)
                    if evento.type == pygame.QUIT:
                        return False
                    elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                        if VOLVER.collidepoint(evento.pos):
                            return True
                    elif evento.type == pygame.KEYDOWN:
                        self._registrar_accion(evento.key)

                ahora = pygame.time.get_ticks() / 1000
                if self._puesto is not None and ahora - tiempo_ultima_entrada >= INTERVALO_ENTRADAS:
                    partida = self._estado.get("match", {})

                    if partida.get("started") and not partida.get("finished"):
                        self._conexion.enviar_entradas(self._leer_controles())
                    else:
                        self._conexion.enviar_mensaje({"type": "state"})

                    tiempo_ultima_entrada = ahora

                mensaje = self._conexion.obtener_mensaje()

                while mensaje is not None:
                    if mensaje.get("type") == "joined":
                        self._puesto = mensaje["slot"]
                        self._ultima_notificacion_id = mensaje.get("last_notification_id", 0)
                        self._mensaje = f"Conectado como {mensaje['username']} ({self._puesto})"
                        self._conexion.enviar_mensaje({"type": "state"})

                    elif mensaje.get("type") == "error":
                        self._mensaje = f"Error de conexión: {mensaje.get('message', '')}"
                    elif mensaje.get("type") == "reject":
                        self._mensaje = mensaje.get("message", "Solicitud rechazada")

                    mensaje = self._conexion.obtener_mensaje()
                respuesta = self._conexion.obtener_estado()
                if respuesta is not None:
                    if respuesta.get("type") == "state":
                        self._estado = respuesta
                        self._procesar_notificaciones(respuesta)
                        self._intentar_iniciar_partida(respuesta)
                        for puesto in ("red", "blue"):
                            usuario = respuesta.get("players", {}).get(puesto, {}).get("username")
                            if usuario:
                                self._nombres[puesto] = usuario
                        if respuesta.get("match", {}).get("finished"):

                            pantalla_victoria = PantallaVictoria(estado=self._estado,avatares=self._avatares, nombres=self._nombres,)
                            return pantalla_victoria.ejecutar()
                    elif respuesta.get("type") == "error":
                        self._mensaje = f"Error de conexión: {respuesta.get('message', '')}"

                self._dibujar(pantalla, fuente)
                dibujar_volver(pantalla)
                pygame.display.flip()
                reloj.tick(60)
        finally:
            if self._control is not None:
                self._control.cerrar()
                self._control = None
            self._conexion.cerrar()

    # Cuenta las pulsaciones de disparo e interacción del jugador local.
    def _registrar_accion(self, tecla: int) -> None:
        if self._puesto is None:
            return

        teclas = self._teclas[self._puesto]

        for accion in ("shoot", "interact"):
            if tecla == teclas[accion]:
                self._contadores[accion] += 1


    # Obtiene los controles del jugador asignado por el servidor.
    def _leer_controles(self) -> dict[str, int]:
        teclas = self._teclas[self._puesto]
        presionadas = pygame.key.get_pressed()

        entradas = {
            "x": int(presionadas[teclas["right"]]) - int(presionadas[teclas["left"]]),
            "y": int(presionadas[teclas["down"]]) - int(presionadas[teclas["up"]]),
            "interact": self._contadores["interact"],
            "shoot": self._contadores["shoot"],
        }

        if self._control is None:
            return entradas

        control = self._control.leer()

        if control.x or control.y:
            entradas["x"] = control.x
            entradas["y"] = control.y

        if control.interactuar:
            self._contadores["interact"] += 1

        if control.disparar:
            self._contadores["shoot"] += 1

        entradas.update(self._contadores)
        return entradas

    def _intentar_iniciar_partida(self, estado: dict) -> None:
        jugadores = estado.get("players", {})
        partida = estado.get("match", {})

        if (
            self._puesto == "red"
            and not self._inicio_solicitado
            and not partida.get("started")
            and not partida.get("finished")
            and jugadores.get("red", {}).get("connected")
            and jugadores.get("blue", {}).get("connected")
        ):
            self._inicio_solicitado = True
            self._conexion.enviar_mensaje({
                "type": "start",
                "scenario": self._escenario,
            })

    # Muestra las notificaciones nuevas dirigidas al jugador local.
    def _procesar_notificaciones(self, estado: dict) -> None:
        colores = {
            "info": (240, 240, 240),
            "good": (120, 220, 150),
            "warning": (255, 200, 100),
            "danger": (255, 100, 100),
        }

        for notificacion in estado.get("notifications", []):
            identificador = notificacion.get("id", 0)

            if identificador <= self._ultima_notificacion_id:
                continue
            if (
                self._puesto == "red"
                and not estado.get("match", {}).get("started")
                and notificacion.get("kind") == "reject"
                and notificacion.get("for") == self._puesto
                and notificacion.get("code") == "waiting_for_players"
            ):
                self._inicio_solicitado = False

            destinatario = notificacion.get("for")
            if destinatario is None or destinatario == self._puesto:
                self._notificaciones.agregar(
                    notificacion.get("message", ""),
                    colores.get(notificacion.get("severity"), colores["info"]),
                )

            self._ultima_notificacion_id = identificador

    @staticmethod
    def _obtener_estado_jugador(jugador: dict) -> tuple[str, tuple[int, int, int]]:
        """Devuelve el texto y color correspondientes al estado del jugador."""

        estado = jugador.get("status")

        if jugador.get("frozen") and jugador.get("trap"):
            return f"Atrapado: {jugador['trap']} ({jugador.get('trap_remaining', 0):.1f}s)", COLOR_INMOVILIZADO
        if estado in ("stunned", "frozen") or jugador.get("frozen"):
            return "Inmovilizado", COLOR_INMOVILIZADO

        if jugador.get("extracting"):
            return "Extrayendo energia", COLOR_EXTRAYENDO

        if jugador.get("slowed"):
            return f"Ralentizado ({jugador.get('slow_remaining', 0):.1f}s)", COLOR_INMOVILIZADO

        if jugador.get("interacting"):
            return "Interactuando", COLOR_EXTRAYENDO

        return "Normal", COLOR_NORMAL
    
    def _obtener_estado_reactor(self, reactor: dict) -> tuple[str, tuple[int, int, int]]:
        """Devuelve el estado del reactor usando el nombre del jugador."""

        if not isinstance(reactor, dict):
            return "Estado desconocido", (180, 180, 180)

        operador = reactor.get("operator")
        estado = reactor.get("status")

        if estado == "overload":
            return "Reactor sobrecargado", (255, 180, 80)

        if estado == "available":
            return "Reactor disponible", (120, 220, 150)

        if estado == "in_use" and operador is None:
            return "Reactor ocupado", (255, 180, 80)

        if operador is None:
            return "Sin operador", (120, 220, 150)

        if operador == "red":
            nombre = self._nombres.get("red", "Jugador sin identificar")
            return f"Operado por {nombre}", (255, 100, 100)

        if operador == "blue":
            nombre = self._nombres.get("blue", "Jugador sin identificar")
            return f"Operado por {nombre}", (100, 160, 255)

        return "Estado desconocido", (180, 180, 180)

    @staticmethod
    def _obtener_estado_partida(partida: dict) -> tuple[str, tuple[int, int, int]]:
        if partida and partida.get("finished", False):
            return "FINALIZADA", (200, 200, 200)

        if not partida or not partida.get("started", False):
            return "EN ESPERA", (255, 200, 100)

        if partida.get("overtime", 0) > 0:
            return "PRORROGA", (255, 160, 80)

        return "EN PARTIDA", (120, 220, 150)

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

        for puerta in self._estado.get("doors", []):
            rectangulo = pygame.Rect(int(puerta["x"]), int(puerta["y"]),
                                    int(puerta["width"]), int(puerta["height"]))
            if puerta["open"]:
                pygame.draw.rect(pantalla, COLOR_PUERTA_ABIERTA, rectangulo, 3)
            else:
                pygame.draw.rect(pantalla, COLOR_PUERTA_CERRADA, rectangulo)

        for trampa in self._estado.get("traps", []):
            rectangulo = pygame.Rect(int(trampa["x"]), int(trampa["y"]),
                                    int(trampa["width"]), int(trampa["height"]))
            color = COLORES_TRAMPA.get(trampa["type"], COLOR_OBSTACULO)
            pygame.draw.rect(pantalla, color, rectangulo)
            pygame.draw.rect(pantalla, COLOR_TEXTO, rectangulo, 2)
            letra = fuente.render(LETRAS_TRAMPA.get(trampa["type"], "?"), True, COLOR_TEXTO)
            pantalla.blit(letra, letra.get_rect(center=rectangulo.center))

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
            self._renderizador_avatares.dibujar(pantalla=pantalla,centro=centro,direccion=direccion,avatar=self._avatares.get(nombre, "avatar_1"), tamano=TAMANO_JUGADOR, invertido=jugador.get("inverted", False),)
            # Resaltar visualmente al jugador controlado en este cliente.
            if nombre == self._puesto:
                contorno_local = pygame.Rect(
                    int(centro.x - TAMANO_JUGADOR / 2 - 5),
                    int(centro.y - TAMANO_JUGADOR / 2 - 5),
                    TAMANO_JUGADOR + 10,
                    TAMANO_JUGADOR + 10,
                )

                pygame.draw.rect(
                    pantalla,
                    (255, 255, 255),
                    contorno_local,
                    3,
                    border_radius=6,
                )
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
        for nombre in ("red", "blue"):
            jugador = jugadores.get(nombre, {})
            puntos = jugador.get("score", 0)
            etiqueta = self._nombres[nombre]

            marcador = fuente.render(
                f"{etiqueta}: {puntos}",
                True,
                colores[nombre],
            )
            pantalla.blit(marcador, (x, 15))

            texto_estado, color_estado = self._obtener_estado_jugador(jugador)

            indicador = fuente.render(
                texto_estado,
                True,
                color_estado,
            )
            pantalla.blit(indicador, (x, 45))

            x += max(marcador.get_width(), indicador.get_width()) + 40

        # Mostrar el estado del reactor una sola vez
        reactor = self._estado.get("reactor", {})

        texto_reactor, color_reactor = self._obtener_estado_reactor(reactor)

        indicador_reactor = fuente.render(
            f"Reactor: {texto_reactor}",
            True,
            color_reactor,
        )

        pantalla.blit(
            indicador_reactor,
            (ANCHO // 2 - indicador_reactor.get_width() // 2, 75),
        )

        partida = self._estado.get("match")

        texto_partida, color_partida = self._obtener_estado_partida(partida)

        indicador_partida = fuente.render(
            texto_partida,
            True,
            color_partida,
        )

        pantalla.blit(
            indicador_partida,
            indicador_partida.get_rect(midtop=(ANCHO // 2, 110)),
        )

        if partida is not None:
            prorrogas = partida.get("overtime", 0)

            if partida["condition"] == "time" or prorrogas > 0:
                tiempo_limite = partida.get("time_limit")

                if tiempo_limite is None:
                    tiempo_limite = partida["value"] * 60

                segundos = max(
                    0,
                    int(tiempo_limite - partida["elapsed"] + 0.999)
                )

                if prorrogas > 0:
                    limite = f"Prorroga {prorrogas}: {segundos // 60}:{segundos % 60:02d}"
                else:
                    limite = f"Tiempo: {segundos // 60}:{segundos % 60:02d}"

            else:
                limite = f"Objetivo: {partida['value']} puntos"

            texto_limite = fuente.render(limite, True, COLOR_TEXTO)
            pantalla.blit(
                texto_limite,
                texto_limite.get_rect(midtop=(ANCHO // 2, 15))
            )
            self._notificaciones.dibujar(pantalla, fuente)
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
