
import pygame

from scenario_selection import ESCENARIOS, SelectorEscenarios


def test_existen_dos_escenarios():
    assert len(ESCENARIOS) >= 2
    assert len({escenario.id for escenario in ESCENARIOS}) == len(ESCENARIOS)


def test_escenario_inicial():
    selector = SelectorEscenarios()

    assert selector.seleccionado == "arena_clasica"


def test_seleccionar_laberinto():
    selector = SelectorEscenarios()
    tarjetas = selector.tarjetas(1600, 900)

    rectangulo_laberinto = tarjetas[1][0]

    evento = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        {
            "button": 1,
            "pos": rectangulo_laberinto.center,
        },
    )

    assert selector.procesar_evento(evento, 1600, 900)
    assert selector.seleccionado == "laberinto"


def test_clic_fuera_de_tarjetas():
    selector = SelectorEscenarios()

    evento = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        {
            "button": 1,
            "pos": (0, 0),
        },
    )

    assert not selector.procesar_evento(evento, 1600, 900)
    assert selector.seleccionado == "arena_clasica"


def test_evento_que_no_es_clic():
    selector = SelectorEscenarios()

    evento = pygame.event.Event(
        pygame.KEYDOWN,
        {"key": pygame.K_SPACE},
    )

    assert not selector.procesar_evento(evento, 1600, 900)
    assert selector.seleccionado == "arena_clasica"
