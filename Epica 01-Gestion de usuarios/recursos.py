# =====================================================================
#  recursos.py  -  INICIALIZACIÓN DE PYGAME (ventana, reloj y fuentes)
# =====================================================================
#  Aquí se enciende pygame y se crean los objetos que usa TODO el programa:
#     VENTANA -> la superficie donde se dibuja todo
#     RELOJ   -> controla los cuadros por segundo
#     FUENTE_* -> los tipos de letra
#
#  Al importar este módulo, pygame se inicializa automáticamente.
#  Los demás módulos lo usan así:   from recursos import VENTANA, FUENTE_TEXTO
# =====================================================================

import pygame

from config import ANCHO, ALTO, NOMBRE_JUEGO

pygame.init()

VENTANA = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption(NOMBRE_JUEGO)
RELOJ = pygame.time.Clock()        # Sirve para limitar los FPS

pygame.key.start_text_input()      # Activa los eventos de escritura (TEXTINPUT)
pygame.key.set_repeat(400, 40)     # Mantener presionada una tecla la repite

# Fuentes (nombre, tamaño). Si "arial" no existe, pygame usa otra por defecto.
FUENTE_TITULO = pygame.font.SysFont("arial", 34, bold=True)
FUENTE_TEXTO = pygame.font.SysFont("arial", 22)
FUENTE_ETIQUETA = pygame.font.SysFont("arial", 18)
FUENTE_ERROR = pygame.font.SysFont("arial", 16)   # Pequeña pero legible