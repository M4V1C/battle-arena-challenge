# =====================================================================
#  pantalla_juego.py  -  ÁREA DE JUEGO (solo con sesión iniciada)
# =====================================================================
#  Por ahora es una pantalla de bienvenida: demuestra que el sistema
#  identificó al jugador y muestra su avatar. Desde aquí se accede al
#  perfil o se cierra la sesión.
#
#  Aquí es donde más adelante irá el lobby / las partidas. Cuando una
#  partida termine, llama a:
#       perfil_datos.registrar_partida(SESION.usuario, "victoria", puntaje, segundos)
#  para que se actualicen las estadísticas, logros e historial del perfil.
# =====================================================================

from config import MARGEN, ANCHO_CAMPOS, AZUL_CLARO, VERDE
from recursos import VENTANA, FUENTE_TITULO, FUENTE_ERROR
from componentes import (Boton, calcular_panel, dibujar_panel, dibujar_texto_centrado,
                         dibujar_avatar)
from estado import registrar_pantalla, ir_a
from sesion import SESION


# ---------------------------------------------------------------------
# 1) ELEMENTOS Y POSICIONES
# ---------------------------------------------------------------------
PANEL = calcular_panel(630)
X_CAMPOS = PANEL.x + MARGEN

boton_perfil = Boton(X_CAMPOS, PANEL.y + 440, ANCHO_CAMPOS, 52, "Mi perfil")
boton_cerrar_sesion = Boton(X_CAMPOS, PANEL.y + 505, ANCHO_CAMPOS, 52, "Cerrar sesión")


# ---------------------------------------------------------------------
# 2) DIBUJO
# ---------------------------------------------------------------------
def dibujar_juego(estado):
    dibujar_panel(PANEL)
    centro_x = PANEL.centerx

    dibujar_texto_centrado("Área de juego", FUENTE_TITULO, AZUL_CLARO, centro_x, PANEL.y + 40)

    # Avatar grande del jugador identificado
    dibujar_avatar((centro_x, PANEL.y + 180), 70, SESION.avatar)

    dibujar_texto_centrado(f"¡Bienvenido, {SESION.usuario}!", FUENTE_TITULO, AZUL_CLARO,
                           centro_x, PANEL.y + 275)
    dibujar_texto_centrado(SESION.correo, FUENTE_ERROR, AZUL_CLARO, centro_x, PANEL.y + 325)
    dibujar_texto_centrado("Correo verificado", FUENTE_ERROR, VERDE, centro_x, PANEL.y + 350)
    dibujar_texto_centrado("Aquí aparecerán las partidas (próximamente).", FUENTE_ERROR,
                           AZUL_CLARO, centro_x, PANEL.y + 395)

    boton_perfil.dibujar(VENTANA)
    boton_cerrar_sesion.dibujar(VENTANA)


# ---------------------------------------------------------------------
# 3) EVENTOS
# ---------------------------------------------------------------------
def eventos_juego(evento, estado):
    # Botón "Mi perfil"
    if boton_perfil.fue_presionado(evento):
        ir_a(estado, "perfil")

    # Botón "Cerrar sesión": vaciamos la sesión y volvemos al login
    if boton_cerrar_sesion.fue_presionado(evento):
        SESION.cerrar()
        ir_a(estado, "login")


# ---------------------------------------------------------------------
# REGISTRO DE LA PANTALLA
# ---------------------------------------------------------------------
registrar_pantalla("juego", dibujar_juego, eventos_juego)