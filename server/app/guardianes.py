"""Estado de los guardianes; el servidor decide sus objetivos y contactos."""

from dataclasses import dataclass, field

TAMANO_GUARDIAN = 40


@dataclass
class Guardian:
    id: str
    x: float
    y: float
    objetivo: str | None = None
    contactos: set[str] = field(default_factory=set)


def guardianes_iniciales(ancho: int, alto: int) -> list[Guardian]:
    """Cuatro extremos, dentro de los límites y lejos de las apariciones."""
    margen = 20
    extremo_x = ancho - TAMANO_GUARDIAN - margen
    extremo_y = alto - TAMANO_GUARDIAN - margen
    return [
        Guardian("noroeste", margen, margen),
        Guardian("noreste", extremo_x, margen),
        Guardian("suroeste", margen, extremo_y),
        Guardian("sureste", extremo_x, extremo_y),
    ]