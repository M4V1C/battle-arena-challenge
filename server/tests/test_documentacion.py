"""La documentaci\u00f3n refleja los datos y las rutas reales del servidor."""

import json
import re
from pathlib import Path

from fastapi.routing import APIRoute

import app.main as main
from app.reglas import ARCHIVO_REGLAS

RAIZ = Path(__file__).resolve().parents[2]


def bloque_json_tras(texto: str, titulo: str) -> dict:
    coincidencia = re.search(re.escape(titulo) + r"\s.*?```json\s*(\{.*?\})\s*```", texto, re.S)
    assert coincidencia, f"No hay bloque JSON despu\u00e9s de {titulo!r}"
    return json.loads(coincidencia.group(1))


def test_reglas_documentadas_coinciden_con_reglas_json():
    modelo = (RAIZ / "docs" / "modelo-de-datos.md").read_text(encoding="utf-8")
    reales = json.loads(ARCHIVO_REGLAS.read_text(encoding="utf-8"))

    assert bloque_json_tras(modelo, "### Reglas") == reales


def test_readme_documenta_todas_las_rutas_de_la_api():
    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    rutas = {ruta.path for ruta in main.app.routes
             if isinstance(ruta, APIRoute) and ruta.include_in_schema}

    faltantes = sorted(ruta for ruta in rutas if f"{ruta}`" not in readme and f"{ruta}," not in readme)
    assert faltantes == []
    assert "POST /resultados" not in readme
