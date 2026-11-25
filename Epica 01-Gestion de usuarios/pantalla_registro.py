# =====================================================================
#  pantalla_registro.py  -  PANTALLA "¿Eres nuevo? Crea tu cuenta" (US-01)
# =====================================================================
#  Contiene tres partes:
#     1) Los ELEMENTOS de la pantalla (campos y botones) con su posición
#     2) La función que la DIBUJA
#     3) La función que maneja sus EVENTOS (clics y teclas)
#  Al final se REGISTRA en estado.py para que el programa pueda usarla.
# =====================================================================

from config import (MARGEN, ANCHO_CAMPOS, ALTO_CAMPO, SEPARACION, AZUL_CLARO)
from recursos import VENTANA, FUENTE_TITULO, FUENTE_TEXTO
from componentes import (CampoTexto, Boton, calcular_panel, dibujar_panel,
                         dibujar_texto_centrado, dibujar_mensaje,
                         manejar_teclado_campos)
from estado import registrar_pantalla, ir_a, mostrar_procesando
from cuentas import procesar_registro


# ---------------------------------------------------------------------
# 1) ELEMENTOS Y POSICIONES
# ---------------------------------------------------------------------
PANEL = calcular_panel(780)
X_CAMPOS = PANEL.x + MARGEN
Y_PRIMER_CAMPO = PANEL.y + 140

campo_usuario = CampoTexto(X_CAMPOS, Y_PRIMER_CAMPO + SEPARACION * 0, ANCHO_CAMPOS, ALTO_CAMPO,
                           "Nombre de usuario", max_caracteres=20)
campo_correo = CampoTexto(X_CAMPOS, Y_PRIMER_CAMPO + SEPARACION * 1, ANCHO_CAMPOS, ALTO_CAMPO,
                          "Correo electrónico", max_caracteres=60)
campo_clave = CampoTexto(X_CAMPOS, Y_PRIMER_CAMPO + SEPARACION * 2, ANCHO_CAMPOS, ALTO_CAMPO,
                         "Contraseña", es_contrasena=True, max_caracteres=40)
campo_confirmar = CampoTexto(X_CAMPOS, Y_PRIMER_CAMPO + SEPARACION * 3, ANCHO_CAMPOS, ALTO_CAMPO,
                             "Confirmar contraseña", es_contrasena=True, max_caracteres=40)
CAMPOS = [campo_usuario, campo_correo, campo_clave, campo_confirmar]

boton_crear = Boton(X_CAMPOS, PANEL.y + 560, ANCHO_CAMPOS, 52, "Crear cuenta")
boton_ir_login = Boton(X_CAMPOS, PANEL.y + 690, ANCHO_CAMPOS, 52, "Iniciar sesión")


# ---------------------------------------------------------------------
# 2) DIBUJO
# ---------------------------------------------------------------------
def dibujar_registro(estado):
    """Dibuja todos los elementos de la pantalla de registro."""
    dibujar_panel(PANEL)
    centro_x = PANEL.centerx

    dibujar_texto_centrado("¿Eres nuevo? Crea tu cuenta", FUENTE_TITULO, AZUL_CLARO,
                           centro_x, PANEL.y + 40)

    for campo in CAMPOS:
        campo.dibujar(VENTANA)

    boton_crear.dibujar(VENTANA)
    dibujar_mensaje(estado, centro_x, PANEL.y + 622)

    dibujar_texto_centrado("¿Ya tienes una cuenta? Inicia sesión", FUENTE_TEXTO, AZUL_CLARO,
                           centro_x, PANEL.y + 654)
    boton_ir_login.dibujar(VENTANA)


# ---------------------------------------------------------------------
# 3) EVENTOS
# ---------------------------------------------------------------------
def eventos_registro(evento, estado):
    presiono_enter = manejar_teclado_campos(evento, CAMPOS)

    # Botón "Crear cuenta" (o ENTER)
    if boton_crear.fue_presionado(evento) or presiono_enter:
        mostrar_procesando(estado)          # La tarea siguiente es lenta
        creado, mensaje = procesar_registro(
            campo_usuario, campo_correo, campo_clave, campo_confirmar)

        if creado:
            # Todo salió bien: pasamos a la pantalla de verificación
            estado.usuario_pendiente = creado
            estado.correo_pendiente = campo_correo.texto.strip()
            estado.pantalla_anterior = "registro"
            estado.verificado = False
            ir_a(estado, "verificacion")
        else:
            estado.poner_mensaje(mensaje)

    # Botón "Iniciar sesión": nos lleva a la pantalla de login
    if boton_ir_login.fue_presionado(evento):
        ir_a(estado, "login")


def al_entrar_registro(estado):
    """
    Se ejecuta cada vez que se entra a esta pantalla. Si el registro ya terminó
    (la cuenta fue verificada), deja el formulario vacío para el próximo uso.
    """
    if estado.limpiar_registro:
        for campo in CAMPOS:
            campo.limpiar()
        estado.limpiar_registro = False


# ---------------------------------------------------------------------
# REGISTRO DE LA PANTALLA (se ejecuta al importar este archivo)
# ---------------------------------------------------------------------
registrar_pantalla("registro", dibujar_registro, eventos_registro,
                   campos=CAMPOS, al_entrar=al_entrar_registro)