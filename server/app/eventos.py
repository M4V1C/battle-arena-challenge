"""Calendario reproducible de eventos de una partida."""

from dataclasses import dataclass
from random import Random


@dataclass
class Evento:
    id: str
    tipo: str
    inicio: float
    duracion: float
    estado: str = "scheduled"
    fin_real: float | None = None

    @property
    def fin(self) -> float:
        return self.inicio + self.duracion


def programar_eventos(horizonte: float, azar: Random) -> list[Evento]:
    """Tres energías, cinco guardianes, 2-3 sobrecargas y dos eventos creativos."""
    def duracion(fraccion: float, maximo: float) -> float:
        return min(maximo, max(0.05, horizonte * fraccion))

    eventos = [
        Evento(f"energia_{n}", "energy", horizonte * fraccion,
               duracion(0.08, 5.0))
        for n, fraccion in enumerate((0.08, 0.32, 0.58), 1)
    ]
    eventos.append(Evento("guardianes_extra", "extra_guardians", horizonte * 0.22,
                          duracion(0.20, 10.0)))
    ventanas = ((0.12, 0.18), (0.52, 0.58))
    if azar.choice((False, True)):
        ventanas += ((0.78, 0.84),)
    for n, (inicio, fin) in enumerate(ventanas, 1):
        eventos.append(Evento(f"sobrecarga_{n}", "overload",
                              max(n * 0.6, horizonte * azar.uniform(inicio, fin)),
                              duracion(0.08, 4.0)))
    eventos.extend((
        Evento("impulso", "speed_boost", horizonte * 0.40,
               duracion(0.12, 5.0)),
        Evento("tregua", "guardian_truce", horizonte * 0.70,
               duracion(0.12, 5.0)),
    ))
    return sorted(eventos, key=lambda e: (e.inicio, e.id))
