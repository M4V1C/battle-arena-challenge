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

    # --- Paso 2: usuario y correo únicos ---
    usuarios = cargar_usuarios()
    error_usuario, error_correo, cuenta_pendiente = buscar_duplicados(usuarios, usuario, correo)
    campo_usuario.error = error_usuario
    campo_correo.error = error_correo
    if error_usuario or error_correo:
        return None, ""

    # --- Paso 3: validar el correo con la API ---
    es_valido, mensaje = validar_correo_con_api(correo)
    if not es_valido:
        campo_correo.error = mensaje
        return None, ""

    # --- Paso 4: enviar el correo con el código ---
    codigo = generar_codigo()
    se_envio, error_envio = enviar_correo_codigo(correo, usuario, codigo)
    if not se_envio:
        return None, error_envio

    # --- Paso 5: guardar en usuarios.json ---
    sal, hash_contrasena = hashear_contrasena(clave)
    cuenta = {
        "usuario": usuario,
        "correo": correo,
        "contrasena_sal": sal,
        "contrasena_hash": hash_contrasena,
        "correo_verificado": False,
        "codigo_verificacion": codigo,
        "codigo_expira": time.time() + MINUTOS_VALIDEZ_CODIGO * 60,
    }
    cuenta.update(campos_perfil_iniciales())     # avatar, fecha de registro, estadísticas...

    if cuenta_pendiente is not None:
        # Era un reintento: quitamos el registro viejo para reemplazarlo
        usuarios = [u for u in usuarios if u is not cuenta_pendiente]
    usuarios.append(cuenta)
    guardar_usuarios(usuarios)
    return usuario, ""


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

    usuarios = cargar_usuarios()
    for u in usuarios:
        if u.get("usuario") != nombre_usuario:
            continue

        # Si ya estaba verificada, no hay nada más que hacer
        if u.get("correo_verificado"):
            return True

        # ¿Expiró el código?
        if time.time() > u.get("codigo_expira", 0):
            campo_codigo.error = "El código expiró. Vuelve atrás y crea la cuenta de nuevo."
            return False

        # ¿Es el código correcto?
        if codigo != str(u.get("codigo_verificacion")):
            campo_codigo.error = "El código es incorrecto."
            return False

        # ¡Correcto! Cambiamos el estado de la cuenta a "Correo verificado"
        u["correo_verificado"] = True
        u.pop("codigo_verificacion", None)     # Ya no hace falta guardar el código
        u.pop("codigo_expira", None)
        guardar_usuarios(usuarios)
        return True

    campo_codigo.error = "No se encontró la cuenta."
    return False


def reenviar_codigo_verificacion(cuenta):
    """
    Genera y envía un código de verificación NUEVO a una cuenta existente.
    Se usa cuando alguien intenta iniciar sesión con el correo sin verificar
    (así no se queda atascado si perdió el primer código).
    Devuelve (se_envio, mensaje_de_error).
    """
    codigo = generar_codigo()
    se_envio, error = enviar_correo_codigo(cuenta["correo"], cuenta["usuario"], codigo)
    if not se_envio:
        return False, error

    # Guardamos el código nuevo en usuarios.json
    usuarios = cargar_usuarios()
    for u in usuarios:
        if u.get("usuario") == cuenta["usuario"]:
            u["codigo_verificacion"] = codigo
            u["codigo_expira"] = time.time() + MINUTOS_VALIDEZ_CODIGO * 60
    guardar_usuarios(usuarios)
    return True, ""


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
    # Si el usuario no existe O la contraseña falla, damos el MISMO mensaje:
    # así nadie puede averiguar qué usuarios existen probando nombres.
    cuenta = buscar_cuenta(cargar_usuarios(), identificador)
    if cuenta is None or not contrasena_correcta(cuenta, clave):
        return "error", "Usuario o contraseña incorrectos.", None

    # --- Paso 3: correo verificado ---
    if not cuenta.get("correo_verificado", False):
        return "no_verificado", "", cuenta

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

    usuarios = cargar_usuarios()
    cuenta = buscar_cuenta_por_correo(usuarios, correo)

    if cuenta is not None:
        codigo = generar_codigo()
        se_envio, error_envio = enviar_correo_recuperacion(correo, cuenta["usuario"], codigo)
        if not se_envio:
            return False, error_envio

        # Guardamos el código en la cuenta, con su caducidad y contador de intentos
        # (en un proyecto real el código también se guardaría hasheado)
        cuenta["recuperacion_codigo"] = codigo
        cuenta["recuperacion_expira"] = time.time() + MINUTOS_VALIDEZ_RECUPERACION * 60
        cuenta["recuperacion_intentos"] = 0
        guardar_usuarios(usuarios)

    return True, ""


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

    # --- Buscamos la cuenta y su código de recuperación ---
    mensaje_invalido = "El código es incorrecto o ya expiró."
    usuarios = cargar_usuarios()
    cuenta = buscar_cuenta_por_correo(usuarios, correo)

    if cuenta is None or "recuperacion_codigo" not in cuenta:
        campo_codigo.error = mensaje_invalido
        return False

    # ¿Expiró? Si sí, lo borramos para que no se pueda usar nunca más
    if time.time() > cuenta.get("recuperacion_expira", 0):
        _borrar_codigo_recuperacion(cuenta)
        guardar_usuarios(usuarios)
        campo_codigo.error = mensaje_invalido
        return False

    # ¿Demasiados intentos fallidos? Invalidamos el código (evita adivinarlo)
    if cuenta.get("recuperacion_intentos", 0) >= MAX_INTENTOS_RECUPERACION:
        _borrar_codigo_recuperacion(cuenta)
        guardar_usuarios(usuarios)
        campo_codigo.error = "Demasiados intentos. Solicita un código nuevo."
        return False

    # ¿Es el código correcto?
    if codigo != str(cuenta["recuperacion_codigo"]):
        cuenta["recuperacion_intentos"] = cuenta.get("recuperacion_intentos", 0) + 1
        guardar_usuarios(usuarios)
        campo_codigo.error = mensaje_invalido
        return False

    # --- ¡Correcto! Guardamos la nueva contraseña (con una sal nueva) ---
    sal, hash_contrasena = hashear_contrasena(nueva)
    cuenta["contrasena_sal"] = sal
    cuenta["contrasena_hash"] = hash_contrasena
    _borrar_codigo_recuperacion(cuenta)          # El código es de un solo uso
    guardar_usuarios(usuarios)
    return True