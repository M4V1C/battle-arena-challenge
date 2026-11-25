# =====================================================================
#  pantalla_recuperacion.py  -  RECUPERAR CONTRASEÑA (US-05)
# =====================================================================
#  Este archivo contiene DOS pantallas (los dos pasos del proceso):
#     "rec_solicitud" -> el jugador escribe su correo y recibe un código
#     "rec_nueva"     -> escribe el código y la nueva contraseña
# =====================================================================

from config import (MARGEN, ANCHO_CAMPOS, ALTO_CAMPO, SEPARACION, AZUL_CLARO, VERDE,
                    MINUTOS_VALIDEZ_RECUPERACION)
from recursos import VENTANA, FUENTE_TITULO, FUENTE_TEXTO, FUENTE_ERROR
from componentes import (CampoTexto, Boton, calcular_panel, dibujar_panel,
                         dibujar_texto_centrado, dibujar_mensaje,
                         manejar_teclado_campos)
from estado import registrar_pantalla, ir_a, mostrar_procesando
from cuentas import solicitar_recuperacion, restablecer_contrasena


# =====================================================================
# PASO 1: PEDIR EL CÓDIGO
# =====================================================================
PANEL_1 = calcular_panel(510)
X_1 = PANEL_1.x + MARGEN

campo_rec_correo = CampoTexto(X_1, PANEL_1.y + 190, ANCHO_CAMPOS, ALTO_CAMPO,
                              "Correo electrónico", max_caracteres=60)
boton_enviar_codigo = Boton(X_1, PANEL_1.y + 300, ANCHO_CAMPOS, 52, "Enviar código")
boton_paso1_volver = Boton(X_1, PANEL_1.y + 410, ANCHO_CAMPOS, 52, "Volver")


def dibujar_rec_solicitud(estado):
    """Dibuja la pantalla donde se pide el código de recuperación."""
    dibujar_panel(PANEL_1)
    centro_x = PANEL_1.centerx

    dibujar_texto_centrado("Recupera tu contraseña", FUENTE_TITULO, AZUL_CLARO,
                           centro_x, PANEL_1.y + 40)
    dibujar_texto_centrado("Escribe el correo electrónico de tu cuenta.", FUENTE_TEXTO, AZUL_CLARO,
                           centro_x, PANEL_1.y + 105)
    dibujar_texto_centrado("Te enviaremos un código para crear una nueva contraseña.",
                           FUENTE_ERROR, AZUL_CLARO, centro_x, PANEL_1.y + 138)

    campo_rec_correo.dibujar(VENTANA)
    boton_enviar_codigo.dibujar(VENTANA)
    dibujar_mensaje(estado, centro_x, PANEL_1.y + 365)
    boton_paso1_volver.dibujar(VENTANA)


def eventos_rec_solicitud(evento, estado):
    presiono_enter = manejar_teclado_campos(evento, [campo_rec_correo])

    # Botón "Enviar código" (o ENTER)
    if boton_enviar_codigo.fue_presionado(evento) or presiono_enter:
        mostrar_procesando(estado)
        todo_bien, mensaje = solicitar_recuperacion(campo_rec_correo)

        if todo_bien:
            estado.correo_recuperacion = campo_rec_correo.texto.strip()
            ir_a(estado, "rec_nueva")
        else:
            estado.poner_mensaje(mensaje)

    # Botón "Volver": regresa al login
    if boton_paso1_volver.fue_presionado(evento):
        ir_a(estado, "login")


def al_entrar_rec_solicitud(estado):
    """Al entrar, el campo del correo empieza vacío."""
    campo_rec_correo.limpiar()


# =====================================================================
# PASO 2: CÓDIGO Y NUEVA CONTRASEÑA
# =====================================================================
PANEL_2 = calcular_panel(720)
X_2 = PANEL_2.x + MARGEN

campo_rec_codigo = CampoTexto(X_2, PANEL_2.y + 200, ANCHO_CAMPOS, ALTO_CAMPO,
                              "Código de recuperación", max_caracteres=6)
campo_rec_nueva = CampoTexto(X_2, PANEL_2.y + 200 + SEPARACION, ANCHO_CAMPOS, ALTO_CAMPO,
                             "Nueva contraseña", es_contrasena=True, max_caracteres=40)
campo_rec_confirmar = CampoTexto(X_2, PANEL_2.y + 200 + SEPARACION * 2, ANCHO_CAMPOS, ALTO_CAMPO,
                                 "Confirmar nueva contraseña", es_contrasena=True, max_caracteres=40)
CAMPOS_PASO_2 = [campo_rec_codigo, campo_rec_nueva, campo_rec_confirmar]

boton_cambiar = Boton(X_2, PANEL_2.y + 510, ANCHO_CAMPOS, 52, "Cambiar contraseña")
boton_paso2_volver = Boton(X_2, PANEL_2.y + 615, ANCHO_CAMPOS, 52, "Volver")


def dibujar_rec_nueva(estado):
    """Dibuja la pantalla donde se escribe el código y la nueva contraseña."""
    dibujar_panel(PANEL_2)
    centro_x = PANEL_2.centerx

    dibujar_texto_centrado("Crea tu nueva contraseña", FUENTE_TITULO, AZUL_CLARO,
                           centro_x, PANEL_2.y + 40)
    dibujar_texto_centrado("Si el correo está registrado, te enviamos un código.",
                           FUENTE_ERROR, AZUL_CLARO, centro_x, PANEL_2.y + 100)
    dibujar_texto_centrado(f"Es válido por {MINUTOS_VALIDEZ_RECUPERACION} minutos.",
                           FUENTE_ERROR, AZUL_CLARO, centro_x, PANEL_2.y + 122)

    for campo in CAMPOS_PASO_2:
        campo.dibujar(VENTANA)

    boton_cambiar.dibujar(VENTANA)
    dibujar_mensaje(estado, centro_x, PANEL_2.y + 575)
    boton_paso2_volver.dibujar(VENTANA)


def eventos_rec_nueva(evento, estado):
    presiono_enter = manejar_teclado_campos(evento, CAMPOS_PASO_2)

    # Botón "Cambiar contraseña" (o ENTER)
    if boton_cambiar.fue_presionado(evento) or presiono_enter:
        if restablecer_contrasena(campo_rec_codigo, campo_rec_nueva,
                                  campo_rec_confirmar, estado.correo_recuperacion):
            # Contraseña cambiada -> volvemos al login con un mensaje verde
            ir_a(estado, "login")
            estado.poner_mensaje("Contraseña actualizada. Ya puedes iniciar sesión.", VERDE)

    # Botón "Volver": regresa al paso 1
    if boton_paso2_volver.fue_presionado(evento):
        ir_a(estado, "rec_solicitud")


def al_entrar_rec_nueva(estado):
    """Al entrar, los tres campos empiezan vacíos."""
    for campo in CAMPOS_PASO_2:
        campo.limpiar()


# ---------------------------------------------------------------------
# REGISTRO DE LAS DOS PANTALLAS
# ---------------------------------------------------------------------
registrar_pantalla("rec_solicitud", dibujar_rec_solicitud, eventos_rec_solicitud,
                   campos=[campo_rec_correo], al_entrar=al_entrar_rec_solicitud)
registrar_pantalla("rec_nueva", dibujar_rec_nueva, eventos_rec_nueva,
                   campos=CAMPOS_PASO_2, al_entrar=al_entrar_rec_nueva)