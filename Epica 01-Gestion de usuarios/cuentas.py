# =====================================================================
#  cuentas.py  -  LÓGICA DE LAS CUENTAS DE USUARIO
# =====================================================================
#  Aquí está lo que "pasa" cuando el usuario presiona un botón, sin dibujar
#  nada (el dibujo está en los archivos pantalla_*.py):
#
#     US-01  procesar_registro()
#     US-02  procesar_verificacion(), reenviar_codigo_verificacion()
#     US-03  procesar_login()
#     US-05  solicitar_recuperacion(), restablecer_contrasena()
#
#  Las funciones reciben los CampoTexto de la pantalla, leen su texto y
#  escriben los errores en campo.error para que se muestren en rojo.
# =====================================================================

import secrets
import time

from config import (MINUTOS_VALIDEZ_CODIGO, MINUTOS_VALIDEZ_RECUPERACION,
                    MAX_INTENTOS_RECUPERACION)
from base_datos import (cargar_usuarios, guardar_usuarios, hashear_contrasena,
                        contrasena_correcta, buscar_duplicados, buscar_cuenta,
                        buscar_cuenta_por_correo)
from validaciones import (validar_usuario, validar_formato_correo, validar_contrasena,
                          validar_confirmacion, validar_correo_con_api)
from correo import enviar_correo_codigo, enviar_correo_recuperacion
from perfil_datos import campos_perfil_iniciales
from api_servidor import (
    registrar,
    verificar,
    login,
    solicitar_recuperacion as solicitar_remoto,
    restablecer,
    reenviar_verificacion as reenviar_remoto,
)


def generar_codigo():
    """Genera un código aleatorio de 6 dígitos (como texto)."""
    return str(secrets.randbelow(900000) + 100000)


# ---------------------------------------------------------------------
# US-01 REGISTRO
# ---------------------------------------------------------------------
def procesar_registro(campo_usuario, campo_correo, campo_clave, campo_confirmar):
    """
    Se ejecuta al presionar "Crear cuenta". Pasos:
      1. Validar campos (obligatorios, formato, contraseña, coincidencia)
      2. Revisar en usuarios.json que usuario y correo no existan
      3. Validar el correo con la API
      4. Enviar el correo con el código
      5. Guardar la cuenta en usuarios.json (aún sin verificar)

    Devuelve (nombre_de_usuario_creado_o_None, mensaje_general_de_error).
    Los errores de cada campo se guardan en campo.error.
    """
    campos = (campo_usuario, campo_correo, campo_clave, campo_confirmar)
    for campo in campos:
        campo.error = ""

    # Leemos lo que escribió el usuario (strip() quita espacios al inicio/final)
    usuario = campo_usuario.texto.strip()
    correo = campo_correo.texto.strip()
    clave = campo_clave.texto
    confirmacion = campo_confirmar.texto

    # --- Paso 1: validaciones locales ---
    campo_usuario.error = validar_usuario(usuario)
    campo_correo.error = validar_formato_correo(correo)
    campo_clave.error = validar_contrasena(clave)
    campo_confirmar.error = validar_confirmacion(clave, confirmacion)
    if any(campo.error for campo in campos):
        return None, ""

    try:
        respuesta = registrar(usuario, correo, clave)
    except ValueError as error:
        mensaje = str(error)
        if "usuario" in mensaje.lower():
            campo_usuario.error = mensaje
        elif "correo" in mensaje.lower():
            campo_correo.error = mensaje
        else:
            return None, mensaje
        return None, ""
    # El servidor solo devuelve el código en modo demo (EXPOSE_CODES=1).
    codigo = respuesta.get("codigo_verificacion")
    if codigo:
        return usuario, f"Cuenta creada. Código de verificación: {codigo}"
    return usuario, "Cuenta creada. Revisa tu correo para obtener el código de verificación."


# ---------------------------------------------------------------------
# US-02 VERIFICACIÓN DEL CORREO
# ---------------------------------------------------------------------
def procesar_verificacion(campo_codigo, nombre_usuario):
    """
    Se ejecuta al presionar "Confirmar" en la pantalla de verificación.
    Compara el código escrito con el guardado en usuarios.json.
    Devuelve True si la verificación fue exitosa.
    """
    campo_codigo.error = ""
    codigo = campo_codigo.texto.strip()

    if not codigo:
        campo_codigo.error = "Escribe el código que te enviamos."
        return False

    try:
        verificar(nombre_usuario, codigo)
        return True
    except ValueError as error:
        campo_codigo.error = str(error)
        return False


