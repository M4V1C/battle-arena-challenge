"""Estado autoritativo y reglas de movimiento de la arena."""

import math
import threading
from dataclasses import dataclass, field
from typing import Any

ACCIONES = ("shoot", "interact")

# Posición actual de un jugador dentro de la arena
@dataclass
class Jugador:
    x: float
    y: float
    # Vector unitario de apuntado; conserva la última dirección de movimiento.
    dir_x: float = 1.0
    dir_y: float = 0.0
    tiempo_interaccion: float = 0.0
    puntos: int = 0
    # Último contador de pulsaciones procesado por acción.
    contadores: dict[str, int] = field(default_factory=lambda: dict.fromkeys(ACCIONES, 0))


@dataclass
class Proyectil:
    x: float
    y: float
    vx: float
    vy: float
    dueno: str


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
    TAMANO_PROYECTIL = 8
    VELOCIDAD_PROYECTIL = 900.0
    DURACION_INTERACCION = 0.15
    RADIO_REACTOR = 1.5 * TAMANO_JUGADOR  # Anillo de diámetro 3x el hitbox.
    INTERVALO_PUNTO = 0.5

    # Crea la arena con las posiciones iniciales de rojo y azul
    def __init__(self, obstaculos: tuple[Obstaculo, ...] = MAPA_INICIAL):
        self._obstaculos = tuple(obstaculos)
        self._reactor = Obstaculo(
            (self.ANCHO - self.TAMANO_JUGADOR) / 2,
            (self.ALTO - self.TAMANO_JUGADOR) / 2,
            self.TAMANO_JUGADOR,
            self.TAMANO_JUGADOR,
        )
        # El reactor es sólido para jugadores y disparos.
        self._solidos = self._obstaculos + (self._reactor,)
        self._operador_reactor: str | None = None
        self._tiempo_reactor = 0.0
        # El bloqueo hace atómicas las actualizaciones concurrentes recibidas
        # por los hilos que atienden conexiones TCP.
        self._bloqueo = threading.Lock()
        self._jugadores = {
            "red": Jugador(100, 100, dir_x=1.0),
            "blue": Jugador(660, 460, dir_x=-1.0),
        }
        self._proyectiles: list[Proyectil] = []
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
        acciones = {
            nombre: self._leer_acciones(entradas.get(nombre))
            for nombre in self._jugadores
        }

        with self._bloqueo:
            self._entradas.update(direcciones)
            for nombre, (dx, dy) in direcciones.items():
                jugador = self._jugadores[nombre]
                magnitud = math.hypot(dx, dy)
                if magnitud and nombre != self._operador_reactor:
                    jugador.dir_x, jugador.dir_y = dx / magnitud, dy / magnitud
                # Los contadores son acumulativos: una pulsación no se pierde
                # aunque el cliente descarte mensajes intermedios.
                for accion, contador in acciones[nombre].items():
                    if contador > jugador.contadores[accion]:
                        self._ejecutar_accion(nombre, accion)
                    jugador.contadores[accion] = contador
            return self._crear_estado()

    def _ejecutar_accion(self, nombre: str, accion: str) -> None:
        jugador = self._jugadores[nombre]
        if accion == "interact":
            jugador.tiempo_interaccion = self.DURACION_INTERACCION
            if self._operador_reactor == nombre:
                self._operador_reactor = None
            elif self._operador_reactor is None and self._en_rango_reactor(jugador):
                self._operador_reactor = nombre
                self._tiempo_reactor = 0.0
        elif accion == "shoot" and nombre != self._operador_reactor:
            centro = self.TAMANO_JUGADOR / 2 - self.TAMANO_PROYECTIL / 2
            self._proyectiles.append(
                Proyectil(
                    jugador.x + centro,
                    jugador.y + centro,
                    jugador.dir_x * self.VELOCIDAD_PROYECTIL,
                    jugador.dir_y * self.VELOCIDAD_PROYECTIL,
                    nombre,
                )
            )

    def _en_rango_reactor(self, jugador: Jugador) -> bool:
        mitad = self.TAMANO_JUGADOR / 2
        return math.hypot(
            jugador.x + mitad - (self._reactor.x + mitad),
            jugador.y + mitad - (self._reactor.y + mitad),
        ) <= self.RADIO_REACTOR

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
                if magnitud and nombre != self._operador_reactor:
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
            for jugador in self._jugadores.values():
                jugador.tiempo_interaccion = max(0.0, jugador.tiempo_interaccion - delta_t)
            if self._operador_reactor is not None:
                self._tiempo_reactor += delta_t
                puntos, self._tiempo_reactor = divmod(self._tiempo_reactor, self.INTERVALO_PUNTO)
                self._jugadores[self._operador_reactor].puntos += int(puntos)
            self._proyectiles = [
                p for p in self._proyectiles if self._mover_proyectil(p, delta_t)
            ]
            return self._crear_estado()

    # Avanza un proyectil y devuelve False si chocó con algo o salió del mapa.
    def _mover_proyectil(self, proyectil: Proyectil, delta_t: float) -> bool:
        tamano = self.TAMANO_PROYECTIL
        distancia = math.hypot(proyectil.vx, proyectil.vy) * delta_t
        # Subpasos del tamaño del proyectil para no atravesar paredes.
        pasos = max(1, math.ceil(distancia / tamano))
        for _ in range(pasos):
            proyectil.x += proyectil.vx * delta_t / pasos
            proyectil.y += proyectil.vy * delta_t / pasos
            if (
                proyectil.x < 0
                or proyectil.y < 0
                or proyectil.x + tamano > self.ANCHO
                or proyectil.y + tamano > self.ALTO
            ):
                return False
            if any(o.colisiona(proyectil.x, proyectil.y, tamano) for o in self._solidos):
                return False
            for nombre, jugador in self._jugadores.items():
                if nombre != proyectil.dueno and Obstaculo(
                    jugador.x, jugador.y, self.TAMANO_JUGADOR, self.TAMANO_JUGADOR
                ).colisiona(proyectil.x, proyectil.y, tamano):
                    return False
        return True

    def _mover_x(self, jugador: Jugador, delta: float) -> None:
        tamano = self.TAMANO_JUGADOR
        jugador.x = min(max(jugador.x + delta, 0), self.ANCHO - tamano)
        for obstaculo in self._solidos:
            if obstaculo.colisiona(jugador.x, jugador.y, tamano):
                if delta > 0:
                    jugador.x = obstaculo.x - tamano
                else:
                    jugador.x = obstaculo.x + obstaculo.ancho

    def _mover_y(self, jugador: Jugador, delta: float) -> None:
        tamano = self.TAMANO_JUGADOR
        jugador.y = min(max(jugador.y + delta, 0), self.ALTO - tamano)
        for obstaculo in self._solidos:
            if obstaculo.colisiona(jugador.x, jugador.y, tamano):
                if delta > 0:
                    jugador.y = obstaculo.y - tamano
                else:
                    jugador.y = obstaculo.y + obstaculo.alto

    # Detiene a los jugadores al perderse la conexión del cliente.
    def detener_movimiento(self) -> None:
        with self._bloqueo:
            self._entradas = {nombre: (0, 0) for nombre in self._jugadores}
            self._operador_reactor = None
            # Un cliente nuevo empieza sus contadores desde cero.
            for jugador in self._jugadores.values():
                jugador.contadores = dict.fromkeys(ACCIONES, 0)

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
            "projectile_size": self.TAMANO_PROYECTIL,
            "players": {
                nombre: {
                    "x": jugador.x,
                    "y": jugador.y,
                    "dir_x": jugador.dir_x,
                    "dir_y": jugador.dir_y,
                    "interacting": jugador.tiempo_interaccion > 0,
                    "frozen": nombre == self._operador_reactor,
                    "score": jugador.puntos,
                }
                for nombre, jugador in self._jugadores.items()
            },
            "reactor": {
                "x": self._reactor.x,
                "y": self._reactor.y,
                "size": self._reactor.ancho,
                "ring_radius": self.RADIO_REACTOR,
                "operator": self._operador_reactor,
            },
            "projectiles": [{"x": p.x, "y": p.y} for p in self._proyectiles],
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

    # Lee los contadores acumulados de pulsaciones; son opcionales.
    @staticmethod
    def _leer_acciones(valor: dict[str, Any]) -> dict[str, int]:
        contadores = {accion: valor.get(accion, 0) for accion in ACCIONES}
        if any(
            isinstance(c, bool) or not isinstance(c, int) or c < 0
            for c in contadores.values()
        ):
            raise ValueError("Los contadores de acciones deben ser enteros no negativos.")
        return contadores
