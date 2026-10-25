# =====================================================================
#  CONTROL DEL REACTOR
#  US-01 Registro de usuario
#  US-02 Verificación del correo electrónico
#  US-03 Inicio de sesión
#  US-05 Recuperación de contraseña
# =====================================================================
#
#  Cómo está organizado este archivo (de arriba hacia abajo):
#     1. IMPORTACIONES
#     2. CONFIGURACIÓN (tamaños, colores, correo, archivo .json)
#     3. INICIALIZACIÓN DE PYGAME (ventana y fuentes)
#     4. BASE DE DATOS (leer/escribir usuarios.json y buscar cuentas)
#     5. VALIDACIONES (usuario, correo, contraseña, API de correo)
#     6. ENVÍO DE CORREOS (verificación y recuperación)
#     7. SESIÓN DEL JUGADOR (quién ha iniciado sesión)
#     8. COMPONENTES VISUALES (CampoTexto, Boton, EnlaceTexto, avatar)
#     9. LÓGICA DE CADA PANTALLA (registro, verificación, login, recuperación)
#    10. ELEMENTOS Y DIBUJO DE CADA PANTALLA
#    11. MANEJO DE EVENTOS DE CADA PANTALLA
#    12. BUCLE PRINCIPAL (el "corazón" de todo juego en pygame)
#
#  PANTALLAS DEL PROGRAMA (cada una es un "estado" del programa):
#     "registro"      -> crear cuenta
#     "verificacion"  -> escribir el código enviado al correo
#     "login"         -> iniciar sesión
#     "rec_solicitud" -> pedir el código de recuperación de contraseña
#     "rec_nueva"     -> escribir el código y la nueva contraseña
#     "juego"         -> área de juego (solo con sesión iniciada)
#
# =====================================================================


# =====================================================================
# 1. IMPORTACIONES
# =====================================================================
import pygame                      # La librería del juego
import json                        # Para leer/escribir usuarios.json
import os                          # Para construir la ruta del archivo .json
import re                          # Expresiones regulares (validar formatos)
import math                        # Seno y coseno (para dibujar el avatar)
import time                        # Para saber cuándo expira un código
import hashlib                     # Para "encriptar" (hashear) las contraseñas
import secrets                     # Para generar códigos y sales aleatorias seguras
import smtplib                     # Para enviar correos (protocolo SMTP)
import ssl                         # Conexión segura con el servidor de correo
import urllib.request              # Para llamar a la API de validación de correo
import urllib.parse                # Para codificar el correo dentro de la URL
from email.message import EmailMessage   # Para armar el correo
from email.utils import formataddr


# =====================================================================
# 2. CONFIGURACIÓN
# =====================================================================

# --- Ventana ---
ANCHO = 1600
ALTO = 900
FPS = 60                           # Cuadros por segundo del juego

# --- Colores (formato RGB: rojo, verde, azul; cada uno de 0 a 255) ---
NEGRO = (0, 0, 0)
AZUL_CLARO = (100, 200, 255)       # Líneas, textos y bordes
AZUL_OSCURO = (0, 45, 70)          # Fondo de un botón cuando pasas el mouse encima
AZUL_HOVER = (200, 235, 255)       # Color de un enlace de texto con el mouse encima
ROJO = (255, 70, 70)               # Mensajes de error
VERDE = (90, 230, 130)             # Mensajes de éxito

# --- Archivo donde se guardan los usuarios ---
# Se guarda junto a este script, sin importar desde dónde lo ejecutes.
ARCHIVO_USUARIOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "usuarios.json")

# --- Servidor de correo (SMTP) ---
# IMPORTANTE: aquí pones el correo DESDE el que se enviarán los códigos.
# Ejemplo con Gmail: necesitas activar la verificación en 2 pasos y crear una
# "contraseña de aplicación" (NO uses tu contraseña normal de Gmail).
# Más seguro: guardarlas como variables de entorno en vez de escribirlas aquí.
SMTP_SERVIDOR = "smtp.gmail.com"
SMTP_PUERTO = 587
SMTP_USUARIO = os.environ.get("REACTOR_SMTP_USER", "andrewbp32@gmail.com")
SMTP_CLAVE = os.environ.get("REACTOR_SMTP_PASS", "orwa vues mppv ijbk")

# --- Códigos de verificación y de recuperación ---
MINUTOS_VALIDEZ_CODIGO = 15        # Después de este tiempo el código de verificación expira
MINUTOS_VALIDEZ_RECUPERACION = 15  # Después de este tiempo el código de recuperación expira
MAX_INTENTOS_RECUPERACION = 5      # Códigos incorrectos permitidos antes de invalidarlo

NOMBRE_JUEGO = "Control del Reactor"
CORREO_REMITENTE = SMTP_USUARIO      # El correo desde el que se envía

# =====================================================================
# 3. INICIALIZACIÓN DE PYGAME
# =====================================================================
pygame.init()
VENTANA = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Control del Reactor")
RELOJ = pygame.time.Clock()        # Sirve para limitar los FPS

pygame.key.start_text_input()      # Activa los eventos de escritura (TEXTINPUT)
pygame.key.set_repeat(400, 40)     # Mantener presionada una tecla la repite

# Fuentes (nombre, tamaño). Si "arial" no existe, pygame usa otra por defecto.
FUENTE_TITULO = pygame.font.SysFont("arial", 34, bold=True)
FUENTE_TEXTO = pygame.font.SysFont("arial", 22)
FUENTE_ETIQUETA = pygame.font.SysFont("arial", 18)
FUENTE_ERROR = pygame.font.SysFont("arial", 16)   # Pequeña pero legible


