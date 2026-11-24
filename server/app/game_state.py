"""Estado autoritativo y reglas de movimiento de la arena."""

import math
import random
import threading
from dataclasses import dataclass, field
from typing import Any

from app.game_config import CONFIGURACION_INICIAL, validar_configuracion
from app.guardianes import Guardian, TAMANO_GUARDIAN, guardianes_iniciales
from app.reglas import Reglas, cargar_reglas

ACCIONES = ("shoot", "interact")

PUESTOS = ("red", "blue")
ANFITRION = "red"
MAX_NOTIFICACIONES = 20
# Estados del reactor en state.reactor.status.
REACTOR_DISPONIBLE = "available"
REACTOR_EN_USO = "in_use"


class Rechazo(ValueError):
    """Solicitud rechazada: codigo estable para el cliente y motivo legible."""

    def __init__(self, codigo: str, motivo: str):
        super().__init__(motivo)
        self.codigo = codigo
        self.motivo = motivo

# PosiciÃ³n actual de un jugador dentro de la arena
@dataclass
class Jugador:
    x: float
    y: float
    # Vector unitario real; conserva la orientacion al detenerse.
    dir_x: float = 1.0
    dir_y: float = 0.0
    mov_x: float = 0.0
    mov_y: float = 0.0
    tiempo_interaccion: float = 0.0
    puntos: int = 0
    bloqueo_restante: float = 0.0
    lentitud_restante: float = 0.0
    aturdimiento_restante: float = 0.0
    trampa_actual: str | None = None
    trampas_ocupadas: set[str] = field(default_factory=set)
    # Ãšltimo contador de pulsaciones procesado por acciÃ³n.
    contadores: dict[str, int] = field(default_factory=lambda: dict.fromkeys(ACCIONES, 0))


@dataclass
class Proyectil:
    x: float
    y: float
    vx: float
    vy: float
    dueno: str


# RectÃ¡ngulo estÃ¡tico que bloquea el paso de los jugadores.
@dataclass(frozen=True)
class Obstaculo:
    x: float
    y: float
    ancho: float
    alto: float

    def colisiona(self, x: float, y: float, tamano: float) -> bool:
        # Tocar el borde no cuenta como colisiÃ³n, asÃ­ el jugador puede deslizarse.
        return (
            x < self.x + self.ancho
            and x + tamano > self.x
            and y < self.y + self.alto
            and y + tamano > self.y
        )


@dataclass(frozen=True)
class Puerta:
    id: str
    zona: Obstaculo


@dataclass(frozen=True)
class Trampa:
    id: str
    tipo: str
    zona: Obstaculo
    duracion: float

# ObstÃ¡culos iniciales en la arena.
MAPA_INICIAL = (
    Obstaculo(300, 250, 200, 40),
    Obstaculo(900, 150, 40, 300),
    Obstaculo(1200, 500, 250, 40),
    Obstaculo(400, 600, 40, 200),
)
PUERTAS_INICIALES = (Puerta("puerta_central", Obstaculo(600, 400, 40, 120)),)
TIPOS_TRAMPA = (("jaula", 2.5), ("arenas", 1.75), ("inversion", 1.25))