def reenviar_codigo_verificacion(cuenta):
    """
    Genera y envía un código de verificación NUEVO a una cuenta existente.
    Se usa cuando alguien intenta iniciar sesión con el correo sin verificar
    (así no se queda atascado si perdió el primer código).
    Devuelve (se_envio, mensaje_de_error).
    """
    try:
        respuesta = reenviar_remoto(cuenta["usuario"])
        if respuesta.get("ya_verificado"):
            return True, ""
        # El servidor conserva el código para la función de verificación.
        return True, ""
    except ValueError as error:
        return False, str(error)


# ---------------------------------------------------------------------
# US-03 INICIO DE SESIÓN
# ---------------------------------------------------------------------
def procesar_login(campo_ident, campo_clave):
    """
    Se ejecuta al presionar "Iniciar sesión". Pasos:
      1. Comprobar que los campos no estén vacíos
      2. Buscar la cuenta por usuario o correo y comprobar la contraseña
      3. Comprobar que el correo esté verificado

    Devuelve (resultado, mensaje, cuenta) donde resultado es:
      "ok"            -> credenciales correctas y correo verificado
      "no_verificado" -> credenciales correctas, pero falta verificar el correo
      "error"         -> algo falló (el mensaje explica qué)
    """
    campo_ident.error = ""
    campo_clave.error = ""

    identificador = campo_ident.texto.strip()
    clave = campo_clave.texto

    # --- Paso 1: campos obligatorios ---
    if not identificador:
        campo_ident.error = "Escribe tu usuario o correo electrónico."
    if not clave:
        campo_clave.error = "Escribe tu contraseña."
    if campo_ident.error or campo_clave.error:
        return "error", "", None

    # --- Paso 2: buscar cuenta y comprobar contraseña ---
    try:
        respuesta = login(identificador, clave)
    except ValueError as error:
        return "error", str(error), None

    if respuesta.get("no_verificado"):
        return "no_verificado", "", {
            "usuario": respuesta["usuario"],
            "correo": respuesta.get("correo", ""),
            "correo_verificado": False,
        }

    cuenta = {
        "usuario": respuesta["usuario"],
        "correo": respuesta.get("correo", ""),
        "avatar": respuesta.get("avatar", "default"),
        "correo_verificado": True,
        "token": respuesta["token"],
    }
    return "ok", "", cuenta


# ---------------------------------------------------------------------
# US-05 RECUPERACIÓN DE CONTRASEÑA
# ---------------------------------------------------------------------
# Flujo:
#   1) El usuario escribe su correo -> se envía un código al correo.
#   2) El usuario escribe el código y define la nueva contraseña.
#   El código expira solo a los MINUTOS_VALIDEZ_RECUPERACION minutos.
#
# Nota: en una página web se enviaría un "enlace". Como este es un programa de
# escritorio (no hay una web a la que apuntar), el correo lleva un CÓDIGO que el
# jugador escribe en el juego. Cumple lo mismo: es de un solo uso y expira.

def solicitar_recuperacion(campo_correo):
    """
    Se ejecuta al presionar "Enviar código" en la pantalla de recuperación.
    Devuelve (todo_bien, mensaje_general_de_error).

    Por seguridad, si el correo NO está registrado devolvemos "todo_bien" igual
    (sin enviar nada). Así nadie puede usar esta pantalla para descubrir qué
    correos tienen cuenta.
    """
    campo_correo.error = ""
    correo = campo_correo.texto.strip()

    # Validamos el formato antes de buscar nada
    campo_correo.error = validar_formato_correo(correo)
    if campo_correo.error:
        return False, ""

    try:
        solicitar_remoto(correo)
        return True, ""
    except ValueError as error:
        return False, str(error)


def _borrar_codigo_recuperacion(cuenta):
    """Elimina de la cuenta los datos del código de recuperación (ya usado o vencido)."""
    cuenta.pop("recuperacion_codigo", None)
    cuenta.pop("recuperacion_expira", None)
    cuenta.pop("recuperacion_intentos", None)


def restablecer_contrasena(campo_codigo, campo_nueva, campo_confirmar, correo):
    """
    Se ejecuta al presionar "Cambiar contraseña". Comprueba el código y, si es
    correcto y no ha expirado, guarda la nueva contraseña.
    Devuelve True si la contraseña fue cambiada.
    """
    campos = (campo_codigo, campo_nueva, campo_confirmar)
    for campo in campos:
        campo.error = ""

    codigo = campo_codigo.texto.strip()
    nueva = campo_nueva.texto
    confirmacion = campo_confirmar.texto

    # --- Validaciones de los campos ---
    if not codigo:
        campo_codigo.error = "Escribe el código que te enviamos."
    campo_nueva.error = validar_contrasena(nueva)
    campo_confirmar.error = validar_confirmacion(nueva, confirmacion)
    if any(campo.error for campo in campos):
        return False

    try:
        restablecer(correo, codigo, nueva)
        return True
    except ValueError as error:
        campo_codigo.error = str(error)
        return False