"""Imagen reproducible: versiones fijas y sin datos de usuarios dentro de la imagen."""

import re
from pathlib import Path

SERVIDOR = Path(__file__).resolve().parents[1]


def lineas(nombre):
    texto = (SERVIDOR / nombre).read_text(encoding="utf-8")
    return [linea.strip() for linea in texto.splitlines() if linea.strip() and not linea.startswith("#")]


def test_dependencias_con_version_fija():
    assert all(re.fullmatch(r"[\w\-\[\]]+==[\w.]+", linea) for linea in lineas("requirements.txt"))


def test_imagen_base_con_version_concreta():
    base = next(linea for linea in lineas("Dockerfile") if linea.startswith("FROM"))
    assert re.fullmatch(r"FROM python:3\.12\.\d+-slim", base)


def test_la_imagen_no_copia_cuentas_ni_resultados_pero_si_la_configuracion():
    reglas = lineas(".dockerignore")
    assert "data/*" in reglas
    reincluidas = {regla[1:].rstrip("/") for regla in reglas if regla.startswith("!")}
    assert reincluidas == {"data/escenarios", "data/reglas.json", "data/game_config.json"}
    assert all((SERVIDOR / ruta).exists() for ruta in reincluidas)
