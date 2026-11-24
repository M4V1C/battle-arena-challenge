import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from victory_screen import PantallaVictoria

APP_WEB = Path(__file__).resolve().parents[1] / "server" / "web" / "app.js"
# Duraciones reales (con error de coma flotante) y casos límite del redondeo.
DURACIONES = [0, 0.4, 0.5, 59.4, 59.5, 59.99999999999764, 60, 119.5, 3599.6]


def crear_estado(ganador="red", duracion=332, prorrogas=0):
    return {
        "match": {
            "finished": True,
            "winner": ganador,
            "elapsed": duracion,
            "condition": "points",
            "value": 20,
            "overtime": prorrogas,
        },
        "players": {
            "red": {"score": 20},
            "blue": {"score": 15},
        },
    }


def crear_pantalla(estado):
    return PantallaVictoria(
        estado=estado,
        avatares={"red": "avatar_1", "blue": "avatar_1"},
        nombres={"red": "Jugador Rojo", "blue": "Jugador Azul"},
    )


def test_podio_ganador_rojo():
    pantalla = crear_pantalla(crear_estado("red"))

    assert pantalla._ganador == "red"
    assert pantalla._podio == [("red", 1), ("blue", 2)]


def test_podio_ganador_azul():
    pantalla = crear_pantalla(crear_estado("blue"))

    assert pantalla._ganador == "blue"
    assert pantalla._podio == [("blue", 1), ("red", 2)]


def test_duracion_partida():
    pantalla = crear_pantalla(crear_estado(duracion=332))

    assert pantalla._minutos == 5
    assert pantalla._segundos == 32


@pytest.mark.parametrize("duracion, esperado", [
    (59.99999999999764, (1, 0)),
    (59.5, (1, 0)),
    (59.4, (0, 59)),
    (0.4, (0, 0)),
    (-2, (0, 0)),
])
def test_duracion_se_redondea_al_segundo_mas_cercano(duracion, esperado):
    pantalla = crear_pantalla(crear_estado(duracion=duracion))

    assert (pantalla._minutos, pantalla._segundos) == esperado


def duraciones_web(valores):
    """Ejecuta la función duracion() de la webapp con Node."""
    script = APP_WEB.read_text(encoding="utf-8")
    funcion = re.search(r"function duracion\(segundos\) \{.*?\n\}", script, re.S).group(0)
    codigo = f"{funcion}\nconsole.log(JSON.stringify({json.dumps(valores)}.map(duracion)));"
    salida = subprocess.run([shutil.which("node"), "-e", codigo],
                            capture_output=True, text=True, timeout=30, check=True)
    return json.loads(salida.stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js no esta instalado")
def test_duracion_coincide_con_la_webapp():
    pantallas = [crear_pantalla(crear_estado(duracion=valor)) for valor in DURACIONES]

    assert duraciones_web(DURACIONES) == [
        f"{pantalla._minutos}:{pantalla._segundos:02d}" for pantalla in pantallas
    ]


def test_prorrogas():
    pantalla = crear_pantalla(crear_estado(prorrogas=2))

    assert pantalla._prorrogas == 2


def test_puntuaciones_finales():
    pantalla = crear_pantalla(crear_estado())

    assert pantalla._puntos_rojo == 20
    assert pantalla._puntos_azul == 15