# Mantiene y actualiza las posiciones compartidas de ambos jugadores
class EstadoJuego:

    ANCHO = 1600                          # Ancho de la arena.
    ALTO = 900                            # Alto de la arena.
    TAMANO_JUGADOR = 40                   # TamaÃ±o del hitbox de los jugadores.
    VELOCIDAD = 240.0                     # Velocidad de los jugadores en unidades por segundo.
    TAMANO_PROYECTIL = 8                  # TamaÃ±o del hitbox de los proyectiles.
    VELOCIDAD_PROYECTIL = 900.0           # Velocidad de los proyectiles en unidades por segundo.
    DURACION_INTERACCION = 0.15           # DuraciÃ³n en segundos de la interacciÃ³n con el reactor.
    RADIO_REACTOR = 1.5 * TAMANO_JUGADOR  # Anillo de diÃ¡metro 3x el hitbox.
    VELOCIDAD_GIRO = math.radians(360)
    ZONA_MUERTA = 0.15
    RADIO_PUERTA = 90.0

    # Crea la arena con las posiciones iniciales de rojo y azul
    def __init__(
        self,
        obstaculos: tuple[Obstaculo, ...] = MAPA_INICIAL,
        reglas: Reglas | None = None,
        puertas: tuple[Puerta, ...] | None = None,
        trampas: tuple[Trampa, ...] | None = None,
        semilla: int | None = None,
        guardianes: tuple[Guardian, ...] | None = None,
    ):
        self._reglas = reglas if reglas is not None else cargar_reglas()

        self._configuracion = dict(CONFIGURACION_INICIAL)
        self._obstaculos = tuple(obstaculos)
        # Un mapa personalizado no recibe elementos del mapa inicial por sorpresa.
        self._puertas = tuple(PUERTAS_INICIALES if obstaculos is MAPA_INICIAL else ()) if puertas is None else tuple(puertas)
        self._trampas_fijas = None if trampas is None and obstaculos is MAPA_INICIAL else tuple(trampas or ())
        self._azar = random.Random(semilla)
        self._guardianes_configurados = (
            tuple(guardianes_iniciales(self.ANCHO, self.ALTO))
            if guardianes is None and obstaculos is MAPA_INICIAL
            else tuple(guardianes or ())
        )
        self._guardianes: list[Guardian] = []    
        self._puertas_abiertas: dict[str, bool] = {}
        self._trampas: tuple[Trampa, ...] = ()
        self._reactor = Obstaculo(
            (self.ANCHO - self.TAMANO_JUGADOR) / 2,
            (self.ALTO - self.TAMANO_JUGADOR) / 2,
            self.TAMANO_JUGADOR,
            self.TAMANO_JUGADOR,
        )
        # El reactor es sÃ³lido para jugadores y disparos.
        self._solidos = self._obstaculos + (self._reactor,)
        self._operador_reactor: str | None = None
        self._tiempo_reactor = 0.0
        # El bloqueo hace atÃ³micas las actualizaciones concurrentes recibidas
        # por los hilos que atienden conexiones TCP.
        self._bloqueo = threading.Lock()
        # Sala: usuario que ocupa cada puesto y si su conexion sigue abierta.
        self._puestos: dict[str, str | None] = dict.fromkeys(PUESTOS)
        self._conectados: dict[str, bool] = dict.fromkeys(PUESTOS, False)
        # Avisos para los clientes; el id crece siempre, aunque se vacie la lista.
        self._notificaciones: list[dict[str, Any]] = []
        self._ultimo_id_notificacion = 0
        self._jugadores: dict[str, Jugador] = {}
        self._reiniciar_estado()

    # Reinicia la partida a su estado inicial.
    def reiniciar_partida(self) -> None:
        with self._bloqueo:
            self._reiniciar_estado()

    def iniciar_partida(self, configuracion: Any) -> dict[str, Any]:
        with self._bloqueo:
            return self._iniciar_bloqueado(configuracion)

    # Arranca la partida; el llamador ya posee el bloqueo.
    def _iniciar_bloqueado(self, configuracion: Any) -> dict[str, Any]:
        configuracion = validar_configuracion(configuracion)
        self._configuracion = configuracion
        self._reiniciar_estado()
        if configuracion["condition"] == "time":
            self._limite_tiempo = configuracion["value"] * 60
        self._iniciada = True
        return self._crear_estado()

    # Asigna un puesto al usuario: red al primero (anfitrion) y blue al segundo.
    # Si el usuario ya tenia puesto (se desconecto en plena partida) lo recupera.
    def unir_jugador(self, usuario: Any) -> str:
        if not isinstance(usuario, str) or not usuario.strip():
            raise Rechazo("invalid_user", "El usuario no es válido.")
        usuario = usuario.strip()
        with self._bloqueo:
            for puesto, ocupante in self._puestos.items():
                if ocupante == usuario:
                    if self._conectados[puesto]:
                        raise Rechazo(
                            "already_connected",
                            "Esta cuenta ya está conectada a la partida.",
                        )
                    self._conectados[puesto] = True
                    self._reiniciar_contadores(puesto)
                    return puesto
            libre = next((p for p in PUESTOS if self._puestos[p] is None), None)
            if libre is None:
                raise Rechazo("room_full", "La sala ya tiene dos jugadores.")
            self._puestos[libre] = usuario
            self._conectados[libre] = True
            self._reiniciar_contadores(libre)
            return libre

    # Libera el puesto cuando se cierra la conexion de su cliente.
    # Antes de empezar (o al terminar) el puesto queda libre; en plena partida
    # se reserva para el mismo usuario. Si no queda nadie, la sala se vacia.
    def liberar_puesto(self, puesto: str) -> None:
        with self._bloqueo:
            if puesto not in self._puestos or not self._conectados[puesto]:
                return
            self._conectados[puesto] = False
            self._entradas[puesto] = (0, 0)
            jugador = self._jugadores[puesto]
            jugador.mov_x = jugador.mov_y = 0.0
            self._reiniciar_contadores(puesto)
            if self._operador_reactor == puesto:
                self._operador_reactor = None
            if not self._iniciada or self._terminada:
                self._puestos[puesto] = None
            if not any(self._conectados.values()):
                self._vaciar_sala()

    # Deja la sala como recien creada. El llamador ya posee el bloqueo.
    def _vaciar_sala(self) -> None:
        self._reiniciar_estado()
        for puesto in PUESTOS:
            self._reiniciar_contadores(puesto)
        self._puestos = dict.fromkeys(PUESTOS)
        self._conectados = dict.fromkeys(PUESTOS, False)
        self._notificaciones = []

    def _reiniciar_contadores(self, puesto: str) -> None:
        self._jugadores[puesto].contadores = dict.fromkeys(ACCIONES, 0)

    # Inicia la partida a peticion de un puesto. Solo la inicia el anfitrion,
    # con los dos jugadores conectados y sin otra partida en curso.
    def iniciar_por(self, puesto: str, configuracion: Any) -> dict[str, Any]:
        with self._bloqueo:
            if puesto != ANFITRION:
                raise Rechazo("not_host", "Solo el anfitrión puede iniciar la partida.")
            if self._iniciada and not self._terminada:
                raise Rechazo("match_in_progress", "La partida ya está en curso.")
            if not all(self._conectados.values()):
                raise Rechazo(
                    "waiting_for_players", "Falta que se conecte el otro jugador."
                )
            return self._iniciar_bloqueado(configuracion)

    # Registra un rechazo para un puesto en state.notifications y devuelve el estado.
    def rechazar(self, puesto: str, codigo: str, motivo: str) -> dict[str, Any]:
        with self._bloqueo:
            self._rechazar(puesto, codigo, motivo)
            return self._crear_estado()
    #Anota un rechazo dirigido a un puesto. El llamador ya posee el bloqueo.
    def _rechazar(self, puesto: str, codigo: str, motivo: str) -> None:
        self._agregar_notificacion("reject", motivo, "warning", puesto, codigo)

    # Id de la ultima notificacion emitida (0 si aun no hay ninguna).
    def ultima_notificacion(self) -> int:
        with self._bloqueo:
            return self._ultimo_id_notificacion

    # Agrega un aviso con id creciente. El llamador ya posee el bloqueo.
    def _agregar_notificacion(
        self,
        tipo: str,
        mensaje: str,
        severidad: str,
        para: str | None = None,
        codigo: str | None = None,
    ) -> None:
        self._ultimo_id_notificacion += 1
        notificacion: dict[str, Any] = {
            "id": self._ultimo_id_notificacion,
            "kind": tipo,
            "message": mensaje,
            "severity": severidad,
            "for": para,
        }
        if codigo is not None:
            notificacion["code"] = codigo
        self._notificaciones.append(notificacion)
        del self._notificaciones[:-MAX_NOTIFICACIONES]

    # Inicializa o reinicia el estado interno del juego. No debe llamarse directamente desde fuera de la clase.
    def _reiniciar_estado(self) -> None:
        self._iniciada = False
        self._terminada = False
        self._ganador = None
        self._tiempo_partida = 0.0
        self._prorrogas = 0
        self._limite_tiempo = None
        self._operador_reactor = None
        self._tiempo_reactor = 0.0
        self._puertas_abiertas = {puerta.id: False for puerta in self._puertas}
        self._trampas = self._generar_trampas() if self._trampas_fijas is None else self._trampas_fijas
        self._guardianes = [Guardian(g.id, g.x, g.y) for g in self._guardianes_configurados]
        anteriores = self._jugadores
        self._jugadores = {
            "red": Jugador(100, 100, dir_x=1.0),
            "blue": Jugador(
                self.ANCHO - self.TAMANO_JUGADOR - 100,
                self.ALTO - self.TAMANO_JUGADOR - 100,
                dir_x=-1.0,
            ),
        }
        # Los contadores acumulados pertenecen a la conexion, no a la partida:
        # si se reiniciaran, la ultima pulsacion de un cliente se repetiria.
        for nombre, jugador in self._jugadores.items():
            if nombre in anteriores:
                jugador.contadores = dict(anteriores[nombre].contadores)
        self._proyectiles: list[Proyectil] = []
        # El servidor conserva la Ãºltima direcciÃ³n recibida y simula el
        # movimiento a una frecuencia fija, independiente de los paquetes.
        self._entradas = {
            "red": (0, 0),
            "blue": (0, 0),
        }

    def _generar_trampas(self) -> tuple[Trampa, ...]:
        """Elige tres celdas libres y alejadas de los puntos de aparición."""
        candidatos = []
        for y in range(160, 761, 100):
            for x in range(200, 1401, 100):
                zona = Obstaculo(x, y, 64, 64)
                centro = (x + 32, y + 32)
                if any(
                    Obstaculo(solido.x - 40, solido.y - 40,
                              solido.ancho + 80, solido.alto + 80).colisiona(x, y, 64)
                    for solido in self._solidos + tuple(p.zona for p in self._puertas)
                ):
                    continue
                if math.dist(centro, (800, 450)) < 155:
                    continue
                if any(math.dist(centro, aparicion) < 170 for aparicion in ((120, 120), (1480, 780))):
                    continue
                candidatos.append(zona)
        if len(candidatos) < len(TIPOS_TRAMPA):
            raise ValueError("El mapa no tiene espacio para tres trampas.")
        zonas = self._azar.sample(candidatos, len(TIPOS_TRAMPA))
        return tuple(
            Trampa(f"trampa_{tipo}", tipo, zona, duracion)
            for (tipo, duracion), zona in zip(TIPOS_TRAMPA, zonas)
        )

    def _solidos_actuales(self) -> tuple[Obstaculo, ...]:
        return self._solidos + tuple(
            puerta.zona for puerta in self._puertas
            if not self._puertas_abiertas[puerta.id]
        )

    def _activar_trampas(self, jugador: Jugador) -> None:
        ocupadas = {
            trampa.id for trampa in self._trampas
            if trampa.zona.colisiona(jugador.x, jugador.y, self.TAMANO_JUGADOR)
        }
        nuevas = ocupadas - jugador.trampas_ocupadas
        jugador.trampas_ocupadas = ocupadas
        if jugador.bloqueo_restante > 0:
            return
        for trampa in self._trampas:
            if trampa.id in nuevas:
                jugador.bloqueo_restante = trampa.duracion
                jugador.trampa_actual = trampa.tipo
                if trampa.tipo == "arenas":
                    jugador.lentitud_restante = trampa.duracion + 2.0
                if self._operador_reactor is not None:
                    for nombre, candidato in self._jugadores.items():
                        if candidato is jugador and self._operador_reactor == nombre:
                            self._operador_reactor = None
                            break
                break

    def _iniciar_prorroga(self) -> None:
        puntos = {
            nombre: jugador.puntos
            for nombre, jugador in self._jugadores.items()
        }

        tiempo = self._tiempo_partida
        prorrogas = self._prorrogas + 1

        self._reiniciar_estado()

        for nombre, puntaje in puntos.items():
            self._jugadores[nombre].puntos = puntaje

        self._tiempo_partida = tiempo
        self._prorrogas = prorrogas
        self._limite_tiempo = tiempo + 120
        self._iniciada = True

    # Valida y aplica la entrada de UN puesto (la de su propia conexion).
    # No inicia la partida: fuera de una partida activa solo sincroniza los
    # contadores para que una pulsacion vieja no se ejecute al empezar.
    def aplicar_entrada(self, puesto: str, entrada: Any) -> dict[str, Any]:
        if puesto not in self._jugadores:
            raise Rechazo("not_joined", "No tienes un puesto en la partida.")
        direccion = self._leer_direccion(entrada)
        acciones = self._leer_acciones(entrada)
        with self._bloqueo:
            self._aplicar_entrada(puesto, direccion, acciones)
            return self._crear_estado()

    # Valida y aplica las entradas de ambos puestos a la vez (pruebas y bots locales).
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
            for nombre in self._jugadores:
                self._aplicar_entrada(nombre, direcciones[nombre], acciones[nombre])
            return self._crear_estado()

    # Aplica una entrada ya validada. El llamador ya posee el bloqueo.
    def _aplicar_entrada(
        self,
        nombre: str,
        direccion: tuple[float, float],
        acciones: dict[str, int],
    ) -> None:
        jugador = self._jugadores[nombre]
        activa = self._iniciada and not self._terminada
        if activa:
            dx, dy = direccion
            self._entradas[nombre] = direccion
            magnitud = math.hypot(dx, dy)
            jugador.mov_x = dx / magnitud if magnitud else 0.0
            jugador.mov_y = dy / magnitud if magnitud else 0.0
        # Los contadores son acumulativos y un valor menor o igual al ultimo
        # procesado es una repeticion: se ignora (CA-18.8).
        for accion, contador in acciones.items():
            if contador > jugador.contadores[accion]:
                jugador.contadores[accion] = contador
                if activa:
                    self._ejecutar_accion(nombre, accion)
                elif accion == "interact":
                    self._rechazar(nombre, "match_not_active", "La partida no está activa.")

    # Ejecuta la acciÃ³n correspondiente a un jugador, como interactuar con el reactor o disparar.
    def _ejecutar_accion(self, nombre: str, accion: str) -> None:
        jugador = self._jugadores[nombre]
        if jugador.aturdimiento_restante > 0:
            self._rechazar(nombre, "player_stunned", "No puedes actuar mientras estás aturdido.")
            return        
        if jugador.bloqueo_restante > 0:
            self._rechazar(nombre, "player_trapped", "No puedes actuar mientras estás atrapado.")
            return
        if accion == "interact":
            puerta = self._puerta_cercana(jugador)
            if puerta is not None:
                if self._puertas_abiertas[puerta.id] and any(
                    puerta.zona.colisiona(otro.x, otro.y, self.TAMANO_JUGADOR)
                    for otro in self._jugadores.values()
                ):
                    self._rechazar(nombre, "door_occupied", "La puerta no puede cerrarse sobre un jugador.")
                    return
                self._puertas_abiertas[puerta.id] = not self._puertas_abiertas[puerta.id]
                return
            if self._operador_reactor == nombre:
                self._operador_reactor = None
            elif self._operador_reactor is not None:
                self._rechazar(
                    nombre, "reactor_busy", "El otro jugador está usando el reactor."
                )
            elif not self._en_rango_reactor(jugador):
                self._rechazar(
                    nombre,
                    "out_of_range",
                    "Estás fuera de la zona del reactor. Acércate para extraer energía.",
                )
            else:
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

    def _puerta_cercana(self, jugador: Jugador) -> Puerta | None:
        centro = (jugador.x + self.TAMANO_JUGADOR / 2,
                  jugador.y + self.TAMANO_JUGADOR / 2)
        cercanas = [
            puerta for puerta in self._puertas
            if math.dist(centro, (puerta.zona.x + puerta.zona.ancho / 2,
                                  puerta.zona.y + puerta.zona.alto / 2)) <= self.RADIO_PUERTA
        ]
        return min(cercanas, key=lambda p: math.dist(
            centro, (p.zona.x + p.zona.ancho / 2, p.zona.y + p.zona.alto / 2)
        )) if cercanas else None

    # Verifica si un jugador estÃ¡ dentro del rango de interacciÃ³n con el reactor.
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
            raise ValueError("delta_t debe ser un nÃºmero no negativo.")

    # Simula el avance del juego durante un intervalo de tiempo delta_t, actualizando posiciones, proyectiles y el estado del reactor.
        with self._bloqueo:
            if not self._iniciada or self._terminada:
                return self._crear_estado()
            condicion = self._configuracion["condition"]
            limite = self._configuracion["value"]
            if condicion == "time" or self._prorrogas > 0:
                delta_t = min(
                    delta_t,
                    max(0.0, self._limite_tiempo - self._tiempo_partida)
                )
            elif self._operador_reactor is not None:
                # Extracciones que faltan para que el operador llegue al objetivo.
                restantes = limite - self._jugadores[self._operador_reactor].puntos
                faltan = math.ceil(max(0, restantes) / self._reglas.puntos_por_energia)
                delta_t = min(
                    delta_t,
                    max(0.0, faltan * self._reglas.intervalo_extraccion - self._tiempo_reactor),
                )
            self._tiempo_partida += delta_t
            for nombre, (dx, dy) in self._entradas.items():
                jugador = self._jugadores[nombre]
                tiempo_bloqueado = min(delta_t, jugador.bloqueo_restante)
                tiempo_lento = jugador.lentitud_restante
                jugador.bloqueo_restante = max(0.0, jugador.bloqueo_restante - delta_t)
                jugador.aturdimiento_restante = max(0.0, jugador.aturdimiento_restante - delta_t)               
                jugador.lentitud_restante = max(0.0, jugador.lentitud_restante - delta_t)
                if jugador.bloqueo_restante == 0:
                    jugador.trampa_actual = None
                if nombre != self._operador_reactor:
                    intensidad = math.hypot(dx, dy) * (0.5 if tiempo_lento > 0 else 1.0)
                    self._mover_girando(jugador, intensidad, delta_t - tiempo_bloqueado)
                self._activar_trampas(jugador)
            self._avanzar_guardianes(delta_t)
            for jugador in self._jugadores.values():
                jugador.tiempo_interaccion = max(0.0, jugador.tiempo_interaccion - delta_t)
            if self._operador_reactor is not None:
                self._tiempo_reactor += delta_t
                intervalo = self._reglas.intervalo_extraccion
                extracciones = math.floor((self._tiempo_reactor + 1e-9) / intervalo)
                self._tiempo_reactor = max(0.0, self._tiempo_reactor - extracciones * intervalo)
                # Unica fuente de puntos: extraer energia del reactor.
                self._jugadores[self._operador_reactor].puntos += (
                    extracciones * self._reglas.puntos_por_energia
                )
            self._proyectiles = [
                p for p in self._proyectiles if self._mover_proyectil(p, delta_t)
            ]
            limite_alcanzado = (
                self._tiempo_partida + 1e-9 >= self._limite_tiempo
                if condicion == "time" or self._prorrogas > 0
                else any(
                    jugador.puntos >= limite
                    for jugador in self._jugadores.values()
                )
            )

            if limite_alcanzado:
                rojo = self._jugadores["red"].puntos
                azul = self._jugadores["blue"].puntos

                if rojo > azul:
                    self._ganador = "red"
                    self._terminada = True
                elif azul > rojo:
                    self._ganador = "blue"
                    self._terminada = True
                else:
                    self._iniciar_prorroga()

            return self._crear_estado()

    def _mover_girando(self, jugador: Jugador, intensidad: float, delta_t: float) -> None:
        if not intensidad or not delta_t:
            return
        angulo = math.atan2(jugador.dir_y, jugador.dir_x)
        objetivo = math.atan2(jugador.mov_y, jugador.mov_x)
        diferencia = (objetivo - angulo + math.pi) % math.tau - math.pi
        velocidad = self.VELOCIDAD * min(intensidad, 1.0)
        if abs(diferencia) < 1e-9:
            jugador.dir_x, jugador.dir_y = jugador.mov_x, jugador.mov_y
            self._mover_recto(jugador, velocidad * delta_t)
            return
        velocidad_angular = math.copysign(self.VELOCIDAD_GIRO, diferencia)
        duracion = min(delta_t, abs(diferencia) / self.VELOCIDAD_GIRO)
        pasos = max(
            1, math.ceil(duracion * 120),
            math.ceil(velocidad * duracion / (self.TAMANO_JUGADOR / 2)),
        )
        paso_t = duracion / pasos
        for _ in range(pasos):
            if jugador.bloqueo_restante > 0:
                break
            siguiente = angulo + velocidad_angular * paso_t
            paso_x = velocidad * (math.sin(siguiente) - math.sin(angulo)) / velocidad_angular
            paso_y = velocidad * (math.cos(angulo) - math.cos(siguiente)) / velocidad_angular
            self._mover_x(jugador, paso_x)
            self._mover_y(jugador, paso_y)
            angulo = siguiente
        if jugador.bloqueo_restante > 0:
            jugador.dir_x, jugador.dir_y = math.cos(angulo), math.sin(angulo)
            return
        if abs(diferencia) <= self.VELOCIDAD_GIRO * delta_t + 1e-9:
            jugador.dir_x, jugador.dir_y = jugador.mov_x, jugador.mov_y
        else:
            jugador.dir_x, jugador.dir_y = math.cos(angulo), math.sin(angulo)
        self._mover_recto(jugador, velocidad * max(0.0, delta_t - duracion))

    def _mover_recto(self, jugador: Jugador, distancia: float) -> None:
        if distancia <= 0 or jugador.bloqueo_restante > 0:
            return
        pasos = max(1, math.ceil(distancia / (self.TAMANO_JUGADOR / 2)))
        for _ in range(pasos):
            if jugador.bloqueo_restante > 0:
                break
            self._mover_x(jugador, jugador.dir_x * distancia / pasos)
            self._mover_y(jugador, jugador.dir_y * distancia / pasos)

    def _avanzar_guardianes(self, delta_t: float) -> None:
        """Persiguen al jugador libre más cercano y aturden al tocar un avatar."""
        tamano = TAMANO_GUARDIAN
        velocidad = self._reglas.velocidad_guardian
        pasos = max(1, math.ceil(velocidad * delta_t / (tamano / 2)))
        paso_t = delta_t / pasos
        for guardian in self._guardianes:
            for _ in range(pasos):
                elegibles = [
                    (nombre, jugador) for nombre, jugador in self._jugadores.items()
                    if jugador.bloqueo_restante <= 0
                ]
                if elegibles:
                    nombre, objetivo = min(
                        elegibles,
                        key=lambda par: math.dist(
                            (guardian.x, guardian.y), (par[1].x, par[1].y)
                        ),
                    )
                    guardian.objetivo = nombre
                    dx = objetivo.x - guardian.x
                    dy = objetivo.y - guardian.y
                    distancia = math.hypot(dx, dy)
                    if distancia > 0 and paso_t > 0:
                        avance = min(velocidad * paso_t, distancia)
                        siguiente_x = min(max(guardian.x + dx / distancia * avance, 0), self.ANCHO - tamano)
                        if not any(o.colisiona(siguiente_x, guardian.y, tamano)
                                   for o in self._solidos_actuales()):
                            guardian.x = siguiente_x
                        siguiente_y = min(max(guardian.y + dy / distancia * avance, 0), self.ALTO - tamano)
                        if not any(o.colisiona(guardian.x, siguiente_y, tamano)
                                   for o in self._solidos_actuales()):
                            guardian.y = siguiente_y
                else:
                    guardian.objetivo = None

                contactos = {
                    nombre for nombre, jugador in self._jugadores.items()
                    if Obstaculo(jugador.x, jugador.y, self.TAMANO_JUGADOR,
                                 self.TAMANO_JUGADOR).colisiona(guardian.x, guardian.y, tamano)
                }
                for nombre in contactos - guardian.contactos:
                    jugador = self._jugadores[nombre]
                    jugador.bloqueo_restante += self._reglas.duracion_aturdimiento
                    jugador.aturdimiento_restante = jugador.bloqueo_restante
                    if self._operador_reactor == nombre:
                        self._operador_reactor = None
                        self._tiempo_reactor = 0.0
                    self._agregar_notificacion(
                        "guardian_hit", f"{nombre} fue aturdido por un guardián.",
                        "danger", codigo="guardian_hit"
                    )
                guardian.contactos = contactos

    # Avanza un proyectil y devuelve False si chocÃ³ con algo o saliÃ³ del mapa.
    def _mover_proyectil(self, proyectil: Proyectil, delta_t: float) -> bool:
        tamano = self.TAMANO_PROYECTIL
        distancia = math.hypot(proyectil.vx, proyectil.vy) * delta_t
        # Subpasos del tamaÃ±o del proyectil para no atravesar paredes.
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
            if any(o.colisiona(proyectil.x, proyectil.y, tamano) for o in self._solidos_actuales()):
                return False
            for nombre, jugador in self._jugadores.items():
                if nombre != proyectil.dueno and Obstaculo(
                    jugador.x, jugador.y, self.TAMANO_JUGADOR, self.TAMANO_JUGADOR
                ).colisiona(proyectil.x, proyectil.y, tamano):
                    return False
        return True

    # Mueve al jugador en la direcciÃ³n x, manejando colisiones con los lÃ­mites del mapa y obstÃ¡culos sÃ³lidos.
    def _mover_x(self, jugador: Jugador, delta: float) -> None:
        if jugador.bloqueo_restante > 0:
            return
        tamano = self.TAMANO_JUGADOR
        jugador.x = min(max(jugador.x + delta, 0), self.ANCHO - tamano)
        for obstaculo in self._solidos_actuales():
            if obstaculo.colisiona(jugador.x, jugador.y, tamano):
                if delta > 0:
                    jugador.x = obstaculo.x - tamano
                else:
                    jugador.x = obstaculo.x + obstaculo.ancho
        self._activar_trampas(jugador)

    # Mueve al jugador en la direcciÃ³n y, manejando colisiones con los lÃ­mites del mapa y obstÃ¡culos sÃ³lidos.
    def _mover_y(self, jugador: Jugador, delta: float) -> None:
        if jugador.bloqueo_restante > 0:
            return
        tamano = self.TAMANO_JUGADOR
        jugador.y = min(max(jugador.y + delta, 0), self.ALTO - tamano)
        for obstaculo in self._solidos_actuales():
            if obstaculo.colisiona(jugador.x, jugador.y, tamano):
                if delta > 0:
                    jugador.y = obstaculo.y - tamano
                else:
                    jugador.y = obstaculo.y + obstaculo.alto
        self._activar_trampas(jugador)

    # Detiene a los jugadores al perderse la conexiÃ³n del cliente, reiniciando sus entradas y contadores.
    def detener_movimiento(self) -> None:
        with self._bloqueo:
            self._entradas = {nombre: (0, 0) for nombre in self._jugadores}
            self._operador_reactor = None
            # Un cliente nuevo empieza sus contadores desde cero.
            for jugador in self._jugadores.values():
                jugador.contadores = dict.fromkeys(ACCIONES, 0)
                jugador.mov_x = jugador.mov_y = 0.0

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
            "match": {
                "started": self._iniciada,        # nuevo
                "finished": self._terminada,
                "elapsed": self._tiempo_partida,
                "condition": self._configuracion["condition"],
                "value": self._configuracion["value"],
                "winner": self._ganador,
                "time_limit": self._limite_tiempo,
                "overtime": self._prorrogas,
            },
            "players": {
                nombre: {
                    "x": jugador.x,
                    "y": jugador.y,
                    "dir_x": jugador.dir_x,
                    "dir_y": jugador.dir_y,
                    "move_x": jugador.mov_x,
                    "move_y": jugador.mov_y,
                    "interacting": jugador.tiempo_interaccion > 0,
                    "frozen": jugador.bloqueo_restante > 0,
                    "status": "stunned" if jugador.aturdimiento_restante > 0 else (
                        "frozen" if jugador.bloqueo_restante > 0 else "normal"
                    ),
                    "stun_remaining": jugador.aturdimiento_restante,
                    "trap": jugador.trampa_actual,
                    "trap_remaining": jugador.bloqueo_restante,
                    "inverted": jugador.trampa_actual == "inversion",
                    "slowed": jugador.lentitud_restante > 0 and jugador.bloqueo_restante == 0,
                    "slow_remaining": max(0.0, jugador.lentitud_restante - jugador.bloqueo_restante),
                    "extracting": nombre == self._operador_reactor,
                    "score": jugador.puntos,
                    "username": self._puestos[nombre],     # nuevo
                    "connected": self._conectados[nombre], # nuevo
                }
                for nombre, jugador in self._jugadores.items()
            },
            "reactor": {
                "x": self._reactor.x,
                "y": self._reactor.y,
                "size": self._reactor.ancho,
                "ring_radius": self.RADIO_REACTOR,
                "operator": self._operador_reactor,
                "status": (
                    REACTOR_DISPONIBLE
                    if self._operador_reactor is None
                    else REACTOR_EN_USO
                ),
            },
            "projectiles": [{"x": p.x, "y": p.y} for p in self._proyectiles],
            "obstacles": [
                {"x": o.x, "y": o.y, "width": o.ancho, "height": o.alto}
                for o in self._obstaculos],
            "doors": [
                {"id": p.id, "x": p.zona.x, "y": p.zona.y,
                 "width": p.zona.ancho, "height": p.zona.alto,
                 "open": self._puertas_abiertas[p.id]}
                for p in self._puertas
            ],
            "traps": [
                {"id": t.id, "type": t.tipo, "x": t.zona.x, "y": t.zona.y,
                 "width": t.zona.ancho, "height": t.zona.alto,
                 "duration": t.duracion}
                for t in self._trampas
            ],
            "guardians": [
                {"id": g.id, "x": g.x, "y": g.y, "size": TAMANO_GUARDIAN,
                 "target": g.objetivo}
                for g in self._guardianes
            ],
            "notifications": list(self._notificaciones),   # nuevo
        }

    # Valida entradas digitales o analogicas y descarta el ruido del stick.
    @staticmethod
    def _leer_direccion(valor: Any) -> tuple[float, float]:
        if not isinstance(valor, dict):
            raise ValueError("Falta la entrada de un jugador.")
        dx = valor.get("x")
        dy = valor.get("y")
        if any(
            isinstance(eje, bool)
            or not isinstance(eje, (int, float))
            or not math.isfinite(eje)
            or not -1 <= eje <= 1
            for eje in (dx, dy)
        ):
            raise ValueError("Cada eje debe ser un numero finito entre -1 y 1.")
        if math.hypot(dx, dy) <= EstadoJuego.ZONA_MUERTA:
            return 0.0, 0.0
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
