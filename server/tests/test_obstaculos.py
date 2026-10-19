import pytest

from app.game_state import MAPA_INICIAL, EstadoJuego, Obstaculo


def mover_rojo(juego: EstadoJuego, x: int, y: int, segundos: float = 2.0) -> dict:
    juego.actualizar_entradas({"red": {"x": x, "y": y}, "blue": {"x": 0, "y": 0}})
    for _ in range(int(segundos * 60)):
        juego.avanzar(1 / 60)
    jugador = juego.estado()["players"]["red"]
    return {"x": jugador["x"], "y": jugador["y"]}


@pytest.mark.parametrize(
    ("dx", "dy", "obstaculo", "esperado"),
    [
        (1, 0, Obstaculo(200, 80, 40, 80), {"x": 160, "y": 100}),
        (-1, 0, Obstaculo(20, 80, 40, 80), {"x": 60, "y": 100}),
        (0, 1, Obstaculo(80, 200, 80, 40), {"x": 100, "y": 160}),
        (0, -1, Obstaculo(80, 20, 80, 40), {"x": 100, "y": 60}),
    ],
)
def test_obstaculo_detiene_el_movimiento(dx, dy, obstaculo, esperado):
    """El hitbox del obstáculo detiene al jugador en su borde por cualquier lado."""
    juego = EstadoJuego(obstaculos=(obstaculo,))

    assert mover_rojo(juego, dx, dy) == pytest.approx(esperado)


def test_jugador_se_desliza_por_la_pared_en_diagonal():
    """Al chocar en diagonal se bloquea un eje y el otro sigue avanzando."""
    juego = EstadoJuego(obstaculos=(Obstaculo(200, 0, 40, 900),))

    posicion = mover_rojo(juego, 1, 1, segundos=1.0)

    assert posicion["x"] == pytest.approx(160)
    assert posicion["y"] > 200


def test_delta_grande_no_atraviesa_obstaculos_delgados():
    """Un salto de tiempo grande no permite cruzar una pared delgada."""
    juego = EstadoJuego(obstaculos=(Obstaculo(300, 0, 5, 900),))
    juego.actualizar_entradas({"red": {"x": 1, "y": 0}, "blue": {"x": 0, "y": 0}})

    juego.avanzar(5.0)

    assert juego.estado()["players"]["red"]["x"] == pytest.approx(260)


def test_estado_incluye_obstaculos():
    """El cliente recibe los obstáculos para dibujar el mapa."""
    estado = EstadoJuego(obstaculos=(Obstaculo(10, 20, 30, 40),)).estado()

    assert estado["obstacles"] == [{"x": 10, "y": 20, "width": 30, "height": 40}]


def test_mapa_inicial_no_atrapa_a_los_jugadores():
    """Las posiciones iniciales no se solapan con el mapa por defecto."""
    juego = EstadoJuego()
    tamano = EstadoJuego.TAMANO_JUGADOR

    for jugador in juego.estado()["players"].values():
        assert not any(
            o.colisiona(jugador["x"], jugador["y"], tamano) for o in MAPA_INICIAL
        )
