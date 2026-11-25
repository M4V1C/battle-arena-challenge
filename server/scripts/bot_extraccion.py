"""Prueba de extremo a extremo: un bot camina al reactor y extrae energía.

Con el servidor corriendo:  python scripts/bot_extraccion.py [host] [puerto]
Muestra el rechazo por estar lejos, el reactor en uso, los puntos y la liberación.
"""

import json
import math
import socket
import sys
import time

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PUERTO = int(sys.argv[2]) if len(sys.argv) > 2 else 9000


class Bot:
    def __init__(self):
        self.conn = socket.create_connection((HOST, PUERTO), timeout=5)
        self.lector = self.conn.makefile("r", encoding="utf-8", newline="\n")
        self.interact = 0

    def enviar(self, **mensaje) -> dict:
        self.conn.sendall((json.dumps(mensaje) + "\n").encode("utf-8"))
        return json.loads(self.lector.readline())

    def mover(self, x=0, y=0, pulsar=False) -> dict:
        self.interact += 1 if pulsar else 0
        return self.enviar(type="input", x=x, y=y, interact=self.interact, shoot=0)


def rechazos(estado):
    return [n["code"] for n in estado["notifications"] if n["kind"] == "reject"]


def resumen(estado):
    rojo = estado["players"]["red"]
    return (f"pos=({rojo['x']:.0f},{rojo['y']:.0f}) puntos={rojo['score']} "
            f"extracting={rojo['extracting']} frozen={rojo['frozen']} "
            f"reactor={estado['reactor']['status']} rechazos={rechazos(estado)}")


ana, beto = Bot(), Bot()
try:
    ana.enviar(type="join", token="ana")
    beto.enviar(type="join", token="beto")
    estado = ana.enviar(type="start")
    print("inicio                  ", resumen(estado))
    estado = ana.mover(pulsar=True)
    print("E lejos del reactor     ", resumen(estado))

    reactor = (estado["reactor"]["x"] + 20, estado["reactor"]["y"] + 20)
    for _ in range(1200):
        rojo = estado["players"]["red"]
        dx, dy = reactor[0] - (rojo["x"] + 20), reactor[1] - (rojo["y"] + 20)
        if math.hypot(dx, dy) <= 50:
            break
        norma = math.hypot(dx, dy)
        estado = ana.mover(dx / norma, dy / norma)
        time.sleep(1 / 60)
    print("llegó al reactor        ", resumen(estado))

    estado = ana.mover(pulsar=True)
    print("E junto al reactor      ", resumen(estado))
    time.sleep(2.1)
    estado = beto.mover(pulsar=True)
    print("beto intenta usarlo     ", resumen(estado))
    print("beto rechazos           ", [n["code"] for n in estado["notifications"] if n["for"] == "blue"])
    estado = ana.mover()
    print("tras 2.1 s extrayendo   ", resumen(estado))
    estado = ana.mover(pulsar=True)
    time.sleep(1.0)
    estado = ana.mover()
    print("soltó el reactor (+1 s) ", resumen(estado))
finally:
    ana.conn.close()
    beto.conn.close()
