"""Prueba manual del servidor con bots TCP.

Con el servidor corriendo:  python scripts/bots.py [host] [puerto]
"""

import json
import socket
import sys
import time

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PUERTO = int(sys.argv[2]) if len(sys.argv) > 2 else 9000


class Bot:
    def __init__(self, nombre: str):
        self.nombre = nombre
        self.conn = socket.create_connection((HOST, PUERTO), timeout=5)
        self.lector = self.conn.makefile("r", encoding="utf-8", newline="\n")

    def enviar(self, **mensaje) -> dict:
        self.conn.sendall((json.dumps(mensaje) + "\n").encode("utf-8"))
        return json.loads(self.lector.readline())

    def cerrar(self) -> None:
        self.lector.close()
        self.conn.close()


def mostrar(titulo: str, respuesta: dict) -> None:
    if respuesta.get("type") == "state":
        rechazos = [n["code"] for n in respuesta["notifications"] if n["kind"] == "reject"]
        rojo, azul = respuesta["players"]["red"], respuesta["players"]["blue"]
        resumen = (
            f"state started={respuesta['match']['started']} "
            f"red={rojo['username']}({rojo['x']:.0f},{rojo['y']:.0f}) "
            f"blue={azul['username']}({azul['x']:.0f},{azul['y']:.0f}) "
            f"rechazos={rechazos[-3:]}"
        )
    else:
        resumen = json.dumps(respuesta, ensure_ascii=False)
    print(f"{titulo:<34} {resumen}")


ana, beto, carla = Bot("ana"), Bot("beto"), Bot("carla")
try:
    mostrar("ana  join", ana.enviar(type="join", token="ana"))
    mostrar("beto join", beto.enviar(type="join", token="beto"))
    mostrar("carla join (sala llena)", carla.enviar(type="join", token="carla"))
    mostrar("beto start (no es anfitrión)", beto.enviar(type="start"))
    mostrar("ana  input antes de start", ana.enviar(type="input", x=1, y=0, interact=0, shoot=0))
    mostrar("ana  start", ana.enviar(type="start"))
    mostrar("ana  input (mueve a red)", ana.enviar(type="input", x=1, y=0, interact=0, shoot=0))
    mostrar("beto input como red (ajeno)", beto.enviar(type="input", player="red", x=1, y=0, interact=0, shoot=0))
    mostrar("beto input propio (mueve a blue)", beto.enviar(type="input", x=-1, y=0, interact=0, shoot=0))
    time.sleep(0.5)
    mostrar("estado tras 0.5 s", ana.enviar(type="state"))
finally:
    for bot in (ana, beto, carla):
        bot.cerrar()
