import json
import shutil
import subprocess
from pathlib import Path

from app.game_state import EstadoJuego

NODE = shutil.which("node")
WEB_DIR = Path(__file__).resolve().parents[1] / "web"
ARNES_WEB = Path(__file__).with_name("webapp_harness.js")


def partida_iniciada(**kwargs) -> EstadoJuego:
    """Juego con la partida ya iniciada: las entradas solo mueven en una partida en curso."""
    juego = EstadoJuego(**kwargs)
    juego.iniciar_partida({"condition": "points", "value": 20})
    return juego


def abrir_webapp(escenario: str) -> dict:
    """Ejecuta app.js con Node, un DOM y un fetch simulados; devuelve el estado visible."""
    salida = subprocess.run(
        [NODE, str(ARNES_WEB), str(WEB_DIR / "app.js"), str(WEB_DIR / "index.html"), escenario],
        capture_output=True, text=True, encoding="utf-8", timeout=30, check=True,
    )
    return json.loads(salida.stdout)

