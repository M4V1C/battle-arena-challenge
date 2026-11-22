
from game import (
    Juego,
    COLOR_NORMAL,
    COLOR_INMOVILIZADO,
    COLOR_EXTRAYENDO,
)


def test_jugador_normal():
    texto, color = Juego._obtener_estado_jugador({
        "frozen": False,
        "interacting": False,
    })

    assert texto == "Normal"
    assert color == COLOR_NORMAL


def test_jugador_inmovilizado():
    texto, color = Juego._obtener_estado_jugador({
        "frozen": True,
        "interacting": False,
    })

    assert texto == "Inmovilizado"
    assert color == COLOR_INMOVILIZADO


def test_jugador_extrayendo():
    texto, color = Juego._obtener_estado_jugador({
        "frozen": False,
        "extracting": True,
    })

    assert texto == "Extrayendo energia"
    assert color == COLOR_EXTRAYENDO

def test_jugador_interactuando():
    texto, color = Juego._obtener_estado_jugador({
        "frozen": False,
        "interacting": True,
    })

    assert texto == "Interactuando"
    assert color == COLOR_EXTRAYENDO

def test_inmovilizacion_tiene_prioridad():
    texto, _ = Juego._obtener_estado_jugador({
        "frozen": True,
        "interacting": True,
    })

    assert texto == "Inmovilizado"


def test_reactor_sin_operador():
    juego = Juego.__new__(Juego)
    juego._nombres = {"red": "Gaby", "blue": "Carlos"}

    texto, _ = juego._obtener_estado_reactor({
        "operator": None,
    })

    assert texto == "Sin operador"


def test_reactor_operado_por_primer_usuario():
    juego = Juego.__new__(Juego)
    juego._nombres = {"red": "Gaby", "blue": "Carlos"}

    texto, _ = juego._obtener_estado_reactor({
        "operator": "red",
    })

    assert texto == "Operado por Gaby"


def test_reactor_operado_por_segundo_usuario():
    juego = Juego.__new__(Juego)
    juego._nombres = {"red": "Gaby", "blue": "Carlos"}

    texto, _ = juego._obtener_estado_reactor({
        "operator": "blue",
    })

    assert texto == "Operado por Carlos"


def test_reactor_estado_desconocido():
    juego = Juego.__new__(Juego)
    juego._nombres = {"red": "Gaby", "blue": "Carlos"}

    texto, _ = juego._obtener_estado_reactor({
        "operator": "otro",
    })

    assert texto == "Estado desconocido"

def test_partida_en_espera():
    texto, _ = Juego._obtener_estado_partida({
        "started": False,
        "finished": False,
    })
    assert texto == "EN ESPERA"


def test_partida_activa():
    texto, _ = Juego._obtener_estado_partida({
        "started": True,
        "finished": False,
        "overtime": 0,
    })
    assert texto == "EN PARTIDA"


def test_partida_en_prorroga():
    texto, _ = Juego._obtener_estado_partida({
        "started": True,
        "finished": False,
        "overtime": 1,
    })
    assert texto == "PRORROGA"


def test_partida_finalizada():
    texto, _ = Juego._obtener_estado_partida({
        "started": True,
        "finished": True,
        "overtime": 1,
    })
    assert texto == "FINALIZADA"