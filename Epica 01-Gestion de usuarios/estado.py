# =====================================================================
#  estado.py  -  ESTADO DEL PROGRAMA Y NAVEGACIÓN ENTRE PANTALLAS
# =====================================================================
#  Aquí está lo que comparten TODAS las pantallas:
#
#   1) La clase Estado: guarda en qué pantalla estamos y los datos que
#      las pantallas se pasan entre sí.
#
#   2) El REGISTRO de pantallas: un diccionario donde cada archivo
#      pantalla_*.py se "anota" con:
#           - su función para DIBUJARSE,
#           - su función para manejar EVENTOS,
#           - sus campos de texto,
#           - (opcional) una función que se ejecuta al ENTRAR a la pantalla.
#      Gracias a esto, las pantallas no necesitan importarse entre sí
#      y agregar una pantalla nueva es solo crear un archivo y registrarlo.
#
#   3) ir_a(): cambia de pantalla.
#   4) dibujar_pantalla() y mostrar_procesando().
# =====================================================================

import pygame

from config import AZUL_CLARO, ROJO, NEGRO
from recursos import VENTANA
from componentes import dibujar_barra_sesion


# =====================================================================
# 1) CLASE ESTADO
# =====================================================================
class Estado:
    """
    Contenedor de variables compartidas. Así podemos pasárselo a las
    funciones en lugar de usar muchas variables sueltas.
    """

    def __init__(self):
        self.pantalla = "registro"            # Pantalla actual
        self.pantalla_anterior = "registro"   # A dónde vuelve el botón "Volver" de verificación

        # Mensajes
        self.mensaje = ""                     # Mensaje general de la pantalla actual
        self.color_mensaje = ROJO             # Color de ese mensaje
        self.aviso_verificacion = ""          # Aviso rojo extra en la pantalla de verificación

        # Verificación de correo
        self.usuario_pendiente = ""           # Usuario que está verificando su correo
        self.correo_pendiente = ""            # Su correo (para mostrarlo en pantalla)
        self.verificado = False               # ¿Ya se verificó correctamente el correo?
        self.limpiar_registro = False         # Pide a la pantalla de registro vaciar su formulario

        # Recuperación de contraseña
        self.correo_recuperacion = ""         # Correo para el que se pidió recuperar contraseña

        # Perfil del jugador
        self.perfil = None                    # Datos del perfil cargados (ver perfil_datos.py)
        self.pestana_perfil = "estadisticas"  # Pestaña abierta en el perfil
        self.scroll_historial = 0             # Desplazamiento de la lista del historial

    def poner_mensaje(self, texto, color=ROJO):
        """Cambia el mensaje general que se muestra en la pantalla."""
        self.mensaje = texto
        self.color_mensaje = color


# =====================================================================
# 2) REGISTRO DE PANTALLAS
# =====================================================================
PANTALLAS = {}      # nombre -> {"dibujar": ..., "eventos": ..., "campos": [...], "al_entrar": ...}

# Pantallas a las que NO se puede entrar sin sesión iniciada (CA-02.5 y CA-03.4)
PANTALLAS_PROTEGIDAS = ("juego", "perfil")


def registrar_pantalla(nombre, dibujar, eventos, campos=None, al_entrar=None):
    """
    Anota una pantalla en el registro. Cada archivo pantalla_*.py llama a esta
    función una vez, al final del archivo.
    """
    PANTALLAS[nombre] = {
        "dibujar": dibujar,
        "eventos": eventos,
        "campos": campos or [],
        "al_entrar": al_entrar,
    }


# =====================================================================
# 3) NAVEGACIÓN
# =====================================================================
def ir_a(estado, pantalla):
    """
    Cambia de pantalla. Borra mensajes anteriores, deja el cursor listo en
    el primer campo de la pantalla nueva y ejecuta su función 'al_entrar'.
    """
    estado.pantalla = pantalla
    estado.poner_mensaje("")
    estado.aviso_verificacion = ""

    # Quitamos el cursor de TODOS los campos de TODAS las pantallas...
    for datos in PANTALLAS.values():
        for campo in datos["campos"]:
            campo.activo = False

    # ...y se lo damos al primer campo de la pantalla nueva
    datos_nueva = PANTALLAS[pantalla]
    if datos_nueva["campos"]:
        datos_nueva["campos"][0].activo = True

    if datos_nueva["al_entrar"]:
        datos_nueva["al_entrar"](estado)


# =====================================================================
# 4) DIBUJO GENERAL
# =====================================================================
def dibujar_pantalla(estado):
    """Borra la ventana, dibuja la pantalla actual y la barra de sesión."""
    VENTANA.fill(NEGRO)                                  # Borramos el cuadro anterior
    PANTALLAS[estado.pantalla]["dibujar"](estado)        # Dibuja la pantalla actual
    dibujar_barra_sesion()                               # Avatar y nombre arriba a la derecha


def mostrar_procesando(estado):
    """
    Muestra "Procesando..." de inmediato. Se usa ANTES de tareas lentas (API,
    enviar correos) porque mientras se ejecutan la ventana queda congelada.
    """
    estado.poner_mensaje("Procesando, por favor espera...", AZUL_CLARO)
    dibujar_pantalla(estado)
    pygame.display.flip()