# =====================================================================
# 4. BASE DE DATOS (usuarios.json)
# =====================================================================
# El archivo contiene una LISTA de usuarios. Cada usuario es un diccionario:
# {
#     "usuario": "juan",
#     "correo": "juan@correo.com",
#     "contrasena_sal": "...",        <- dato aleatorio usado para hashear
#     "contrasena_hash": "...",       <- la contraseña NUNCA se guarda en claro
#     "avatar": "default",            <- avatar del jugador (se podrá cambiar luego)
#     "correo_verificado": false,
#     "codigo_verificacion": "123456",      <- solo existe mientras no se verifica
#     "codigo_expira": 1700000000.0,
#     "recuperacion_codigo": "654321",      <- solo existe si pidió recuperar contraseña
#     "recuperacion_expira": 1700000000.0,
#     "recuperacion_intentos": 0
# }

def cargar_usuarios():
    """Lee usuarios.json y devuelve la lista de usuarios ([] si no hay nada)."""
    if not os.path.exists(ARCHIVO_USUARIOS):
        return []
    try:
        with open(ARCHIVO_USUARIOS, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except (json.JSONDecodeError, OSError):
        return []                  # Archivo vacío o dañado: empezamos de cero
    return datos if isinstance(datos, list) else []


def guardar_usuarios(usuarios):
    """Escribe la lista completa de usuarios en usuarios.json."""
    with open(ARCHIVO_USUARIOS, "w", encoding="utf-8") as archivo:
        json.dump(usuarios, archivo, indent=4, ensure_ascii=False)


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
    Busca una cuenta por nombre de usuario O por correo (CA-03.1).
    Devuelve el diccionario de la cuenta, o None si no existe.
    """
    identificador = identificador.lower()
    for u in usuarios:
        if (u.get("usuario", "").lower() == identificador
                or u.get("correo", "").lower() == identificador):
            return u
    return None


def buscar_cuenta_por_correo(usuarios, correo):
    """Busca una cuenta solo por correo (se usa en la recuperación de contraseña)."""
    for u in usuarios:
        if u.get("correo", "").lower() == correo.lower():
            return u
    return None


# =====================================================================
# 5. VALIDACIONES
# =====================================================================
# Todas devuelven un texto con el error, o "" (texto vacío) si todo está bien.

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


# =====================================================================
# 6. ENVÍO DE CORREOS
# =====================================================================

def generar_codigo():
    """Genera un código aleatorio de 6 dígitos (como texto)."""
    return str(secrets.randbelow(900000) + 100000)


def enviar_correo(destino, asunto, cuerpo):
    """
    Función base: envía un correo de texto simple por SMTP.
    Devuelve (se_envio, mensaje_de_error).
    """
    # Comprobamos que el programador haya configurado el correo emisor
    if "tu_correo" in SMTP_USUARIO:
        return False, "Configura SMTP_USUARIO y SMTP_CLAVE al inicio del archivo."

    # Armamos el correo
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
        "Tu código de verificación - Control del Reactor",
        f"Hola {usuario},\n\n"
        f"Tu código de verificación es: {codigo}\n\n"
        f"Es válido por {MINUTOS_VALIDEZ_CODIGO} minutos.\n"
        "Si no creaste una cuenta en Control del Reactor, ignora este mensaje."
    )


def enviar_correo_recuperacion(destino, usuario, codigo):
    """Envía el correo con el código para RECUPERAR la contraseña (US-05)."""
    return enviar_correo(
        destino,
        "Recuperación de contraseña - Control del Reactor",
        f"Hola {usuario},\n\n"
        "Recibimos una solicitud para restablecer tu contraseña.\n"
        f"Tu código de recuperación es: {codigo}\n\n"
        f"Es válido por {MINUTOS_VALIDEZ_RECUPERACION} minutos y deja de funcionar "
        "después de ese tiempo.\n"
        "Si no fuiste tú, ignora este mensaje: tu contraseña no cambiará."
    )


# =====================================================================
# 7. SESIÓN DEL JUGADOR
# =====================================================================
# La sesión guarda QUIÉN ha iniciado sesión. Como es un objeto que vive
# mientras el programa está abierto, se mantiene al cambiar de pantalla
# (CA-03.6). Al cerrar sesión se vacía.

class Sesion:
    def __init__(self):
        self.usuario = None        # Nombre del jugador (None = nadie ha iniciado sesión)
        self.correo = None
        self.avatar = "default"

    @property
    def activa(self):
        """True si hay un jugador autenticado."""
        return self.usuario is not None

    def iniciar(self, cuenta):
        """Guarda los datos del jugador (NUNCA guardamos su contraseña ni su hash)."""
        self.usuario = cuenta["usuario"]
        self.correo = cuenta["correo"]
        self.avatar = cuenta.get("avatar", "default")

    def cerrar(self):
        """Vacía la sesión."""
        self.usuario = None
        self.correo = None
        self.avatar = "default"


SESION = Sesion()                  # Una única sesión para todo el programa


# =====================================================================
# 8. COMPONENTES VISUALES
# =====================================================================

class CampoTexto:
    """
    Una caja donde el usuario escribe. Guarda:
      - su rectángulo (posición y tamaño),
      - el texto escrito,
      - si está 'activo' (si tiene el cursor),
      - el mensaje de error que se muestra debajo en rojo.
    """

    def __init__(self, x, y, ancho, alto, etiqueta, es_contrasena=False, max_caracteres=40):
        self.rect = pygame.Rect(x, y, ancho, alto)
        self.etiqueta = etiqueta             # Texto pequeño que aparece encima
        self.es_contrasena = es_contrasena   # Si True, se muestran asteriscos
        self.max_caracteres = max_caracteres
        self.texto = ""
        self.activo = False
        self.error = ""

    def manejar_evento(self, evento):
        """Recibe un evento de pygame y actúa si le corresponde."""
        # Clic izquierdo: el campo se activa solo si el clic cae dentro de él
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            self.activo = self.rect.collidepoint(evento.pos)

        # Si no está activo, ignora el teclado
        if not self.activo:
            return

        # TEXTINPUT: llega el carácter ya escrito (respeta acentos, ñ, mayúsculas)
        if evento.type == pygame.TEXTINPUT:
            if len(self.texto) < self.max_caracteres:
                self.texto += evento.text
                self.error = ""              # Al escribir, se borra el error viejo

        # Retroceso: borra el último carácter
        elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_BACKSPACE:
            self.texto = self.texto[:-1]
            self.error = ""

    def limpiar(self):
        """Deja el campo vacío y sin error."""
        self.texto = ""
        self.error = ""

    def dibujar(self, ventana):
        # 1) Etiqueta encima de la caja
        etiqueta = FUENTE_ETIQUETA.render(self.etiqueta, True, AZUL_CLARO)
        ventana.blit(etiqueta, (self.rect.x, self.rect.y - 24))

        # 2) Fondo negro y borde. Rojo si hay error; más grueso si está activo
        pygame.draw.rect(ventana, NEGRO, self.rect, border_radius=6)
        color_borde = ROJO if self.error else AZUL_CLARO
        grosor = 3 if self.activo else 1
        pygame.draw.rect(ventana, color_borde, self.rect, grosor, border_radius=6)

        # 3) Texto escrito (asteriscos si es contraseña)
        contenido = "*" * len(self.texto) if self.es_contrasena else self.texto
        superficie = FUENTE_TEXTO.render(contenido, True, AZUL_CLARO)
        # Si el texto es más ancho que la caja, mostramos solo el final
        espacio_util = self.rect.width - 24
        while superficie.get_width() > espacio_util and len(contenido) > 0:
            contenido = contenido[1:]
            superficie = FUENTE_TEXTO.render(contenido, True, AZUL_CLARO)
        pos_texto = (self.rect.x + 12, self.rect.centery - superficie.get_height() // 2)
        ventana.blit(superficie, pos_texto)

        # 4) Cursor parpadeante (cambia cada 500 milisegundos)
        if self.activo and (pygame.time.get_ticks() // 500) % 2 == 0:
            x_cursor = pos_texto[0] + superficie.get_width() + 2
            pygame.draw.line(ventana, AZUL_CLARO,
                             (x_cursor, self.rect.y + 10),
                             (x_cursor, self.rect.bottom - 10), 2)

        # 5) Mensaje de error en rojo, debajo de la caja
        if self.error:
            texto_error = FUENTE_ERROR.render(self.error, True, ROJO)
            ventana.blit(texto_error, (self.rect.x, self.rect.bottom + 6))


class Boton:
    """Un botón rectangular con texto que cambia de color al pasar el mouse."""

    def __init__(self, x, y, ancho, alto, texto):
        self.rect = pygame.Rect(x, y, ancho, alto)
        self.texto = texto

    def dibujar(self, ventana):
        # ¿El mouse está encima? Entonces rellenamos con azul oscuro
        encima = self.rect.collidepoint(pygame.mouse.get_pos())
        fondo = AZUL_OSCURO if encima else NEGRO
        pygame.draw.rect(ventana, fondo, self.rect, border_radius=8)
        pygame.draw.rect(ventana, AZUL_CLARO, self.rect, 2, border_radius=8)

        # Texto centrado dentro del botón
        superficie = FUENTE_TEXTO.render(self.texto, True, AZUL_CLARO)
        ventana.blit(superficie, superficie.get_rect(center=self.rect.center))

    def fue_presionado(self, evento):
        """True si el evento es un clic izquierdo dentro del botón."""
        return (evento.type == pygame.MOUSEBUTTONDOWN
                and evento.button == 1
                and self.rect.collidepoint(evento.pos))


class EnlaceTexto:
    """
    Un texto subrayado en el que se puede hacer clic (como un link web).
    Se usa para "¿Olvidaste tu contraseña?".
    """

    def __init__(self, centro_x, y, texto):
        self.texto = texto
        superficie = FUENTE_ETIQUETA.render(texto, True, AZUL_CLARO)
        # El rectángulo se calcula a partir del tamaño del texto, centrado en 'centro_x'
        self.rect = superficie.get_rect(midtop=(centro_x, y))

    def dibujar(self, ventana):
        encima = self.rect.collidepoint(pygame.mouse.get_pos())
        color = AZUL_HOVER if encima else AZUL_CLARO
        superficie = FUENTE_ETIQUETA.render(self.texto, True, color)
        ventana.blit(superficie, self.rect)
        # Línea de subrayado
        pygame.draw.line(ventana, color,
                         (self.rect.left, self.rect.bottom - 1),
                         (self.rect.right, self.rect.bottom - 1), 1)

    def fue_presionado(self, evento):
        return (evento.type == pygame.MOUSEBUTTONDOWN
                and evento.button == 1
                and self.rect.collidepoint(evento.pos))


def dibujar_avatar(centro, radio, avatar="default"):
    """
    Dibuja el avatar del jugador: un círculo con una silueta (cabeza y hombros).
    'avatar' indica cuál mostrar. Por ahora solo existe "default"; cuando
    agregues la User Story de avatares, aquí se dibujaría o cargaría el elegido
    (por ejemplo con pygame.image.load(ruta)).
    """
    cx, cy = centro

    # Círculo exterior
    pygame.draw.circle(VENTANA, NEGRO, centro, radio)
    pygame.draw.circle(VENTANA, AZUL_CLARO, centro, radio, 2)

    # Cabeza: un círculo pequeño un poco por encima del centro
    radio_cabeza = int(radio * 0.28)
    pygame.draw.circle(VENTANA, AZUL_CLARO, (cx, int(cy - radio * 0.22)), radio_cabeza, 2)

    # Hombros: la mitad superior de una elipse, dibujada como una línea quebrada
    # formada por muchos puntos pequeños (usamos seno y coseno para calcularlos)
    puntos = []
    for i in range(31):
        angulo = math.pi * i / 30                         # De 0 a 180 grados (en radianes)
        x = cx + math.cos(angulo) * radio * 0.55
        y = cy + radio * 0.62 - math.sin(angulo) * radio * 0.50
        puntos.append((x, y))
    pygame.draw.lines(VENTANA, AZUL_CLARO, False, puntos, 2)


def dibujar_barra_sesion():
    """
    Dibuja en la esquina superior derecha el avatar y el nombre del jugador
    que tiene la sesión iniciada. Se llama desde TODAS las pantallas, así que
    cuando haya más pantallas con sesión, el jugador siempre se verá identificado.
    """
    if not SESION.activa:
        return
    dibujar_avatar((ANCHO - 70, 55), 28, SESION.avatar)
    nombre = FUENTE_TEXTO.render(SESION.usuario, True, AZUL_CLARO)
    VENTANA.blit(nombre, nombre.get_rect(midright=(ANCHO - 112, 55)))


# =====================================================================
# 9. LÓGICA DE CADA PANTALLA
# =====================================================================

# ---------------------------------------------------------------------
# 9.1 REGISTRO (US-01)
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
        "avatar": "default",
        "correo_verificado": False,
        "codigo_verificacion": codigo,
        "codigo_expira": time.time() + MINUTOS_VALIDEZ_CODIGO * 60,
    }
    if cuenta_pendiente is not None:
        # Era un reintento: quitamos el registro viejo para reemplazarlo
        usuarios = [u for u in usuarios if u is not cuenta_pendiente]
    usuarios.append(cuenta)
    guardar_usuarios(usuarios)
    return usuario, ""


# ---------------------------------------------------------------------
# 9.2 VERIFICACIÓN DEL CORREO (US-02)
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
# 9.3 INICIO DE SESIÓN (US-03)
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

    # --- Paso 3: correo verificado (CA-03.4) ---
    if not cuenta.get("correo_verificado", False):
        return "no_verificado", "", cuenta

    return "ok", "", cuenta


# ---------------------------------------------------------------------
# 9.4 RECUPERACIÓN DE CONTRASEÑA (US-05)
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

    # CA-05.4: ¿expiró? Si sí, lo borramos para que no se pueda usar nunca más
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


# =====================================================================
# 10. ELEMENTOS Y DIBUJO DE CADA PANTALLA
# =====================================================================

class Estado:
    """
    Guarda en qué pantalla estamos y los datos que las pantallas comparten.
    Es un simple "contenedor" de variables: así podemos pasárselo a las
    funciones en lugar de usar muchas variables sueltas.
    """

    def __init__(self):
        self.pantalla = "registro"       # Pantalla actual
        self.pantalla_anterior = "registro"   # A dónde vuelve el botón "Volver" de verificación
        self.usuario_pendiente = ""      # Usuario que está verificando su correo
        self.correo_pendiente = ""       # Su correo (para mostrarlo en pantalla)
        self.correo_recuperacion = ""    # Correo para el que se pidió recuperar contraseña
        self.mensaje = ""                # Mensaje general de la pantalla actual
        self.color_mensaje = ROJO        # Color de ese mensaje
        self.aviso_verificacion = ""     # Aviso rojo extra en la pantalla de verificación
        self.verificado = False          # ¿Ya se verificó correctamente el correo?

    def poner_mensaje(self, texto, color=ROJO):
        """Cambia el mensaje general que se muestra en la pantalla."""
        self.mensaje = texto
        self.color_mensaje = color


# --- Funciones de dibujo generales ---------------------------------------

def calcular_panel(alto_panel, ancho_panel=640):
    """Devuelve un rectángulo centrado en la ventana."""
    x = (ANCHO - ancho_panel) // 2
    y = (ALTO - alto_panel) // 2
    return pygame.Rect(x, y, ancho_panel, alto_panel)


def dibujar_panel(panel):
    """Dibuja el recuadro central: fondo negro y borde azul claro."""
    pygame.draw.rect(VENTANA, NEGRO, panel, border_radius=14)
    pygame.draw.rect(VENTANA, AZUL_CLARO, panel, 2, border_radius=14)


def dibujar_texto_centrado(texto, fuente, color, centro_x, y):
    """Dibuja un texto centrado horizontalmente en 'centro_x', con su parte superior en 'y'."""
    superficie = fuente.render(texto, True, color)
    VENTANA.blit(superficie, superficie.get_rect(midtop=(centro_x, y)))


def dibujar_mensaje(estado, centro_x, y):
    """Dibuja el mensaje general de la pantalla (errores del servidor, éxito, 'Procesando...')."""
    if estado.mensaje:
        dibujar_texto_centrado(estado.mensaje, FUENTE_ERROR, estado.color_mensaje, centro_x, y)


# --- Medidas comunes a todas las pantallas ---
MARGEN = 60                                       # Espacio entre el borde del panel y los campos
ANCHO_CAMPOS = 640 - 2 * MARGEN                   # Ancho de campos y botones (520)
ALTO_CAMPO = 46
SEPARACION = 108                                  # Distancia vertical entre campos (deja sitio al error)


# ---------------------------------------------------------------------
# 10.1 Pantalla de REGISTRO
# ---------------------------------------------------------------------
PANEL_REGISTRO = calcular_panel(780)
X_CAMPOS = PANEL_REGISTRO.x + MARGEN
Y_PRIMER_CAMPO = PANEL_REGISTRO.y + 140

campo_usuario = CampoTexto(X_CAMPOS, Y_PRIMER_CAMPO + SEPARACION * 0, ANCHO_CAMPOS, ALTO_CAMPO,
                           "Nombre de usuario", max_caracteres=20)
campo_correo = CampoTexto(X_CAMPOS, Y_PRIMER_CAMPO + SEPARACION * 1, ANCHO_CAMPOS, ALTO_CAMPO,
                          "Correo electrónico", max_caracteres=60)
campo_clave = CampoTexto(X_CAMPOS, Y_PRIMER_CAMPO + SEPARACION * 2, ANCHO_CAMPOS, ALTO_CAMPO,
                         "Contraseña", es_contrasena=True, max_caracteres=40)
campo_confirmar = CampoTexto(X_CAMPOS, Y_PRIMER_CAMPO + SEPARACION * 3, ANCHO_CAMPOS, ALTO_CAMPO,
                             "Confirmar contraseña", es_contrasena=True, max_caracteres=40)
CAMPOS_REGISTRO = [campo_usuario, campo_correo, campo_clave, campo_confirmar]

boton_crear = Boton(X_CAMPOS, PANEL_REGISTRO.y + 560, ANCHO_CAMPOS, 52, "Crear cuenta")
boton_ir_login = Boton(X_CAMPOS, PANEL_REGISTRO.y + 690, ANCHO_CAMPOS, 52, "Iniciar sesión")


def dibujar_registro(estado):
    """Dibuja todos los elementos de la pantalla de registro."""
    dibujar_panel(PANEL_REGISTRO)
    centro_x = PANEL_REGISTRO.centerx

    dibujar_texto_centrado("¿Eres nuevo? Crea tu cuenta", FUENTE_TITULO, AZUL_CLARO,
                           centro_x, PANEL_REGISTRO.y + 40)

    for campo in CAMPOS_REGISTRO:
        campo.dibujar(VENTANA)

    boton_crear.dibujar(VENTANA)
    dibujar_mensaje(estado, centro_x, PANEL_REGISTRO.y + 622)

    dibujar_texto_centrado("¿Ya tienes una cuenta? Inicia sesión", FUENTE_TEXTO, AZUL_CLARO,
                           centro_x, PANEL_REGISTRO.y + 654)
    boton_ir_login.dibujar(VENTANA)


# ---------------------------------------------------------------------
# 10.2 Pantalla de VERIFICACIÓN DE CORREO
# ---------------------------------------------------------------------
PANEL_VERIFICACION = calcular_panel(560)
X_V = PANEL_VERIFICACION.x + MARGEN

campo_codigo = CampoTexto(X_V, PANEL_VERIFICACION.y + 250, ANCHO_CAMPOS, ALTO_CAMPO,
                          "Código de verificación", max_caracteres=6)
boton_confirmar = Boton(X_V, PANEL_VERIFICACION.y + 360, ANCHO_CAMPOS, 52, "Confirmar")
boton_volver = Boton(X_V, PANEL_VERIFICACION.y + 470, ANCHO_CAMPOS, 52, "Volver")


def dibujar_verificacion(estado):
    """Dibuja todos los elementos de la pantalla de verificación de correo."""
    dibujar_panel(PANEL_VERIFICACION)
    centro_x = PANEL_VERIFICACION.centerx

    dibujar_texto_centrado("Verifica tu correo electrónico", FUENTE_TITULO, AZUL_CLARO,
                           centro_x, PANEL_VERIFICACION.y + 40)
    dibujar_texto_centrado("Escribe aquí el código que te enviamos.", FUENTE_TEXTO, AZUL_CLARO,
                           centro_x, PANEL_VERIFICACION.y + 110)
    dibujar_texto_centrado(f"Enviado a: {estado.correo_pendiente}", FUENTE_ERROR, AZUL_CLARO,
                           centro_x, PANEL_VERIFICACION.y + 150)

    # Aviso rojo: aparece cuando llegamos aquí desde el login con correo sin verificar
    if estado.aviso_verificacion:
        dibujar_texto_centrado(estado.aviso_verificacion, FUENTE_ERROR, ROJO,
                               centro_x, PANEL_VERIFICACION.y + 180)

    campo_codigo.dibujar(VENTANA)
    boton_confirmar.dibujar(VENTANA)
    dibujar_mensaje(estado, centro_x, PANEL_VERIFICACION.y + 425)
    boton_volver.dibujar(VENTANA)


# ---------------------------------------------------------------------
# 10.3 Pantalla de INICIO DE SESIÓN
# ---------------------------------------------------------------------
PANEL_LOGIN = calcular_panel(620)
X_L = PANEL_LOGIN.x + MARGEN

campo_login_ident = CampoTexto(X_L, PANEL_LOGIN.y + 140, ANCHO_CAMPOS, ALTO_CAMPO,
                               "Usuario o correo electrónico", max_caracteres=60)
campo_login_clave = CampoTexto(X_L, PANEL_LOGIN.y + 140 + SEPARACION, ANCHO_CAMPOS, ALTO_CAMPO,
                               "Contraseña", es_contrasena=True, max_caracteres=40)
CAMPOS_LOGIN = [campo_login_ident, campo_login_clave]

enlace_olvido = EnlaceTexto(PANEL_LOGIN.centerx, PANEL_LOGIN.y + 332, "¿Olvidaste tu contraseña?")
boton_login = Boton(X_L, PANEL_LOGIN.y + 375, ANCHO_CAMPOS, 52, "Iniciar sesión")
boton_ir_registro = Boton(X_L, PANEL_LOGIN.y + 512, ANCHO_CAMPOS, 52, "Crear cuenta")


def dibujar_login(estado):
    """Dibuja todos los elementos de la pantalla de inicio de sesión."""
    dibujar_panel(PANEL_LOGIN)
    centro_x = PANEL_LOGIN.centerx

    dibujar_texto_centrado("Iniciar sesión", FUENTE_TITULO, AZUL_CLARO,
                           centro_x, PANEL_LOGIN.y + 40)

    for campo in CAMPOS_LOGIN:
        campo.dibujar(VENTANA)

    enlace_olvido.dibujar(VENTANA)
    boton_login.dibujar(VENTANA)
    dibujar_mensaje(estado, centro_x, PANEL_LOGIN.y + 440)

    dibujar_texto_centrado("¿No tienes cuenta? Regístrate", FUENTE_TEXTO, AZUL_CLARO,
                           centro_x, PANEL_LOGIN.y + 476)
    boton_ir_registro.dibujar(VENTANA)


# ---------------------------------------------------------------------
# 10.4 Pantalla de RECUPERACIÓN - paso 1: pedir el código
# ---------------------------------------------------------------------
PANEL_REC1 = calcular_panel(510)
X_R1 = PANEL_REC1.x + MARGEN

campo_rec_correo = CampoTexto(X_R1, PANEL_REC1.y + 190, ANCHO_CAMPOS, ALTO_CAMPO,
                              "Correo electrónico", max_caracteres=60)
boton_enviar_codigo = Boton(X_R1, PANEL_REC1.y + 300, ANCHO_CAMPOS, 52, "Enviar código")
boton_rec1_volver = Boton(X_R1, PANEL_REC1.y + 410, ANCHO_CAMPOS, 52, "Volver")


def dibujar_rec_solicitud(estado):
    """Dibuja la pantalla donde se pide el código de recuperación."""
    dibujar_panel(PANEL_REC1)
    centro_x = PANEL_REC1.centerx

    dibujar_texto_centrado("Recupera tu contraseña", FUENTE_TITULO, AZUL_CLARO,
                           centro_x, PANEL_REC1.y + 40)
    dibujar_texto_centrado("Escribe el correo electrónico de tu cuenta.", FUENTE_TEXTO, AZUL_CLARO,
                           centro_x, PANEL_REC1.y + 105)
    dibujar_texto_centrado("Te enviaremos un código para crear una nueva contraseña.",
                           FUENTE_ERROR, AZUL_CLARO, centro_x, PANEL_REC1.y + 138)

    campo_rec_correo.dibujar(VENTANA)
    boton_enviar_codigo.dibujar(VENTANA)
    dibujar_mensaje(estado, centro_x, PANEL_REC1.y + 365)
    boton_rec1_volver.dibujar(VENTANA)


# ---------------------------------------------------------------------
# 10.5 Pantalla de RECUPERACIÓN - paso 2: código y nueva contraseña
# ---------------------------------------------------------------------
PANEL_REC2 = calcular_panel(720)
X_R2 = PANEL_REC2.x + MARGEN

campo_rec_codigo = CampoTexto(X_R2, PANEL_REC2.y + 200, ANCHO_CAMPOS, ALTO_CAMPO,
                              "Código de recuperación", max_caracteres=6)
campo_rec_nueva = CampoTexto(X_R2, PANEL_REC2.y + 200 + SEPARACION, ANCHO_CAMPOS, ALTO_CAMPO,
                             "Nueva contraseña", es_contrasena=True, max_caracteres=40)
campo_rec_confirmar = CampoTexto(X_R2, PANEL_REC2.y + 200 + SEPARACION * 2, ANCHO_CAMPOS, ALTO_CAMPO,
                                 "Confirmar nueva contraseña", es_contrasena=True, max_caracteres=40)
CAMPOS_REC_NUEVA = [campo_rec_codigo, campo_rec_nueva, campo_rec_confirmar]

boton_cambiar = Boton(X_R2, PANEL_REC2.y + 510, ANCHO_CAMPOS, 52, "Cambiar contraseña")
boton_rec2_volver = Boton(X_R2, PANEL_REC2.y + 615, ANCHO_CAMPOS, 52, "Volver")


def dibujar_rec_nueva(estado):
    """Dibuja la pantalla donde se escribe el código y la nueva contraseña."""
    dibujar_panel(PANEL_REC2)
    centro_x = PANEL_REC2.centerx

    dibujar_texto_centrado("Crea tu nueva contraseña", FUENTE_TITULO, AZUL_CLARO,
                           centro_x, PANEL_REC2.y + 40)
    dibujar_texto_centrado("Si el correo está registrado, te enviamos un código.",
                           FUENTE_ERROR, AZUL_CLARO, centro_x, PANEL_REC2.y + 100)
    dibujar_texto_centrado(f"Es válido por {MINUTOS_VALIDEZ_RECUPERACION} minutos.",
                           FUENTE_ERROR, AZUL_CLARO, centro_x, PANEL_REC2.y + 122)

    for campo in CAMPOS_REC_NUEVA:
        campo.dibujar(VENTANA)

    boton_cambiar.dibujar(VENTANA)
    dibujar_mensaje(estado, centro_x, PANEL_REC2.y + 575)
    boton_rec2_volver.dibujar(VENTANA)


# ---------------------------------------------------------------------
# 10.6 ÁREA DE JUEGO (solo accesible con sesión iniciada)
# ---------------------------------------------------------------------
PANEL_JUEGO = calcular_panel(560)
X_J = PANEL_JUEGO.x + MARGEN

boton_cerrar_sesion = Boton(X_J, PANEL_JUEGO.y + 450, ANCHO_CAMPOS, 52, "Cerrar sesión")


def dibujar_juego(estado):
    """
    Dibuja el área de juego. Por ahora es solo una pantalla de bienvenida que
    demuestra que el sistema identificó al jugador y muestra su avatar (CA-03.5).
    Aquí es donde más adelante irá el lobby / las partidas.
    """
    dibujar_panel(PANEL_JUEGO)
    centro_x = PANEL_JUEGO.centerx

    dibujar_texto_centrado("Área de juego", FUENTE_TITULO, AZUL_CLARO,
                           centro_x, PANEL_JUEGO.y + 40)

    # Avatar grande del jugador identificado
    dibujar_avatar((centro_x, PANEL_JUEGO.y + 180), 70, SESION.avatar)

    dibujar_texto_centrado(f"¡Bienvenido, {SESION.usuario}!", FUENTE_TITULO, AZUL_CLARO,
                           centro_x, PANEL_JUEGO.y + 275)
    dibujar_texto_centrado(SESION.correo, FUENTE_ERROR, AZUL_CLARO,
                           centro_x, PANEL_JUEGO.y + 325)
    dibujar_texto_centrado("Correo verificado", FUENTE_ERROR, VERDE,
                           centro_x, PANEL_JUEGO.y + 350)
    dibujar_texto_centrado("Aquí aparecerán las partidas (próximamente).", FUENTE_ERROR, AZUL_CLARO,
                           centro_x, PANEL_JUEGO.y + 395)

    boton_cerrar_sesion.dibujar(VENTANA)


# ---------------------------------------------------------------------
# 10.7 Dibujo general: elige qué pantalla dibujar
# ---------------------------------------------------------------------
# Diccionario: nombre de pantalla -> función que la dibuja
DIBUJOS = {
    "registro": dibujar_registro,
    "verificacion": dibujar_verificacion,
    "login": dibujar_login,
    "rec_solicitud": dibujar_rec_solicitud,
    "rec_nueva": dibujar_rec_nueva,
    "juego": dibujar_juego,
}


def dibujar_pantalla(estado):
    """Borra la ventana, dibuja la pantalla actual y la barra de sesión."""
    VENTANA.fill(NEGRO)                    # Borramos el cuadro anterior
    DIBUJOS[estado.pantalla](estado)       # Llamamos a la función de la pantalla actual
    dibujar_barra_sesion()                 # Avatar y nombre arriba a la derecha (si hay sesión)


def mostrar_procesando(estado):
    """
    Muestra "Procesando..." de inmediato. Se usa ANTES de tareas lentas (API,
    enviar correos) porque mientras se ejecutan la ventana queda congelada.
    """
    estado.poner_mensaje("Procesando, por favor espera...", AZUL_CLARO)
    dibujar_pantalla(estado)
    pygame.display.flip()


# =====================================================================
# 11. MANEJO DE EVENTOS DE CADA PANTALLA
# =====================================================================
# Cada pantalla tiene su función de eventos. Recibe un 'evento' de pygame
# (un clic, una tecla...) y el 'estado' del programa.

# Qué campos tiene cada pantalla (sirve para dar el foco al primero al entrar)
CAMPOS_POR_PANTALLA = {
    "registro": CAMPOS_REGISTRO,
    "verificacion": [campo_codigo],
    "login": CAMPOS_LOGIN,
    "rec_solicitud": [campo_rec_correo],
    "rec_nueva": CAMPOS_REC_NUEVA,
}
TODOS_LOS_CAMPOS = [c for lista in CAMPOS_POR_PANTALLA.values() for c in lista]


def ir_a(estado, pantalla):
    """
    Cambia de pantalla. Borra mensajes anteriores y deja el cursor
    listo en el primer campo de la pantalla nueva.
    """
    estado.pantalla = pantalla
    estado.poner_mensaje("")
    estado.aviso_verificacion = ""
    for campo in TODOS_LOS_CAMPOS:
        campo.activo = False
    if pantalla in CAMPOS_POR_PANTALLA:
        CAMPOS_POR_PANTALLA[pantalla][0].activo = True


def cambiar_foco(campos):
    """Pasa el cursor al siguiente campo de la lista (tecla TAB)."""
    indice_actual = -1
    for i, campo in enumerate(campos):
        if campo.activo:
            indice_actual = i
        campo.activo = False
    campos[(indice_actual + 1) % len(campos)].activo = True


def manejar_teclado_campos(evento, campos):
    """
    Pasa el evento a cada campo de la pantalla, gestiona la tecla TAB
    (cambiar de campo) y devuelve True si se presionó ENTER.
    """
    for campo in campos:
        campo.manejar_evento(evento)

    if evento.type == pygame.KEYDOWN:
        if evento.key == pygame.K_TAB:
            cambiar_foco(campos)
        elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return True
    return False


# ---------------------------------------------------------------------
# 11.1 Eventos de REGISTRO
# ---------------------------------------------------------------------
def eventos_registro(evento, estado):
    presiono_enter = manejar_teclado_campos(evento, CAMPOS_REGISTRO)

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
            campo_codigo.limpiar()
            ir_a(estado, "verificacion")
        else:
            estado.poner_mensaje(mensaje, ROJO)

    # Botón "Iniciar sesión": nos lleva a la pantalla de login
    if boton_ir_login.fue_presionado(evento):
        ir_a(estado, "login")


# ---------------------------------------------------------------------
# 11.2 Eventos de VERIFICACIÓN
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

        if estado.verificado and destino == "registro":
            # Terminó el registro: dejamos el formulario limpio
            for campo in CAMPOS_REGISTRO:
                campo.limpiar()

        ir_a(estado, destino)

        if estado.verificado and destino == "login":
            estado.poner_mensaje("¡Correo verificado! Ya puedes iniciar sesión.", VERDE)


# ---------------------------------------------------------------------
# 11.3 Eventos de LOGIN
# ---------------------------------------------------------------------
def eventos_login(evento, estado):
    presiono_enter = manejar_teclado_campos(evento, CAMPOS_LOGIN)

    # Botón "Iniciar sesión" (o ENTER)
    if boton_login.fue_presionado(evento) or presiono_enter:
        mostrar_procesando(estado)
        resultado, mensaje, cuenta = procesar_login(campo_login_ident, campo_login_clave)

        if resultado == "ok":
            # CA-03.2: credenciales correctas -> iniciamos la sesión y entramos al juego
            SESION.iniciar(cuenta)
            campo_login_ident.limpiar()
            campo_login_clave.limpiar()
            ir_a(estado, "juego")

        elif resultado == "no_verificado":
            # CA-03.4: correo sin verificar -> NO entra. Le avisamos y le enviamos
            # un código nuevo para que pueda verificarlo desde aquí mismo.
            se_envio, _ = reenviar_codigo_verificacion(cuenta)
            if se_envio:
                estado.usuario_pendiente = cuenta["usuario"]
                estado.correo_pendiente = cuenta["correo"]
                estado.pantalla_anterior = "login"
                estado.verificado = False
                campo_login_clave.limpiar()          # No dejamos la contraseña escrita
                campo_codigo.limpiar()
                ir_a(estado, "verificacion")
                estado.aviso_verificacion = ("Tu correo aún no está verificado. "
                                             "Te enviamos un nuevo código.")
            else:
                estado.poner_mensaje("Correo no verificado. No se pudo enviar el nuevo código.", ROJO)

        else:
            # CA-03.3: credenciales incorrectas (o campos vacíos)
            estado.poner_mensaje(mensaje, ROJO)

    # Enlace "¿Olvidaste tu contraseña?"
    if enlace_olvido.fue_presionado(evento):
        campo_rec_correo.limpiar()
        ir_a(estado, "rec_solicitud")

    # Botón "Crear cuenta": vuelve al registro
    if boton_ir_registro.fue_presionado(evento):
        ir_a(estado, "registro")


# ---------------------------------------------------------------------
# 11.4 Eventos de RECUPERACIÓN (paso 1)
# ---------------------------------------------------------------------
def eventos_rec_solicitud(evento, estado):
    presiono_enter = manejar_teclado_campos(evento, [campo_rec_correo])

    # Botón "Enviar código" (o ENTER)
    if boton_enviar_codigo.fue_presionado(evento) or presiono_enter:
        mostrar_procesando(estado)
        todo_bien, mensaje = solicitar_recuperacion(campo_rec_correo)

        if todo_bien:
            # Pasamos al paso 2 con los campos vacíos
            estado.correo_recuperacion = campo_rec_correo.texto.strip()
            for campo in CAMPOS_REC_NUEVA:
                campo.limpiar()
            ir_a(estado, "rec_nueva")
        else:
            estado.poner_mensaje(mensaje, ROJO)

    # Botón "Volver": regresa al login
    if boton_rec1_volver.fue_presionado(evento):
        ir_a(estado, "login")


# ---------------------------------------------------------------------
# 11.5 Eventos de RECUPERACIÓN (paso 2)
# ---------------------------------------------------------------------
def eventos_rec_nueva(evento, estado):
    presiono_enter = manejar_teclado_campos(evento, CAMPOS_REC_NUEVA)

    # Botón "Cambiar contraseña" (o ENTER)
    if boton_cambiar.fue_presionado(evento) or presiono_enter:
        if restablecer_contrasena(campo_rec_codigo, campo_rec_nueva,
                                  campo_rec_confirmar, estado.correo_recuperacion):
            # CA-05.3: contraseña cambiada -> volvemos al login con un mensaje verde
            for campo in CAMPOS_REC_NUEVA:
                campo.limpiar()
            ir_a(estado, "login")
            estado.poner_mensaje("Contraseña actualizada. Ya puedes iniciar sesión.", VERDE)

    # Botón "Volver": regresa al paso 1
    if boton_rec2_volver.fue_presionado(evento):
        ir_a(estado, "rec_solicitud")


# ---------------------------------------------------------------------
# 11.6 Eventos del ÁREA DE JUEGO
# ---------------------------------------------------------------------
def eventos_juego(evento, estado):
    # Botón "Cerrar sesión": vaciamos la sesión y volvemos al login
    if boton_cerrar_sesion.fue_presionado(evento):
        SESION.cerrar()
        ir_a(estado, "login")


# Diccionario: nombre de pantalla -> función que maneja sus eventos
MANEJADORES_EVENTOS = {
    "registro": eventos_registro,
    "verificacion": eventos_verificacion,
    "login": eventos_login,
    "rec_solicitud": eventos_rec_solicitud,
    "rec_nueva": eventos_rec_nueva,
    "juego": eventos_juego,
}


# =====================================================================
# 12. BUCLE PRINCIPAL
# =====================================================================
# Todo juego de pygame repite 3 pasos muchas veces por segundo:
#     A) Leer eventos (teclado, mouse, cerrar ventana)
#     B) Actualizar la lógica
#     C) Dibujar la pantalla

def main():
    estado = Estado()
    ir_a(estado, "registro")       # Empezamos en el registro, con el primer campo listo

    ejecutando = True
    while ejecutando:

        # ---------- A) EVENTOS ----------
        for evento in pygame.event.get():

            # Cerrar la ventana
            if evento.type == pygame.QUIT:
                ejecutando = False
                continue

            # El evento se lo pasamos a la función de la pantalla actual
            MANEJADORES_EVENTOS[estado.pantalla](evento, estado)

        # ---------- B) LÓGICA ----------
        # Protección: sin sesión iniciada NO se puede entrar al área de juego
        # (CA-02.5 y CA-03.4). Si alguien llega ahí sin sesión, vuelve al login.
        if estado.pantalla == "juego" and not SESION.activa:
            ir_a(estado, "login")

        # ---------- C) DIBUJAR ----------
        dibujar_pantalla(estado)
        pygame.display.flip()                  # Mostramos lo que dibujamos
        RELOJ.tick(FPS)                        # Limita el juego a 60 cuadros por segundo

    pygame.quit()


# Esta condición hace que main() solo se ejecute al correr este archivo directamente
if __name__ == "__main__":
    main()