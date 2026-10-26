import pygame

from game import ALTO, ANCHO, COLOR_ERROR, COLOR_ROJO, COLOR_TEXTO, FONDO, Juego
from network import ConexionServidor
from gestion_usuarios import GestionUsuarios
from avatar_selection import PantallaAvatares
from avatar_repository import RepositorioAvatares

# Definición de la interfaz de usuario y la lógica de las pantallas del juego.
VOLVER = pygame.Rect(ANCHO - 80, 16, 56, 48)
MODO_PUNTOS = pygame.Rect(ANCHO // 2 - 240, 300, 240, 56)
MODO_TIEMPO = pygame.Rect(ANCHO // 2, 300, 240, 56)
CAMPO_VALOR = pygame.Rect(ANCHO // 2 - 240, 420, 480, 56)
GUARDAR = pygame.Rect(ANCHO // 2 - 160, 580, 320, 64)

# Función para dibujar el botón de volver en la interfaz.
def dibujar_volver(pantalla: pygame.Surface) -> None:
    color = COLOR_ERROR if VOLVER.collidepoint(pygame.mouse.get_pos()) else COLOR_ROJO
    centro = pygame.Vector2(VOLVER.center)
    puntos = [(-20, 0), (-3, -16), (-3, -6), (20, -6),
              (20, 6), (-3, 6), (-3, 16)]
    pygame.draw.polygon(pantalla, color, [centro + punto for punto in puntos])

# Clase principal de la aplicación que gestiona las pantallas y la interacción del usuario.
class Aplicacion:
    # Inicializa la aplicación con la información del host y puerto del servidor.
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.usuarios = GestionUsuarios()
        self.esperando_segundo_jugador = False
        self.pantalla_actual = "login"
        self.activa = True
        self.error = ""
        self._conexion_config: ConexionServidor | None = None
        self._configuracion = {"condition": "points", "value": 20, "sensitivity": 1.0}
        self._valor = "20"
        self._campo_activo = False
        self._seleccionado = False
        self._pendiente = False
        self._configuracion_cargada = False
        self._confirmacion = ""
        self._pantalla_avatares = PantallaAvatares(RepositorioAvatares())

    def _cerrar_configuracion(self) -> None:
        if self._conexion_config is not None:
            self._conexion_config.cerrar()
            self._conexion_config = None
        self._campo_activo = False
        pygame.key.stop_text_input()

    def _abrir_configuracion(self) -> None:
        self.pantalla_actual = "configuracion"
        self._confirmacion = ""
        self._configuracion_cargada = False
        self._pendiente = True
        try:
            self._conexion_config = ConexionServidor(
                self.host, self.port, solicitud_inicial={"type": "get_config"}
            )
        except OSError as error:
            self._pendiente = False
            self.error = str(error)

    def actualizar_configuracion(self) -> None:
        if self._conexion_config is None:
            return
        respuesta = self._conexion_config.obtener_estado()
        if respuesta is None:
            return
        guardando = self._configuracion_cargada
        self._pendiente = False
        if respuesta.get("type") == "config":
            self._configuracion = respuesta["config"]
            self._valor = str(self._configuracion["value"])
            self._configuracion_cargada = True
            self.error = ""
            self._confirmacion = "Configuracion guardada" if guardando else ""
        else:
            self.error = respuesta.get("message", "Respuesta de configuracion invalida")

    def _guardar_configuracion(self) -> None:
        if self._pendiente or not self._configuracion_cargada or self._conexion_config is None:
            return
        try:
            valor = int(self._valor)
            if valor < 1:
                raise ValueError
        except ValueError:
            self.error = "Introduce un numero entero mayor que cero."
            self._confirmacion = ""
            return
        self.error = ""
        self._confirmacion = ""
        self._pendiente = True
        self._conexion_config.guardar_configuracion({**self._configuracion, "value": valor})

    def _evento_configuracion(self, evento: pygame.event.Event) -> None:
        if self._pendiente or not self._configuracion_cargada:
            return
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            self._campo_activo = CAMPO_VALOR.collidepoint(evento.pos)
            self._seleccionado = self._campo_activo
            if self._campo_activo:
                pygame.key.start_text_input()
                pygame.key.set_text_input_rect(CAMPO_VALOR)
            else:
                pygame.key.stop_text_input()
            for rectangulo, modo in ((MODO_PUNTOS, "points"), (MODO_TIEMPO, "time")):
                if rectangulo.collidepoint(evento.pos):
                    self._configuracion["condition"] = modo
                    self._confirmacion = ""
            if GUARDAR.collidepoint(evento.pos):
                self._guardar_configuracion()
        elif evento.type == pygame.TEXTINPUT and self._campo_activo:
            if all(caracter in "0123456789-" for caracter in evento.text):
                self._valor = ("" if self._seleccionado else self._valor) + evento.text
                self._seleccionado = False
                self._confirmacion = ""
        elif evento.type == pygame.KEYDOWN and self._campo_activo:
            if evento.key == pygame.K_BACKSPACE:
                self._valor = "" if self._seleccionado else self._valor[:-1]
                self._seleccionado = False
            elif evento.key == pygame.K_a and evento.mod & pygame.KMOD_CTRL:
                self._seleccionado = True
            elif evento.key == pygame.K_RETURN:
                self._guardar_configuracion()

    # Define el botón de volver en la interfaz.
    def botones(self) -> list[tuple[pygame.Rect, str, str]]:
        opciones = {
            "login": [
                ("Continuar", "inicio"),
            ],
            "inicio": [
                ("Empezar", "juego"),
                ("Avatares", "avatares"),
                ("Configuracion", "configuracion"),
                ("Perfil", "perfil"),
            ],
            "avatares": [],
            "configuracion": [],
        }[self.pantalla_actual]

        altura = len(opciones) * 64 + max(0, len(opciones) - 1) * 20

        return [
            (
                pygame.Rect(
                    ANCHO // 2 - 160,
                    ALTO // 2 - altura // 2 + indice * 84,
                    320,
                    64,
                ),
                etiqueta,
                destino,
            )
            for indice, (etiqueta, destino) in enumerate(opciones)
        ]

    def _iniciar_juego(self):
        try:
            self.activa = Juego(
                self.host,
                self.port,
                self.usuarios.jugador_rojo,
                self.usuarios.jugador_azul,
            ).ejecutar()
        except (OSError, ValueError) as error:
            self.error = str(error)
            
    # Procesa los eventos de la interfaz, como clics de ratón y cierre de ventana.
    def procesar_evento(self, evento: pygame.event.Event) -> None:
        if self.pantalla_actual in ("login", "perfil") and evento.type != pygame.QUIT:
            pantalla_anterior = self.pantalla_actual

            self.usuarios.procesar_evento(evento)

            if self.usuarios.estado.pantalla == "juego" and self.usuarios.autenticado:
                if self.esperando_segundo_jugador:
                    if self.usuarios.completar_segundo_jugador():
                        self.esperando_segundo_jugador = False
                        self.pantalla_actual = "inicio"
                        self._iniciar_juego()
                    else:
                        self.pantalla_actual = "login"
                else:
                    self.pantalla_actual = "inicio"

            elif pantalla_anterior == "perfil" and not self.usuarios.autenticado:
                self.usuarios.cerrar_sesion()
                self.pantalla_actual = "login"

            return
        if evento.type == pygame.QUIT:
            self._cerrar_configuracion()
            self.activa = False
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if self.pantalla_actual != "login" and VOLVER.collidepoint(evento.pos):
                self._cerrar_configuracion()

                if self.pantalla_actual == "inicio":
                    self.usuarios.cerrar_sesion()
                    self.pantalla_actual = "login"
                else:
                    self.pantalla_actual = "inicio"

                self.error = ""
                return
            for rectangulo, _, destino in self.botones():
                if rectangulo.collidepoint(evento.pos):
                    self.error = ""
                    if destino == "juego":
                        if self.usuarios.preparar_segundo_jugador():
                            self.esperando_segundo_jugador = True
                            self.pantalla_actual = "login"
                    elif destino == "configuracion":
                        self._abrir_configuracion()
                    elif destino == "perfil":
                        self.usuarios.abrir_perfil()
                        self.pantalla_actual = "perfil"
                    else:
                        self.pantalla_actual = destino
                    return
        if self.pantalla_actual == "configuracion":
            self._evento_configuracion(evento)

        if self.pantalla_actual == "avatares":
            self._pantalla_avatares.procesar_evento(evento)

    def _dibujar_configuracion(self, pantalla: pygame.Surface, fuente: pygame.font.Font) -> None:
        for rectangulo, etiqueta, modo in (
            (MODO_PUNTOS, "Puntos", "points"), (MODO_TIEMPO, "Tiempo", "time")
        ):
            color = (75, 110, 125) if self._configuracion["condition"] == modo else (45, 50, 60)
            pygame.draw.rect(pantalla, color, rectangulo)
            texto = fuente.render(etiqueta, True, COLOR_TEXTO)
            pantalla.blit(texto, texto.get_rect(center=rectangulo.center))
        etiqueta = "Puntos para terminar" if self._configuracion["condition"] == "points" else "Duracion en minutos"
        pantalla.blit(fuente.render(etiqueta, True, COLOR_TEXTO), (CAMPO_VALOR.x, 380))
        pygame.draw.rect(pantalla, (45, 50, 60), CAMPO_VALOR)
        borde = COLOR_TEXTO if self._campo_activo else (100, 110, 120)
        pygame.draw.rect(pantalla, borde, CAMPO_VALOR, 2)
        texto_valor = fuente.render(self._valor[-18:] or " ", True, COLOR_TEXTO)
        if self._seleccionado:
            pygame.draw.rect(pantalla, (75, 110, 125), CAMPO_VALOR.inflate(-8, -8))
        pantalla.blit(texto_valor, (CAMPO_VALOR.x + 14, CAMPO_VALOR.y + 14))
        sensibilidad = fuente.render(
            f"Sensibilidad (reservada): {self._configuracion['sensitivity']}", True, (170, 175, 185)
        )
        pantalla.blit(sensibilidad, (CAMPO_VALOR.x, 510))
        habilitado = self._configuracion_cargada and not self._pendiente
        pygame.draw.rect(pantalla, (65, 105, 115) if habilitado else (50, 55, 60), GUARDAR, border_radius=6)
        texto_guardar = fuente.render("Guardar" if not self._pendiente else "Esperando...", True, COLOR_TEXTO)
        pantalla.blit(texto_guardar, texto_guardar.get_rect(center=GUARDAR.center))
        if self._confirmacion:
            texto = fuente.render(self._confirmacion, True, (120, 220, 150))
            pantalla.blit(texto, texto.get_rect(center=(ANCHO // 2, 690)))

    # Dibuja la interfaz de usuario en la pantalla, incluyendo botones y mensajes de error.
    def dibujar(self, pantalla: pygame.Surface, fuente: pygame.font.Font) -> None:
        if self.pantalla_actual in ("login", "perfil"):
            self.usuarios.dibujar()
            return    
        pantalla.fill(FONDO)
        titulos = {"avatares": "Avatares","login": "Login", "inicio": "Inicio", "configuracion": "Configuracion"}
        titulo = fuente.render(titulos[self.pantalla_actual], True, COLOR_TEXTO)
        pantalla.blit(titulo, titulo.get_rect(center=(ANCHO // 2, 180)))
        if self.pantalla_actual == "configuracion":
            self._dibujar_configuracion(pantalla, fuente)
        if self.pantalla_actual == "avatares":
            self._pantalla_avatares.dibujar(pantalla, fuente)
        for rectangulo, etiqueta, _ in self.botones():
            color = (75, 100, 120) if rectangulo.collidepoint(pygame.mouse.get_pos()) else (50, 70, 85)
            pygame.draw.rect(pantalla, color, rectangulo, border_radius=6)
            texto = fuente.render(etiqueta, True, COLOR_TEXTO)
            pantalla.blit(texto, texto.get_rect(center=rectangulo.center))
        if self.pantalla_actual != "login":
            dibujar_volver(pantalla)
        if self.error:
            lineas = [self.error[indice:indice + 85] for indice in range(0, len(self.error), 85)]
            for indice, linea in enumerate(lineas[:3]):
                texto = fuente.render(linea, True, COLOR_ERROR)
                pantalla.blit(texto, (40, ALTO - 140 + indice * 32))

    # Ejecuta el bucle principal de la aplicación, manejando eventos y dibujando la interfaz.
    def ejecutar(self) -> None:
        pygame.init()
        try:
            pantalla = pygame.display.set_mode((ANCHO, ALTO))
            pygame.display.set_caption("Battle Arena")
            fuente = pygame.font.SysFont(None, 36)
            reloj = pygame.time.Clock()
            while self.activa:
                self.actualizar_configuracion()
                for evento in pygame.event.get():
                    self.procesar_evento(evento)
                    if not self.activa:
                        break
                self.dibujar(pantalla, fuente)
                pygame.display.flip()
                reloj.tick(60)
        finally:
            self._cerrar_configuracion()
            pygame.quit()