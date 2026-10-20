import pygame

from game import ALTO, ANCHO, COLOR_ERROR, COLOR_ROJO, COLOR_TEXTO, FONDO, Juego


VOLVER = pygame.Rect(ANCHO - 80, 16, 56, 48)


def dibujar_volver(pantalla: pygame.Surface) -> None:
    color = COLOR_ERROR if VOLVER.collidepoint(pygame.mouse.get_pos()) else COLOR_ROJO
    centro = pygame.Vector2(VOLVER.center)
    puntos = [(-20, 0), (-3, -16), (-3, -6), (20, -6),
              (20, 6), (-3, 6), (-3, 16)]
    pygame.draw.polygon(pantalla, color, [centro + punto for punto in puntos])


class Aplicacion:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.pantalla_actual = "login"
        self.activa = True
        self.error = ""

    def botones(self) -> list[tuple[pygame.Rect, str, str]]:
        opciones = {
            "login": [("Continuar", "inicio")],
            "inicio": [("Empezar", "juego"), ("Configuracion", "configuracion")],
            "configuracion": [],
        }[self.pantalla_actual]
        altura = len(opciones) * 64 + max(0, len(opciones) - 1) * 20
        return [
            (pygame.Rect(ANCHO // 2 - 160, ALTO // 2 - altura // 2 + indice * 84,
                         320, 64), etiqueta, destino)
            for indice, (etiqueta, destino) in enumerate(opciones)
        ]

    def procesar_evento(self, evento: pygame.event.Event) -> None:
        if evento.type == pygame.QUIT:
            self.activa = False
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if self.pantalla_actual != "login" and VOLVER.collidepoint(evento.pos):
                self.pantalla_actual = "login" if self.pantalla_actual == "inicio" else "inicio"
                self.error = ""
                return
            for rectangulo, _, destino in self.botones():
                if rectangulo.collidepoint(evento.pos):
                    self.error = ""
                    if destino == "juego":
                        try:
                            self.activa = Juego(self.host, self.port).ejecutar()
                        except (OSError, ValueError) as error:
                            self.error = str(error)
                    else:
                        self.pantalla_actual = destino
                    return

    def dibujar(self, pantalla: pygame.Surface, fuente: pygame.font.Font) -> None:
        pantalla.fill(FONDO)
        titulos = {"login": "Login", "inicio": "Inicio", "configuracion": "Configuracion"}
        titulo = fuente.render(titulos[self.pantalla_actual], True, COLOR_TEXTO)
        pantalla.blit(titulo, titulo.get_rect(center=(ANCHO // 2, 180)))
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

    def ejecutar(self) -> None:
        pygame.init()
        try:
            pantalla = pygame.display.set_mode((ANCHO, ALTO))
            pygame.display.set_caption("Battle Arena")
            fuente = pygame.font.SysFont(None, 36)
            reloj = pygame.time.Clock()
            while self.activa:
                for evento in pygame.event.get():
                    self.procesar_evento(evento)
                    if not self.activa:
                        break
                self.dibujar(pantalla, fuente)
                pygame.display.flip()
                reloj.tick(60)
        finally:
            pygame.quit()