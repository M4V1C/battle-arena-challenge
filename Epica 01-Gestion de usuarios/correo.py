# =====================================================================
#  correo.py  -  ENVÍO DE CORREOS
# =====================================================================
#  Contiene:
#     enviar_correo()               -> función base (arma y envía cualquier correo)
#     enviar_correo_codigo()        -> correo de VERIFICACIÓN de cuenta (US-02)
#     enviar_correo_recuperacion()  -> correo de RECUPERACIÓN de contraseña (US-05)
#
#  Los datos del servidor (usuario, clave, remitente) están en config.py.
# =====================================================================

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr     # Para mostrar "Nombre <correo>" como remitente

from config import (NOMBRE_JUEGO, SMTP_SERVIDOR, SMTP_PUERTO, SMTP_USUARIO,
                    SMTP_CLAVE, CORREO_REMITENTE,
                    MINUTOS_VALIDEZ_CODIGO, MINUTOS_VALIDEZ_RECUPERACION)


def enviar_correo(destino, asunto, cuerpo):
    """
    Función base: envía un correo de texto simple por SMTP.
    Devuelve (se_envio, mensaje_de_error).
    """
    # Comprobamos que el programador haya configurado el correo emisor
    if "tu_correo" in SMTP_USUARIO:
        return False, "Configura SMTP_USUARIO y SMTP_CLAVE en config.py."

    # Armamos el correo. El remitente se verá como "Control del Reactor"
    mensaje = EmailMessage()
    mensaje["Subject"] = asunto
    mensaje["From"] = formataddr((NOMBRE_JUEGO, CORREO_REMITENTE))
    mensaje["To"] = destino
    mensaje.set_content(cuerpo)

    # Nos conectamos al servidor, activamos cifrado, iniciamos sesión y enviamos
    try:
        contexto = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVIDOR, SMTP_PUERTO, timeout=15) as servidor:
            servidor.starttls(context=contexto)
            servidor.login(SMTP_USUARIO, SMTP_CLAVE)
            servidor.send_message(mensaje)
        return True, ""
    except smtplib.SMTPAuthenticationError as error:
        print(f"[ERROR SMTP] {error}")
        return False, "Error del servidor de correo: revisa SMTP_USUARIO y SMTP_CLAVE."
    except smtplib.SMTPRecipientsRefused as error:
        print(f"[ERROR SMTP] {error}")
        return False, "El servidor rechazó ese correo electrónico."
    except Exception as error:
        print(f"[ERROR SMTP] {error}")
        return False, "No se pudo enviar el correo. Revisa tu conexión."


def enviar_correo_codigo(destino, usuario, codigo):
    """Envía el correo con el código de VERIFICACIÓN de la cuenta (US-02)."""
    return enviar_correo(
        destino,
        f"{NOMBRE_JUEGO} - Tu código de verificación",
        f"Hola {usuario},\n\n"
        f"¡Bienvenido a {NOMBRE_JUEGO}!\n"
        f"Tu código de verificación es: {codigo}\n\n"
        f"Es válido por {MINUTOS_VALIDEZ_CODIGO} minutos.\n"
        f"Si no creaste una cuenta en {NOMBRE_JUEGO}, ignora este mensaje.\n\n"
        f"El equipo de {NOMBRE_JUEGO}"
    )


def enviar_correo_recuperacion(destino, usuario, codigo):
    """Envía el correo con el código para RECUPERAR la contraseña (US-05)."""
    return enviar_correo(
        destino,
        f"{NOMBRE_JUEGO} - Recuperación de contraseña",
        f"Hola {usuario},\n\n"
        f"Recibimos una solicitud para restablecer tu contraseña en {NOMBRE_JUEGO}.\n"
        f"Tu código de recuperación es: {codigo}\n\n"
        f"Es válido por {MINUTOS_VALIDEZ_RECUPERACION} minutos y deja de funcionar "
        "después de ese tiempo.\n"
        "Si no fuiste tú, ignora este mensaje: tu contraseña no cambiará.\n\n"
        f"El equipo de {NOMBRE_JUEGO}"
    )