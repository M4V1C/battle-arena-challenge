# =====================================================================
#  config.py  -  CONFIGURACIÓN GENERAL DEL PROYECTO
# =====================================================================
#  Aquí viven TODAS las constantes del juego (tamaños, colores, correo...).
#  Si quieres cambiar algo (un color, el tiempo de expiración de un código,
#  el correo emisor...), este es el único archivo que debes tocar.
#
#  Este módulo no depende de ningún otro: todos los demás lo importan a él.
#
#  ¡OJO! Este archivo contiene la contraseña del correo emisor.
#  Si algún día subes el proyecto a GitHub, NO subas este archivo
#  (agrégalo a un archivo .gitignore) o usa variables de entorno.
# =====================================================================

import os


# ---------------------------------------------------------------------
# VENTANA
# ---------------------------------------------------------------------
ANCHO = 1600
ALTO = 900
FPS = 60                           # Cuadros por segundo del juego

NOMBRE_JUEGO = "Control del Reactor"


# ---------------------------------------------------------------------
# COLORES (formato RGB: rojo, verde, azul; cada uno de 0 a 255)
# ---------------------------------------------------------------------
NEGRO = (0, 0, 0)
AZUL_CLARO = (100, 200, 255)       # Líneas, textos y bordes
AZUL_OSCURO = (0, 45, 70)          # Fondo de un botón con el mouse encima o seleccionado
AZUL_HOVER = (200, 235, 255)       # Texto/enlace con el mouse encima
GRIS_AZUL = (80, 125, 155)         # Elementos "apagados" (logros bloqueados, cabeceras)
LINEA_TENUE = (25, 85, 120)        # Líneas separadoras suaves
ROJO = (255, 70, 70)               # Mensajes de error
VERDE = (90, 230, 130)             # Mensajes de éxito


# ---------------------------------------------------------------------
# MEDIDAS COMUNES DE LA INTERFAZ
# ---------------------------------------------------------------------
ANCHO_PANEL = 640                  # Ancho del recuadro central de las pantallas de cuenta
MARGEN = 60                        # Espacio entre el borde del panel y los campos
ANCHO_CAMPOS = ANCHO_PANEL - 2 * MARGEN   # Ancho de campos y botones (520)
ALTO_CAMPO = 46
SEPARACION = 108                   # Distancia vertical entre campos (deja sitio al error)


# ---------------------------------------------------------------------
# ARCHIVO DE USUARIOS
# ---------------------------------------------------------------------
# Se guarda junto a estos módulos, sin importar desde dónde ejecutes el juego.
CARPETA_PROYECTO = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_USUARIOS = os.path.join(CARPETA_PROYECTO, "usuarios.json")


# ---------------------------------------------------------------------
# CORREO (SMTP)
# ---------------------------------------------------------------------
# Servidor desde el que se envían los códigos. Con Gmail se necesita una
# "contraseña de aplicación" (NO la contraseña normal de la cuenta).
# Si defines las variables de entorno REACTOR_SMTP_USER y REACTOR_SMTP_PASS,
# se usan esas; si no, se usan los valores escritos aquí.
SMTP_SERVIDOR = "smtp.gmail.com"
SMTP_PUERTO = 587
SMTP_USUARIO = os.environ.get("REACTOR_SMTP_USER", "andrewbp32@gmail.com")
# .replace(" ", "") quita los espacios: Google muestra la clave en bloques de 4
# letras separados por espacios, pero en realidad no los lleva.
SMTP_CLAVE = os.environ.get("REACTOR_SMTP_PASS", "orwa vues mppv ijbk").replace(" ", "")

# Dirección que aparece como remitente en el correo. Con Gmail es la misma
# que SMTP_USUARIO; con otros servicios podría ser distinta.
CORREO_REMITENTE = SMTP_USUARIO


# ---------------------------------------------------------------------
# CÓDIGOS DE VERIFICACIÓN Y DE RECUPERACIÓN
# ---------------------------------------------------------------------
MINUTOS_VALIDEZ_CODIGO = 15        # Tiempo antes de que expire el código de verificación
MINUTOS_VALIDEZ_RECUPERACION = 15  # Tiempo antes de que expire el código de recuperación
MAX_INTENTOS_RECUPERACION = 5      # Códigos incorrectos permitidos antes de invalidarlo


# ---------------------------------------------------------------------
# PERFIL DEL JUGADOR
# ---------------------------------------------------------------------
PUNTOS_POR_NIVEL = 500             # Cada 500 puntos acumulados el jugador sube un nivel