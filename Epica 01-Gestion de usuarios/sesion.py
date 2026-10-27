# =====================================================================
#  sesion.py  -  SESIÓN DEL JUGADOR (quién ha iniciado sesión)
# =====================================================================
#  La sesión guarda QUIÉN ha iniciado sesión. Como es un objeto que vive
#  mientras el programa está abierto, se mantiene al cambiar de pantalla.
#  Al cerrar sesión se vacía.
#
#  Uso desde cualquier módulo:
#      from sesion import SESION
#      if SESION.activa: print(SESION.usuario)
# =====================================================================


class Sesion:
    def __init__(self):
        self.usuario = None        # Nombre del jugador (None = nadie ha iniciado sesión)
        self.correo = None
        self.avatar = "default"

    @property
    def activa(self):
        """True si hay un jugador autenticado."""
        return self.usuario is not None

    def iniciar(self, cuenta):
        """Guarda los datos del jugador (NUNCA guardamos su contraseña ni su hash)."""
        self.usuario = cuenta["usuario"]
        self.correo = cuenta["correo"]
        self.avatar = cuenta.get("avatar", "default")

    def cerrar(self):
        """Vacía la sesión."""
        self.usuario = None
        self.correo = None
        self.avatar = "default"


SESION = Sesion()                  # Una única sesión para todo el programa