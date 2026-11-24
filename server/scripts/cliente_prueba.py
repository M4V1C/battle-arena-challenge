"""Cliente mínimo para probar el servidor a mano (un jugador por ventana).

Requiere pygame (el mismo del cliente). Con el servidor corriendo, abre dos
terminales, una por jugador:

    python scripts/cliente_prueba.py ana
    python scripts/cliente_prueba.py beto

El primero en entrar es red (anfitrión). Teclas: WASD o flechas = mover,
E = interactuar con el reactor, ESPACIO = disparar, ENTER = iniciar (anfitrión).
"""

import json
import socket
import sys
import time

ANCHO, ALTO = 1600, 900
ESCALA = 0.6
BARRA = 90
COLORES = {"red": (220, 55, 55), "blue": (55, 110, 230)}
SEVERIDAD = {
    "info": (200, 200, 200), "good": (120, 230, 140),
    "warning": (255, 200, 90), "danger": (255, 110, 110),
}
ESTADO_REACTOR = {"available": "disponible", "in_use": "en uso", "overload": "sobrecarga"}


class Conexion:
    """Una solicitud, una respuesta: igual que el protocolo del servidor."""

    def __init__(self, host: str, puerto: int):
        self._socket = socket.create_connection((host, puerto), timeout=5)
        self._lector = self._socket.makefile("r", encoding="utf-8", newline="\n")

    def enviar(self, **mensaje) -> dict:
        self._socket.sendall((json.dumps(mensaje) + "\n").encode("utf-8"))
        linea = self._lector.readline()
        if not linea:
            raise ConnectionError("El servidor cerró la conexión.")
        return json.loads(linea)

    def cerrar(self) -> None:
        self._lector.close()
        self._socket.close()


def avisos_nuevos(estado: dict, ultimo_id: int, puesto: str) -> tuple[list[dict], int]:
    """Avisos con id mayor al último visto y dirigidos a todos o a este puesto."""
    todos = estado.get("notifications", [])
    nuevos = [n for n in todos if n["id"] > ultimo_id and n["for"] in (None, puesto)]
    return nuevos, max([ultimo_id] + [n["id"] for n in todos])


def etiqueta_jugador(jugador: dict) -> str:
    if jugador.get("status") == "stunned":
        return f"aturdido {jugador.get('stun_remaining', 0):.1f}s"
    if jugador.get("frozen"):
        return f"trampa {jugador.get('trap')} {jugador.get('trap_remaining', 0):.1f}s"
    if jugador.get("slowed"):
        return f"ralentizado {jugador.get('slow_remaining', 0):.1f}s"
    if jugador.get("extracting"):
        return "extrayendo"
    return "normal"


def linea_de_estado(estado: dict) -> str:
    partida = estado["match"]
    if partida["finished"]:
        return f"FIN. Ganador: {estado['players'][partida['winner']]['username']}"
    if not partida["started"]:
        return "Esperando inicio (el anfitrión pulsa ENTER con los dos conectados)"
    meta = f"meta {partida['value']} pts" if partida["condition"] == "points" else (
        f"límite {partida['time_limit']:.0f} s"
    )
    return f"Tiempo {partida['elapsed']:.1f} s | {meta}"


