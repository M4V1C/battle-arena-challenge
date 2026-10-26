# =====================================================================
#  validaciones.py  -  REGLAS PARA LOS DATOS QUE ESCRIBE EL USUARIO
# =====================================================================
#  Todas las funciones validar_* devuelven un texto con el error, o ""
#  (texto vacío) si todo está bien. Así la pantalla puede mostrar
#  directamente el resultado bajo el campo correspondiente.
#
#  Este módulo no usa pygame: solo comprueba textos.
# =====================================================================

import json
import re
import urllib.parse
import urllib.request


def validar_usuario(usuario):
    if not usuario:
        return "El nombre de usuario es obligatorio."
    if len(usuario) < 3 or len(usuario) > 20:
        return "Debe tener entre 3 y 20 caracteres."
    if not re.fullmatch(r"[A-Za-z0-9_]+", usuario):
        return "Solo letras, números y guion bajo (_)."
    return ""


def validar_formato_correo(correo):
    """Validación local rápida del formato (antes de llamar a la API)."""
    if not correo:
        return "El correo electrónico es obligatorio."
    # Patrón: algo @ algo . algo   (sin espacios)
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo):
        return "El formato del correo no es válido."
    return ""


def validar_contrasena(contrasena):
    """Reglas mínimas: 8 caracteres, una mayúscula, una minúscula y un número."""
    if not contrasena:
        return "La contraseña es obligatoria."
    if len(contrasena) < 8:
        return "Debe tener al menos 8 caracteres."
    if not re.search(r"[A-Z]", contrasena):
        return "Debe incluir al menos una letra mayúscula."
    if not re.search(r"[a-z]", contrasena):
        return "Debe incluir al menos una letra minúscula."
    if not re.search(r"[0-9]", contrasena):
        return "Debe incluir al menos un número."
    return ""


def validar_confirmacion(contrasena, confirmacion):
    if not confirmacion:
        return "Debes confirmar la contraseña."
    if contrasena != confirmacion:
        return "Las contraseñas no coinciden."
    return ""


def validar_correo_con_api(correo):
    """
    Valida el correo usando la API gratuita de Disify (no necesita clave):
        https://disify.com/api/email/<correo>
    Responde un JSON como:
        {"format": true, "domain": "gmail.com", "disposable": false, "dns": true}
      - format:     el formato es válido
      - disposable: es un correo temporal/desechable
      - dns:        el dominio existe y puede recibir correos
    Devuelve (es_valido, mensaje_de_error).
    """
    url = "https://disify.com/api/email/" + urllib.parse.quote(correo)
    try:
        peticion = urllib.request.Request(url, headers={"User-Agent": "ControlDelReactor/1.0"})
        with urllib.request.urlopen(peticion, timeout=8) as respuesta:
            datos = json.loads(respuesta.read().decode("utf-8"))
    except Exception as error:
        # Si la API no responde (sin internet, límite de uso...) NO bloqueamos
        # el registro: el envío del correo será la prueba final.
        # Si prefieres bloquear, cambia esta línea por:
        #     return False, "No se pudo validar el correo. Intenta más tarde."
        print(f"[AVISO] No se pudo consultar la API de correo: {error}")
        return True, ""

    if not datos.get("format", True):
        return False, "El formato del correo no es válido."
    if datos.get("disposable", False):
        return False, "No se permiten correos temporales."
    if not datos.get("dns", True):
        return False, "El dominio de ese correo no existe."
    return True, ""