# =====================================================================
#  pantalla_verificacion.py  -  PANTALLA "Verifica tu correo electrónico" (US-02)
# =====================================================================
#  Aquí el jugador escribe el código de 6 dígitos que recibió por correo.
#  Se llega desde el registro o desde el login (si el correo no estaba verificado).
# =====================================================================

from config import MARGEN, ANCHO_CAMPOS, ALTO_CAMPO, AZUL_CLARO, ROJO, VERDE
from recursos import VENTANA, FUENTE_TITULO, FUENTE_TEXTO, FUENTE_ERROR
from componentes import (CampoTexto, Boton, calcular_panel, dibujar_panel,
                         dibujar_texto_centrado, dibujar_mensaje,
                         manejar_teclado_campos)
from estado import registrar_pantalla, ir_a
from cuentas import procesar_verificacion


# ---------------------------------------------------------------------
# 1) ELEMENTOS Y POSICIONES
# ---------------------------------------------------------------------
PANEL = calcular_panel(560)
X_CAMPOS = PANEL.x + MARGEN

campo_codigo = CampoTexto(X_CAMPOS, PANEL.y + 250, ANCHO_CAMPOS, ALTO_CAMPO,
                          "Código de verificación", max_caracteres=6)
boton_confirmar = Boton(X_CAMPOS, PANEL.y + 360, ANCHO_CAMPOS, 52, "Confirmar")
boton_volver = Boton(X_CAMPOS, PANEL.y + 470, ANCHO_CAMPOS, 52, "Volver")


# ---------------------------------------------------------------------
# 2) DIBUJO
# ---------------------------------------------------------------------
def dibujar_verificacion(estado):
    """Dibuja todos los elementos de la pantalla de verificación de correo."""
    dibujar_panel(PANEL)
    centro_x = PANEL.centerx

    dibujar_texto_centrado("Verifica tu correo electrónico", FUENTE_TITULO, AZUL_CLARO,
                           centro_x, PANEL.y + 40)
    dibujar_texto_centrado("Escribe aquí el código que te enviamos.", FUENTE_TEXTO, AZUL_CLARO,
                           centro_x, PANEL.y + 110)
    dibujar_texto_centrado(f"Enviado a: {estado.correo_pendiente}", FUENTE_ERROR, AZUL_CLARO,
                           centro_x, PANEL.y + 150)

    # Aviso rojo: aparece cuando llegamos aquí desde el login con correo sin verificar
    if estado.aviso_verificacion:
        dibujar_texto_centrado(estado.aviso_verificacion, FUENTE_ERROR, ROJO,
                               centro_x, PANEL.y + 180)

    campo_codigo.dibujar(VENTANA)
    boton_confirmar.dibujar(VENTANA)
    dibujar_mensaje(estado, centro_x, PANEL.y + 425)
    boton_volver.dibujar(VENTANA)


# ---------------------------------------------------------------------
# 3) EVENTOS
# ---------------------------------------------------------------------
def eventos_verificacion(evento, estado):
    presiono_enter = manejar_teclado_campos(evento, [campo_codigo])

    # Botón "Confirmar" (o ENTER)
    if boton_confirmar.fue_presionado(evento) or presiono_enter:
        if procesar_verificacion(campo_codigo, estado.usuario_pendiente):
            estado.verificado = True
            estado.poner_mensaje("¡Correo verificado! Tu cuenta ya está activa.", VERDE)
        else:
            estado.poner_mensaje("")

    # Botón "Volver": regresa a la pantalla de donde veníamos
    if boton_volver.fue_presionado(evento):
        destino = estado.pantalla_anterior

        # Si terminó el registro, pedimos que el formulario quede limpio
        if estado.verificado and destino == "registro":
            estado.limpiar_registro = True

        ir_a(estado, destino)

        if estado.verificado and destino == "login":
            estado.poner_mensaje("¡Correo verificado! Ya puedes iniciar sesión.", VERDE)


def al_entrar_verificacion(estado):
    """Al entrar, el campo del código siempre empieza vacío."""
    campo_codigo.limpiar()


# ---------------------------------------------------------------------
# REGISTRO DE LA PANTALLA
# ---------------------------------------------------------------------
registrar_pantalla("verificacion", dibujar_verificacion, eventos_verificacion,
                   campos=[campo_codigo], al_entrar=al_entrar_verificacion)