def dibujar(pygame, pantalla, fuente, estado: dict, puesto: str, avisos: list) -> None:
    def px(valor):
        return int(valor * ESCALA)

    pantalla.fill((30, 30, 40))
    jugadores = estado["players"]
    for i, nombre in enumerate(("red", "blue")):
        j = jugadores[nombre]
        texto = f"{j['username'] or '---'}: {j['score']} pts [{etiqueta_jugador(j)}]"
        marca = "  <- tú" if nombre == puesto else ""
        pantalla.blit(fuente.render(texto + marca, True, COLORES[nombre]), (10 + i * 500, 8))
    reactor = estado["reactor"]
    operador = reactor["operator"]
    detalle = f" por {jugadores[operador]['username']}" if operador else ""
    texto = f"Reactor: {ESTADO_REACTOR.get(reactor['status'], reactor['status'])}{detalle}"
    pantalla.blit(fuente.render(texto, True, (250, 210, 40)), (10, 34))
    pantalla.blit(fuente.render(linea_de_estado(estado), True, (240, 240, 240)), (10, 60))

    for o in estado["obstacles"]:
        pygame.draw.rect(pantalla, (110, 110, 125),
                         (px(o["x"]), BARRA + px(o["y"]), px(o["width"]), px(o["height"])))
    for puerta in estado.get("doors", []):
        caja = (px(puerta["x"]), BARRA + px(puerta["y"]),
                px(puerta["width"]), px(puerta["height"]))
        pygame.draw.rect(pantalla, (90, 215, 130) if puerta["open"] else (230, 145, 65),
                         caja, 2 if puerta["open"] else 0)
    colores_trampa = {"jaula": (215, 75, 80), "arenas": (180, 145, 65),
                      "inversion": (145, 95, 220)}
    for trampa in estado.get("traps", []):
        caja = (px(trampa["x"]), BARRA + px(trampa["y"]),
                px(trampa["width"]), px(trampa["height"]))
        pygame.draw.rect(pantalla, colores_trampa.get(trampa["type"], (110, 110, 125)), caja)
        marca = fuente.render(trampa["type"][0].upper(), True, (255, 255, 255))
        pantalla.blit(marca, marca.get_rect(center=(caja[0] + caja[2] // 2, caja[1] + caja[3] // 2)))
    for guardian in estado.get("guardians", []):
        cx = px(guardian["x"] + guardian["size"] / 2)
        cy = BARRA + px(guardian["y"] + guardian["size"] / 2)
        lado = max(10, px(guardian["size"] * 0.65))
        frente = pygame.Rect(cx - lado // 2, cy - lado // 2, lado, lado)
        pygame.draw.rect(pantalla, (115, 65, 175), frente)
        pygame.draw.rect(pantalla, (235, 190, 90), frente, 2)
        for signo in (-1, 1):
            codo_x = cx + signo * (lado // 2 + 7)
            pygame.draw.lines(pantalla, (235, 190, 90), False,
                              [(cx + signo * lado // 2, cy - 3),
                               (codo_x, cy - 3), (codo_x, cy + 6)], 2)
            pygame.draw.circle(pantalla, (245, 215, 120), (codo_x, cy + 9), 4)
    centro = (px(reactor["x"] + reactor["size"] / 2), BARRA + px(reactor["y"] + reactor["size"] / 2))
    color_anillo = COLORES.get(operador, (250, 210, 40))
    pygame.draw.circle(pantalla, color_anillo, centro, px(reactor["ring_radius"]), 2)
    pygame.draw.rect(pantalla, (250, 210, 40),
                     (px(reactor["x"]), BARRA + px(reactor["y"]), px(reactor["size"]), px(reactor["size"])))
    for p in estado["projectiles"]:
        pygame.draw.circle(pantalla, (255, 240, 150), (px(p["x"]), BARRA + px(p["y"])), 4)
    tamano = px(estado["player_size"])
    for nombre, j in jugadores.items():
        caja = (px(j["x"]), BARRA + px(j["y"]), tamano, tamano)
        pygame.draw.rect(pantalla, COLORES[nombre], caja)
        if j.get("inverted"):
            pygame.draw.line(pantalla, (255, 255, 255),
                             (caja[0] + tamano // 2, caja[1] + tamano - 3),
                             (caja[0] + tamano // 2, caja[1] + 3), 3)
        if nombre == puesto:
            pygame.draw.rect(pantalla, (255, 255, 255), caja, 3)
        if j["interacting"]:
            pygame.draw.circle(pantalla, (250, 220, 50),
                               (caja[0] + tamano // 2, caja[1] + tamano // 2), tamano, 2)

    ahora = time.monotonic()
    for i, (texto, severidad, expira) in enumerate([a for a in avisos if a[2] > ahora][-4:]):
        pantalla.blit(fuente.render(texto, True, SEVERIDAD.get(severidad, SEVERIDAD["info"])),
                      (10, BARRA + px(ALTO) - 28 * (4 - i)))


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python scripts/cliente_prueba.py <usuario> [host] [puerto]")
        return 1
    usuario = sys.argv[1]
    host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    puerto = int(sys.argv[3]) if len(sys.argv) > 3 else 9000

    import pygame

    conexion = Conexion(host, puerto)
    unido = conexion.enviar(type="join", token=usuario)
    if unido.get("type") != "joined":
        print(f"No se pudo entrar: {unido.get('code')} - {unido.get('message')}")
        return 1
    puesto, ultimo_id = unido["slot"], unido["last_notification_id"]
    print(f"Dentro como {unido['username']} en el puesto {puesto}")

    pygame.init()
    pantalla = pygame.display.set_mode((int(ANCHO * ESCALA), BARRA + int(ALTO * ESCALA)))
    pygame.display.set_caption(f"Prueba - {usuario} ({puesto})")
    fuente = pygame.font.Font(None, 26)
    reloj = pygame.time.Clock()
    contadores = {"interact": 0, "shoot": 0}
    estado, avisos = None, []
    activo = True
    try:
        while activo:
            iniciar = False
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    activo = False
                elif evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_e:
                        contadores["interact"] += 1
                    elif evento.key == pygame.K_SPACE:
                        contadores["shoot"] += 1
                    elif evento.key == pygame.K_RETURN:
                        iniciar = True
            teclas = pygame.key.get_pressed()
            x = int(bool(teclas[pygame.K_d] or teclas[pygame.K_RIGHT])) - int(
                bool(teclas[pygame.K_a] or teclas[pygame.K_LEFT]))
            y = int(bool(teclas[pygame.K_s] or teclas[pygame.K_DOWN])) - int(
                bool(teclas[pygame.K_w] or teclas[pygame.K_UP]))

            if iniciar:
                respuesta = conexion.enviar(type="start")
            else:
                respuesta = conexion.enviar(type="input", x=x, y=y, **contadores)
            if respuesta.get("type") == "state":
                estado = respuesta
                nuevos, ultimo_id = avisos_nuevos(estado, ultimo_id, puesto)
                for n in nuevos:
                    print(f"[{n['severity']}] {n.get('code', n['kind'])}: {n['message']}")
                    avisos.append((n["message"], n["severity"], time.monotonic() + 4))
            else:
                texto = respuesta.get("message", str(respuesta))
                avisos.append((texto, "danger", time.monotonic() + 4))
            if estado is not None:
                dibujar(pygame, pantalla, fuente, estado, puesto, avisos)
            pygame.display.flip()
            reloj.tick(60)
    except ConnectionError as error:
        print(error)
    finally:
        conexion.cerrar()
        pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
