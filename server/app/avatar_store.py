
"""Almacenamiento compartido de avatares de los jugadores."""

import base64
import binascii
import hashlib
import threading

JUGADORES = ("red", "blue")
AVATARES_PREDETERMINADOS = tuple(
    f"avatar_{numero}" for numero in range(1, 6)
)

TAMANO_MAXIMO_IMAGEN = 5 * 1024 * 1024


class AlmacenAvatares:
    """Conserva las selecciones y las imágenes de ambos jugadores."""

    def __init__(self):
        self._bloqueo = threading.Lock()

        self._selecciones = {
            "red": "avatar_1",
            "blue": "avatar_2",
        }

        self._imagenes = {}

    def seleccionar(self, jugador: str, avatar: str) -> dict:
        """Actualiza la selección de un jugador."""

        if jugador not in JUGADORES:
            raise ValueError("Jugador no válido.")

        if not isinstance(avatar, str):
            raise ValueError("Avatar no válido.")

        with self._bloqueo:
            if (
                avatar not in AVATARES_PREDETERMINADOS
                and avatar not in self._imagenes
            ):
                raise ValueError("El avatar no existe en el servidor.")

            self._selecciones[jugador] = avatar

            return self._obtener_sin_bloqueo()

    def importar(self, jugador: str, imagen_base64: str) -> dict:
        """Recibe una imagen personalizada y la almacena."""

        if jugador not in JUGADORES:
            raise ValueError("Jugador no válido.")

        if not isinstance(imagen_base64, str):
            raise ValueError("Imagen no válida.")

        if len(imagen_base64) > ((TAMANO_MAXIMO_IMAGEN + 2) // 3) * 4:
            raise ValueError("La imagen supera el tamaño permitido.")

        try:
            datos = base64.b64decode(
                imagen_base64,
                validate=True,
            )
        except (binascii.Error, ValueError) as error:
            raise ValueError("La imagen no tiene un formato válido.") from error

        if not datos or len(datos) > TAMANO_MAXIMO_IMAGEN:
            raise ValueError("La imagen supera el tamaño permitido.")

        identificador = (
            "custom_" + hashlib.sha256(datos).hexdigest() + ".png"
        )

        with self._bloqueo:
            self._imagenes[identificador] = imagen_base64
            self._selecciones[jugador] = identificador

            return self._obtener_sin_bloqueo()

    def obtener(self) -> dict:
        """Devuelve las selecciones actuales."""

        with self._bloqueo:
            return self._obtener_sin_bloqueo()

    def obtener_imagen(self, avatar: str) -> dict:
        """Devuelve una imagen personalizada almacenada."""

        with self._bloqueo:
            if avatar not in self._imagenes:
                raise ValueError("Imagen no encontrada.")

            return {
                "type": "avatar_image",
                "avatar": avatar,
                "image": self._imagenes[avatar],
            }

    def _obtener_sin_bloqueo(self) -> dict:
        return {
            "type": "avatars",
            "players": dict(self._selecciones),
        }
