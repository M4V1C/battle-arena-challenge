"""Estado autoritativo y reglas de movimiento de la arena."""

import math
import threading
from dataclasses import dataclass
from typing import Any

# Posición actual de un jugador dentro de la arena
@dataclass
class Jugador:
    

    x: float
    y: float


# Rectángulo estático que bloquea el paso de los jugadores.
@dataclass(frozen=True)
class Obstaculo:
    x: float
    y: float
    ancho: float
    alto: float

    def colisiona(self, x: float, y: float, tamano: float) -> bool:
        # Tocar el borde no cuenta como colisión, así el jugador puede deslizarse.
        return (
            x < self.x + self.ancho
            and x + tamano > self.x
            and y < self.y + self.alto
            and y + tamano > self.y
        )

# Obstáculos iniciales en la arena.
MAPA_INICIAL = (
    Obstaculo(300, 250, 200, 40),
    Obstaculo(900, 150, 40, 300),
    Obstaculo(1200, 500, 250, 40),
    Obstaculo(400, 600, 40, 200),
)

# Mantiene y actualiza las posiciones compartidas de ambos jugadores
class EstadoJuego:

    ANCHO = 1600
    ALTO = 900
    TAMANO_JUGADOR = 40
    VELOCIDAD = 240.0

    # Crea la arena con las posiciones iniciales de rojo y azul
    def __init__(self, obstaculos: tuple[Obstaculo, ...] = MAPA_INICIAL):
        self._obstaculos = tuple(obstaculos)
        # El bloqueo hace atómicas las actualizaciones concurrentes recibidas
        # por los hilos que atienden conexiones TCP.
        self._bloqueo = threading.Lock()
        self._jugadores = {
            "red": Jugador(100, 100),
            "blue": Jugador(660, 460),
        }
        # El servidor conserva la última dirección recibida y simula el
        # movimiento a una frecuencia fija, independiente de los paquetes.
        self._entradas = {
            "red": (0, 0),
            "blue": (0, 0),
        }

    # Valida y guarda las entradas más recientes de ambos jugadores.
    def actualizar_entradas(self, entradas: Any) -> dict[str, Any]:
        if not isinstance(entradas, dict):
            raise ValueError("Las entradas deben ser un objeto JSON.")

        direcciones = {
            nombre: self._leer_direccion(entradas.get(nombre))
            for nombre in self._jugadores
        }

        with self._bloqueo:
            self._entradas.update(direcciones)
            return self._crear_estado()

    # Simula el movimiento durante delta_t segundos sin depender de FPS o red.
    def avanzar(self, delta_t: float) -> dict[str, Any]:
        if (
            isinstance(delta_t, bool)
            or not isinstance(delta_t, (int, float))
            or not math.isfinite(delta_t)
            or delta_t < 0
        ):
            raise ValueError("delta_t debe ser un número no negativo.")

        with self._bloqueo:
            for nombre, (dx, dy) in self._entradas.items():
                jugador = self._jugadores[nombre]
                magnitud = math.hypot(dx, dy)
                if magnitud:
                    # Normalizar mantiene la misma velocidad al moverse en diagonal.
                    distancia = self.VELOCIDAD * delta_t
                    # Subpasos cortos evitan atravesar obstáculos delgados con delta_t grandes.
                    pasos = max(1, math.ceil(distancia / (self.TAMANO_JUGADOR / 2)))
                    paso_x = (dx / magnitud) * distancia / pasos
                    paso_y = (dy / magnitud) * distancia / pasos
                    for _ in range(pasos):
                        # Resolver cada eje por separado permite deslizarse por las paredes.
                        self._mover_x(jugador, paso_x)
                        self._mover_y(jugador, paso_y)
            return self._crear_estado()

    def _mover_x(self, jugador: Jugador, delta: float) -> None:
        tamano = self.TAMANO_JUGADOR
        jugador.x = min(max(jugador.x + delta, 0), self.ANCHO - tamano)
        for obstaculo in self._obstaculos:
            if obstaculo.colisiona(jugador.x, jugador.y, tamano):
                if delta > 0:
                    jugador.x = obstaculo.x - tamano
                else:
                    jugador.x = obstaculo.x + obstaculo.ancho

    def _mover_y(self, jugador: Jugador, delta: float) -> None:
        tamano = self.TAMANO_JUGADOR
        jugador.y = min(max(jugador.y + delta, 0), self.ALTO - tamano)
        for obstaculo in self._obstaculos:
            if obstaculo.colisiona(jugador.x, jugador.y, tamano):
                if delta > 0:
                    jugador.y = obstaculo.y - tamano
                else:
                    jugador.y = obstaculo.y + obstaculo.alto

    # Detiene a los jugadores al perderse la conexión del cliente.
    def detener_movimiento(self) -> None:
        with self._bloqueo:
            self._entradas = {nombre: (0, 0) for nombre in self._jugadores}

    # Devuelve un snapshot serializable con ambas posiciones actuales
    def estado(self) -> dict[str, Any]:
        with self._bloqueo:
            return self._crear_estado()

    # Construye una copia serializable del estado mientras ya se posee el bloqueo.
    def _crear_estado(self) -> dict[str, Any]:
        return {
            "type": "state",
            "width": self.ANCHO,
            "height": self.ALTO,
            "player_size": self.TAMANO_JUGADOR,
            "players": {
                nombre: {"x": jugador.x, "y": jugador.y}
                for nombre, jugador in self._jugadores.items()
            },
            "obstacles": [
                {"x": o.x, "y": o.y, "width": o.ancho, "height": o.alto}
                for o in self._obstaculos
            ],
        }

    # Valida que cada eje sea un entero de movimiento entre -1 y 1.
    @staticmethod
    def _leer_direccion(valor: Any) -> tuple[int, int]:
        if not isinstance(valor, dict):
            raise ValueError("Falta la entrada de un jugador.")
        dx = valor.get("x")
        dy = valor.get("y")
        if any(
            isinstance(eje, bool) or not isinstance(eje, int) or eje not in (-1, 0, 1)
            for eje in (dx, dy)
        ):
            raise ValueError("Cada eje debe ser -1, 0 o 1.")
        return dx, dy
