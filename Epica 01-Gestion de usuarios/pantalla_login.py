# =====================================================================
#  pantalla_login.py  -  PANTALLA "Iniciar sesión" (US-03)
# =====================================================================
#  El jugador escribe su usuario (o correo) y su contraseña.
#     - Credenciales correctas + correo verificado -> entra al área de juego
#     - Correo sin verificar -> no entra; se le avisa y se le envía un código nuevo
#     - Credenciales incorrectas -> mensaje de error
# =====================================================================

from config import MARGEN, ANCHO_CAMPOS, ALTO_CAMPO, SEPARACION, AZUL_CLARO
from recursos import VENTANA, FUENTE_TITULO, FUENTE_TEXTO
from componentes import (CampoTexto, Boton, EnlaceTexto, calcular_panel, dibujar_panel,
                         dibujar_texto_centrado, dibujar_mensaje,
                         manejar_teclado_campos)
from estado import registrar_pantalla, ir_a, mostrar_procesando
from sesion import SESION
from cuentas import procesar_login, reenviar_codigo_verificacion


# ---------------------------------------------------------------------
# 1) ELEMENTOS Y POSICIONES
# ---------------------------------------------------------------------
PANEL = calcular_panel(620)
X_CAMPOS = PANEL.x + MARGEN

campo_ident = CampoTexto(X_CAMPOS, PANEL.y + 140, ANCHO_CAMPOS, ALTO_CAMPO,
                         "Usuario o correo electrónico", max_caracteres=60)
campo_clave = CampoTexto(X_CAMPOS, PANEL.y + 140 + SEPARACION, ANCHO_CAMPOS, ALTO_CAMPO,
                         "Contraseña", es_contrasena=True, max_caracteres=40)
CAMPOS = [campo_ident, campo_clave]

enlace_olvido = EnlaceTexto(PANEL.centerx, PANEL.y + 332, "¿Olvidaste tu contraseña?")
boton_login = Boton(X_CAMPOS, PANEL.y + 375, ANCHO_CAMPOS, 52, "Iniciar sesión")
boton_ir_registro = Boton(X_CAMPOS, PANEL.y + 512, ANCHO_CAMPOS, 52, "Crear cuenta")


# ---------------------------------------------------------------------
# 2) DIBUJO
# ---------------------------------------------------------------------
def dibujar_login(estado):
    """Dibuja todos los elementos de la pantalla de inicio de sesión."""
    dibujar_panel(PANEL)
    centro_x = PANEL.centerx

    dibujar_texto_centrado("Iniciar sesión", FUENTE_TITULO, AZUL_CLARO, centro_x, PANEL.y + 40)

    for campo in CAMPOS:
        campo.dibujar(VENTANA)

    enlace_olvido.dibujar(VENTANA)
    boton_login.dibujar(VENTANA)
    dibujar_mensaje(estado, centro_x, PANEL.y + 440)

    dibujar_texto_centrado("¿No tienes cuenta? Regístrate", FUENTE_TEXTO, AZUL_CLARO,
                           centro_x, PANEL.y + 476)
    boton_ir_registro.dibujar(VENTANA)


# ---------------------------------------------------------------------
# 3) EVENTOS
# ---------------------------------------------------------------------
def eventos_login(evento, estado):
    presiono_enter = manejar_teclado_campos(evento, CAMPOS)

    # Botón "Iniciar sesión" (o ENTER)
    if boton_login.fue_presionado(evento) or presiono_enter:
        mostrar_procesando(estado)
        resultado, mensaje, cuenta = procesar_login(campo_ident, campo_clave)

        if resultado == "ok":
            # Credenciales correctas -> iniciamos la sesión y entramos al juego
            SESION.iniciar(cuenta)
            campo_ident.limpiar()
            campo_clave.limpiar()               # No dejamos la contraseña escrita
            ir_a(estado, "juego")

        elif resultado == "no_verificado":
            # Correo sin verificar -> NO entra. Le avisamos y le enviamos
            # un código nuevo para que pueda verificarlo desde aquí mismo.
            se_envio, _ = reenviar_codigo_verificacion(cuenta)
            if se_envio:
                estado.usuario_pendiente = cuenta["usuario"]
                estado.correo_pendiente = cuenta["correo"]
                estado.pantalla_anterior = "login"
                estado.verificado = False
                campo_clave.limpiar()
                ir_a(estado, "verificacion")
                estado.aviso_verificacion = ("Tu correo aún no está verificado. "
                                             "Te enviamos un nuevo código.")
            else:
                estado.poner_mensaje("Correo no verificado. No se pudo enviar el nuevo código.")

        else:
            # Credenciales incorrectas (o campos vacíos)
            estado.poner_mensaje(mensaje)

    # Enlace "¿Olvidaste tu contraseña?"
    if enlace_olvido.fue_presionado(evento):
        ir_a(estado, "rec_solicitud")

    # Botón "Crear cuenta": vuelve al registro
    if boton_ir_registro.fue_presionado(evento):
        ir_a(estado, "registro")


# ---------------------------------------------------------------------
# REGISTRO DE LA PANTALLA
# ---------------------------------------------------------------------
registrar_pantalla("login", dibujar_login, eventos_login, campos=CAMPOS)