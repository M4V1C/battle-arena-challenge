# =====================================================================
#  base_datos.py  -  LECTURA Y ESCRITURA DE usuarios.json
# =====================================================================
#  Todo lo que toca el archivo usuarios.json está aquí: leerlo, guardarlo,
#  buscar cuentas y manejar las contraseñas (hash).
#
#  El archivo contiene una LISTA de usuarios. Cada usuario es un diccionario:
#  {
#      "usuario": "juan",
#      "correo": "juan@correo.com",
#      "contrasena_sal": "...",          <- dato aleatorio usado para hashear
#      "contrasena_hash": "...",         <- la contraseña NUNCA se guarda en claro
#      "correo_verificado": true,
#      "avatar": "default",
#      "fecha_registro": "25/10/2026",
#      "estadisticas": {...},            <- ver perfil_datos.py
#      "logros": [...],                  <- ver logros.py
#      "historial": [...],               <- partidas jugadas
#      "codigo_verificacion": "123456",  <- solo existe mientras no se verifica
#      "codigo_expira": 1700000000.0,
#      "recuperacion_codigo": "654321",  <- solo existe si pidió recuperar contraseña
#      "recuperacion_expira": 1700000000.0,
#      "recuperacion_intentos": 0
#  }
# =====================================================================

import json
import os
import secrets
import hashlib
import shutil

from config import ARCHIVO_USUARIOS


# ---------------------------------------------------------------------
# LEER Y GUARDAR
# ---------------------------------------------------------------------
def cargar_usuarios():
    """Lee usuarios.json y devuelve la lista de usuarios ([] si no hay nada)."""
    if not os.path.exists(ARCHIVO_USUARIOS):
        return []

    try:
        with open(ARCHIVO_USUARIOS, "r", encoding="utf-8") as archivo:
            contenido = archivo.read()
        if not contenido.strip():
            return []                          # Archivo vacío: empezamos de cero
        datos = json.loads(contenido)
    except json.JSONDecodeError:
        # El archivo está dañado. Antes de empezar de cero guardamos una copia
        # (usuarios.json.bak) para no perder los datos por accidente.
        try:
            shutil.copy(ARCHIVO_USUARIOS, ARCHIVO_USUARIOS + ".bak")
        except OSError:
            pass
        return []
    except OSError:
        return []

    return datos if isinstance(datos, list) else []


def guardar_usuarios(usuarios):
    """
    Escribe la lista completa de usuarios en usuarios.json.
    Primero escribe en un archivo temporal y luego lo renombra: así, si el
    programa se cierra a mitad de la escritura, usuarios.json no queda roto.
    """
    ruta_temporal = ARCHIVO_USUARIOS + ".tmp"
    with open(ruta_temporal, "w", encoding="utf-8") as archivo:
        json.dump(usuarios, archivo, indent=4, ensure_ascii=False)
    os.replace(ruta_temporal, ARCHIVO_USUARIOS)


# ---------------------------------------------------------------------
# CONTRASEÑAS
# ---------------------------------------------------------------------
def hashear_contrasena(contrasena, sal=None):
    """
    Convierte la contraseña en un 'hash' (un texto irreversible).
    Así, si alguien abre usuarios.json, no puede leer las contraseñas.
    Devuelve (sal, hash). Para comprobar una contraseña (login) se calcula el
    hash de lo que escriba el usuario con la MISMA sal y se compara.
    """
    if sal is None:
        sal = secrets.token_hex(16)            # Sal aleatoria única por usuario
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256", contrasena.encode("utf-8"), bytes.fromhex(sal), 200_000
    )
    return sal, hash_bytes.hex()


def contrasena_correcta(cuenta, contrasena):
    """True si 'contrasena' coincide con la guardada (comparando hashes) en 'cuenta'."""
    sal = cuenta.get("contrasena_sal")
    hash_guardado = cuenta.get("contrasena_hash")
    if not sal or not hash_guardado:
        return False
    _, hash_calculado = hashear_contrasena(contrasena, sal)
    # compare_digest compara de forma segura (tarda lo mismo acierte o falle)
    return secrets.compare_digest(hash_calculado, hash_guardado)


# ---------------------------------------------------------------------
# BÚSQUEDAS
# ---------------------------------------------------------------------
def buscar_duplicados(usuarios, nombre, correo):
    """
    Recorre todos los usuarios guardados para comprobar que el nombre de
    usuario y el correo no estén ya registrados (CA-01.2 y CA-01.3).

    Devuelve (error_usuario, error_correo, cuenta_pendiente).
    'cuenta_pendiente' es una cuenta con el MISMO usuario y correo que aún no
    verificó su correo: permite reintentar el registro (por ejemplo si el
    usuario presionó "Volver") sin quedar bloqueado por su propio registro.
    """
    error_usuario = ""
    error_correo = ""
    cuenta_pendiente = None

    for u in usuarios:
        mismo_nombre = u.get("usuario", "").lower() == nombre.lower()
        mismo_correo = u.get("correo", "").lower() == correo.lower()

        if mismo_nombre and mismo_correo and not u.get("correo_verificado", False):
            cuenta_pendiente = u
            continue

        if mismo_nombre:
            error_usuario = "Este nombre de usuario ya está en uso."
        if mismo_correo:
            error_correo = "Este correo electrónico ya está registrado."

    return error_usuario, error_correo, cuenta_pendiente


def buscar_cuenta(usuarios, identificador):
    """
    Busca una cuenta por nombre de usuario O por correo (se usa en el login).
    Devuelve el diccionario de la cuenta, o None si no existe.
    """
    identificador = identificador.lower()
    for u in usuarios:
        if (u.get("usuario", "").lower() == identificador
                or u.get("correo", "").lower() == identificador):
            return u
    return None


def buscar_cuenta_por_usuario(usuarios, nombre_usuario):
    """Busca una cuenta solo por nombre de usuario."""
    for u in usuarios:
        if u.get("usuario", "").lower() == nombre_usuario.lower():
            return u
    return None


def buscar_cuenta_por_correo(usuarios, correo):
    """Busca una cuenta solo por correo (se usa en la recuperación de contraseña)."""
    for u in usuarios:
        if u.get("correo", "").lower() == correo.lower():
            return u
    return None