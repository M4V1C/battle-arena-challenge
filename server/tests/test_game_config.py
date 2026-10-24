import pytest
import json
import threading

from app.game_state import EstadoJuego
from app.socket_server import procesar_mensaje
from app.game_config import AlmacenConfiguracion, validar_configuracion


def test_configuracion_persiste_entre_instancias(tmp_path):
    ruta = tmp_path / "data" / "game_config.json"
    almacen = AlmacenConfiguracion(ruta)
    assert almacen.obtener()["value"] == 20
    datos = {"condition": "time","value": 2,"sensitivity": 1.5,"freeze_seconds": 3.0,}
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


def test_no_permite_configuracion_durante_partida(tmp_path):
    almacen = AlmacenConfiguracion(tmp_path / "game_config.json")
    juego = EstadoJuego()

    # Antes de iniciar, se permite consultar la configuración.
    respuesta = json.loads(
        procesar_mensaje(
            json.dumps({"type": "get_config"}),
            juego,
            almacen,
        )
    )
    assert respuesta["type"] == "config"

    # Iniciamos la partida.
    juego.iniciar_partida(almacen.obtener())

    # Durante la partida, no se permite consultar la configuración.
    respuesta = json.loads(
        procesar_mensaje(
            json.dumps({"type": "get_config"}),
            juego,
            almacen,
        )
    )
    assert respuesta["type"] == "error"
    assert "partida en curso" in respuesta["message"]

    # Tampoco se permite modificarla.
    respuesta = json.loads(
        procesar_mensaje(
            json.dumps({
                "type": "save_config",
                "config": {
                    "condition": "points",
                    "value": 50,
                    "sensitivity": 1.0,
                },
            }),
            juego,
            almacen,
        )
    )
    assert respuesta["type"] == "error"

    # La configuración almacenada debe permanecer intacta.
    assert almacen.obtener()["value"] == 20

    # Al finalizar la partida, se vuelve a permitir el acceso.
    juego.reiniciar_partida()

    respuesta = json.loads(
        procesar_mensaje(
            json.dumps({"type": "get_config"}),
            juego,
            almacen,
        )
    )
    assert respuesta["type"] == "config"

def test_tiempo_congelamiento_se_guarda(tmp_path):
    ruta = tmp_path / "game_config.json"
    almacen = AlmacenConfiguracion(ruta)

    configuracion = {
        "condition": "points",
        "value": 20,
        "sensitivity": 1.0,
        "freeze_seconds": 2.5,
    }

    almacen.guardar(configuracion)

    nuevo_almacen = AlmacenConfiguracion(ruta)

    assert nuevo_almacen.obtener()["freeze_seconds"] == 2.5


@pytest.mark.parametrize(
    "valor",
    [0, -1, True, "3", None, float("inf"), float("nan")],
)
def test_tiempo_congelamiento_invalido(tmp_path, valor):
    almacen = AlmacenConfiguracion(tmp_path / "game_config.json")
    anterior = almacen.obtener()

    with pytest.raises(ValueError):
        almacen.guardar({
            "condition": "points",
            "value": 20,
            "freeze_seconds": valor,
        })

    assert almacen.obtener() == anterior


def test_configuracion_anterior_utiliza_congelamiento_predeterminado():
    configuracion_anterior = {
        "condition": "points",
        "value": 20,
        "sensitivity": 1.0,
    }

    resultado = validar_configuracion(configuracion_anterior)

    assert resultado["freeze_seconds"] == 3.0   


def test_inicio_de_partida_espera_guardado_de_configuracion():
    juego = EstadoJuego()

    operacion_iniciada = threading.Event()
    permitir_finalizar = threading.Event()
    partida_iniciada = threading.Event()
    errores = []

    def guardar_configuracion():
        def operacion():
            operacion_iniciada.set()
            if not permitir_finalizar.wait(timeout=5):
                raise TimeoutError("La prueba excedio el tiempo de espera.")

        try:
            juego.ejecutar_si_no_hay_partida(operacion)
        except Exception as error:
            errores.append(error)

    def iniciar_partida():
        try:
            juego.iniciar_partida({
                "condition": "points",
                "value": 20,
                "freeze_seconds": 3.0,
            })
            partida_iniciada.set()
        except Exception as error:
            errores.append(error)

    hilo_guardado = threading.Thread(target=guardar_configuracion)
    hilo_partida = threading.Thread(target=iniciar_partida)

    hilo_guardado.start()

    try:
        assert operacion_iniciada.wait(timeout=5)

        hilo_partida.start()

        # El inicio de partida debe esperar mientras el bloqueo
        # de configuracion permanece ocupado.
        assert not partida_iniciada.wait(timeout=0.2)

    finally:
        permitir_finalizar.set()
        hilo_guardado.join(timeout=5)

        if hilo_partida.ident is not None:
            hilo_partida.join(timeout=5)

    assert not hilo_guardado.is_alive()
    assert not hilo_partida.is_alive()
    assert errores == []
    assert partida_iniciada.is_set()
    assert juego.partida_en_curso()
