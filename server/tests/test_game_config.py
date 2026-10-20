import pytest

from app.game_config import AlmacenConfiguracion, validar_configuracion


def test_configuracion_persiste_entre_instancias(tmp_path):
    ruta = tmp_path / "data" / "game_config.json"
    almacen = AlmacenConfiguracion(ruta)
    assert almacen.obtener()["value"] == 20
    datos = {"condition": "time", "value": 2, "sensitivity": 1.5}
    almacen.guardar(datos)
    assert AlmacenConfiguracion(ruta).obtener() == datos


@pytest.mark.parametrize("valor", [0, -1, True, 1.5, "20", None])
def test_limite_invalido_no_modifica_archivo(tmp_path, valor):
    almacen = AlmacenConfiguracion(tmp_path / "config.json")
    anterior = almacen.obtener()
    with pytest.raises(ValueError):
        almacen.guardar({"condition": "points", "value": valor})
    assert AlmacenConfiguracion(almacen.ruta).obtener() == anterior


@pytest.mark.parametrize("condicion", ["points", "time"])
def test_limite_minimo_es_uno(condicion):
    assert validar_configuracion({"condition": condicion, "value": 1})["value"] == 1