from app.game_state import EstadoJuego


def partida_iniciada(**kwargs) -> EstadoJuego:
    """Juego con la partida ya iniciada: las entradas solo mueven en una partida en curso."""
    juego = EstadoJuego(**kwargs)
    juego.iniciar_partida({"condition": "points", "value": 20})
    return juego

