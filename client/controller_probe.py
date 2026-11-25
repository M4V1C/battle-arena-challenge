import argparse
import math

import pygame

from controller import ControlSDL, EntradaControl


ANCHO, ALTO = 1120, 720
ARENA = pygame.Rect(24, 152, 752, 520)
FONDO = (30, 30, 40)
TEXTO = (240, 240, 240)
GRIS = (160, 170, 180)
VERDE = (120, 220, 150)
AMARILLO = (250, 220, 50)
ROJO = (220, 55, 55)


class DemostracionControl:
    def __init__(self):
        self.posicion = pygame.Vector2(ARENA.center)
        self.direccion = pygame.Vector2(1, 0)
        self.proyectiles: list[tuple[pygame.Vector2, pygame.Vector2]] = []
        self.interacciones = 0
        self.disparos = 0
        self.anillo = 0.0
        self.direcciones: set[str] = set()
        self.reposo = False

    @property
    def verificaciones(self) -> dict[str, bool]:
        return {
            "Stick izquierdo": len(self.direcciones) == 4 and self.reposo,
            "X / Interactuar": self.interacciones > 0,
            "R2 / Disparar": self.disparos > 0,
        }

    @property
    def verificada(self) -> bool:
        return all(self.verificaciones.values())

    def actualizar(self, entrada: EntradaControl, delta_t: float) -> None:
        movimiento = pygame.Vector2(entrada.x, entrada.y)
        if movimiento.length_squared():
            self.direccion = movimiento.normalize()
            self.posicion += movimiento * 240 * delta_t
        self.posicion.x = max(ARENA.left + 20, min(self.posicion.x, ARENA.right - 20))
        self.posicion.y = max(ARENA.top + 20, min(self.posicion.y, ARENA.bottom - 20))
        for direccion, valor in (("derecha", entrada.x), ("izquierda", -entrada.x),
                                 ("abajo", entrada.y), ("arriba", -entrada.y)):
            if valor > 0.25:
                self.direcciones.add(direccion)
                self.reposo = False
        if not movimiento.length_squared() and len(self.direcciones) == 4:
            self.reposo = True
        self.anillo = max(0.0, self.anillo - delta_t)
        self.proyectiles = [
            (posicion + direccion * 900 * delta_t, direccion)
            for posicion, direccion in self.proyectiles
            if ARENA.inflate(-8, -8).collidepoint(posicion + direccion * 900 * delta_t)
        ]
        if entrada.interactuar:
            self.interacciones += 1
            self.anillo = 0.15
            print(f"[hardware] X -> interactuar #{self.interacciones}", flush=True)
        if entrada.disparar:
            self.disparos += 1
            self.proyectiles.append((self.posicion.copy(), self.direccion.copy()))
            print(f"[hardware] R2 -> disparar #{self.disparos}", flush=True)


