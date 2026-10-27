
"""Importación y almacenamiento de imágenes personalizadas de avatares."""

import shutil
from pathlib import Path
from uuid import uuid4

import pygame


EXTENSIONES_PERMITIDAS = {".png", ".jpg", ".jpeg"}
TAMANO_MAXIMO = 5 * 1024 * 1024

CARPETA_AVATARES = Path(__file__).resolve().parent / "data" / "custom_avatars"


def importar_avatar(ruta_origen: str) -> str:
    """Valida una imagen, la copia y devuelve su identificador."""
    origen = Path(ruta_origen)

    if not origen.is_file():
        raise ValueError("El archivo seleccionado no existe.")

    if origen.suffix.lower() not in EXTENSIONES_PERMITIDAS:
        raise ValueError("Selecciona una imagen PNG, JPG o JPEG.")

    if origen.stat().st_size > TAMANO_MAXIMO:
        raise ValueError("La imagen no puede superar los 5 MB.")

    try:
        imagen = pygame.image.load(str(origen))
        if imagen.get_width() <= 0 or imagen.get_height() <= 0:
            raise ValueError("La imagen no tiene dimensiones válidas.")
    except pygame.error as error:
        raise ValueError("No se pudo leer la imagen seleccionada.") from error

    CARPETA_AVATARES.mkdir(parents=True, exist_ok=True)

    identificador = f"custom_{uuid4().hex}{origen.suffix.lower()}"
    destino = CARPETA_AVATARES / identificador

    shutil.copyfile(origen, destino)

    return identificador


def obtener_ruta_avatar(identificador: str) -> Path | None:
    """Devuelve la ruta de una imagen personalizada válida."""
    nombre = Path(identificador)

    if (
        not identificador.startswith("custom_")
        or nombre.name != identificador
        or nombre.suffix.lower() not in EXTENSIONES_PERMITIDAS
    ):
        return None

    ruta = CARPETA_AVATARES / identificador
    return ruta if ruta.is_file() else None