def dibujar(
    pantalla: pygame.Surface, fuente: pygame.font.Font, titulo: pygame.font.Font,
    control: ControlSDL, entrada: EntradaControl, demo: DemostracionControl,
) -> None:
    pantalla.fill(FONDO)

    def texto(contenido: str, posicion: tuple[int, int], color=TEXTO, grande=False):
        imagen = (titulo if grande else fuente).render(contenido, True, color)
        pantalla.blit(imagen, posicion)

    texto("Prueba de control", (24, 20), grande=True)
    texto(control.nombre[:65], (24, 72), VERDE if control.conectado else ROJO)
    texto("Conectado" if control.conectado else "Desconectado", (808, 30), VERDE if control.conectado else ROJO)
    for horizontal in range(ARENA.left, ARENA.right, 40):
        pygame.draw.line(pantalla, (40, 42, 53), (horizontal, ARENA.top), (horizontal, ARENA.bottom))
    for vertical in range(ARENA.top, ARENA.bottom, 40):
        pygame.draw.line(pantalla, (40, 42, 53), (ARENA.left, vertical), (ARENA.right, vertical))
    pygame.draw.rect(pantalla, (90, 100, 115), ARENA, 1)
    direccion = demo.direccion * 20
    lateral = pygame.Vector2(-direccion.y, direccion.x)
    pygame.draw.polygon(pantalla, ROJO, [
        demo.posicion + direccion,
        demo.posicion - direccion * 0.8 + lateral * 0.8,
        demo.posicion - direccion * 0.3,
        demo.posicion - direccion * 0.8 - lateral * 0.8,
    ])
    if demo.anillo:
        pygame.draw.circle(pantalla, AMARILLO, demo.posicion, 40, 3)
    for posicion, _ in demo.proyectiles:
        pygame.draw.circle(pantalla, AMARILLO, posicion, 4)
    texto("Stick izquierdo", (808, 144))
    centro_stick = pygame.Vector2(936, 244)
    pygame.draw.circle(pantalla, GRIS, centro_stick, 58, 1)
    pygame.draw.circle(pantalla, VERDE, centro_stick + pygame.Vector2(entrada.x, entrada.y) * 50, 8)
    texto(f"X: {entrada.x:+.2f}   Y: {entrada.y:+.2f}", (808, 318), GRIS)
    texto("X / Interactuar", (808, 374))
    pygame.draw.circle(pantalla, AMARILLO if entrada.boton_x else GRIS, (1076, 386), 10, 0 if entrada.boton_x else 2)
    texto(f"Acciones: {demo.interacciones}", (808, 410), GRIS)
    texto(f"R2 / Disparar: {entrada.gatillo:.0%}", (808, 468))
    pygame.draw.rect(pantalla, (70, 75, 90), (808, 506, 280, 12))
    pygame.draw.rect(pantalla, AMARILLO, (808, 506, round(280 * entrada.gatillo), 12))
    texto(f"Disparos: {demo.disparos}", (808, 538), GRIS)
    for indice, (nombre, verificado) in enumerate(demo.verificaciones.items()):
        texto(f"{nombre}: {'OK' if verificado else 'Pendiente'}", (24 + indice * 365, 108), VERDE if verificado else GRIS)
    if demo.verificada:
        texto("Verificacion fisica completa", (808, 612), VERDE)
    elif control.error:
        texto(control.error[:70], (24, 686), ROJO)


def ejecutar(verificar: bool = False, duracion: float | None = None) -> int:
    pygame.init()
    control = None
    demo = DemostracionControl()
    try:
        pantalla = pygame.display.set_mode((ANCHO, ALTO))
        pygame.display.set_caption("Battle Arena - Prueba independiente del control")
        fuente = pygame.font.SysFont(None, 25)
        titulo = pygame.font.SysFont(None, 42)
        control = ControlSDL()
        reloj = pygame.time.Clock()
        inicio = pygame.time.get_ticks()
        activo = True
        nombre_anterior = None
        direccion_anterior = set()
        while activo:
            delta_t = min(reloj.tick(60) / 1000, 0.05)
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT or (evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE):
                    activo = False
                control.procesar_evento(evento)
            if not activo:
                break
            entrada = control.leer()
            if control.nombre != nombre_anterior:
                print(f"[hardware] {control.nombre}", flush=True)
                nombre_anterior = control.nombre
            demo.actualizar(entrada, delta_t)
            if demo.direcciones != direccion_anterior:
                print(f"[hardware] Stick: {', '.join(sorted(demo.direcciones))}", flush=True)
                direccion_anterior = set(demo.direcciones)
            dibujar(pantalla, fuente, titulo, control, entrada, demo)
            pygame.display.flip()
            if duracion is not None and (pygame.time.get_ticks() - inicio) / 1000 >= duracion:
                break
    finally:
        if control is not None:
            control.cerrar()
        pygame.quit()
    for nombre, verificado in demo.verificaciones.items():
        print(f"{nombre}: {'OK' if verificado else 'Pendiente'}", flush=True)
    return 0 if not verificar or demo.verificada else 1


def main() -> int:
    argumentos = argparse.ArgumentParser(description="Prueba local de hardware SDL, sin servidor.")
    argumentos.add_argument("--verificar", action="store_true")
    argumentos.add_argument("--duracion", type=float, default=None)
    opciones = argumentos.parse_args()
    if opciones.duracion is not None and (not math.isfinite(opciones.duracion) or opciones.duracion <= 0):
        argumentos.error("--duracion debe ser un numero positivo finito")
    try:
        return ejecutar(opciones.verificar, opciones.duracion)
    except pygame.error as error:
        print(f"Error de SDL: {error}", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())