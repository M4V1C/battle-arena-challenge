# =====================================================================
#  CONTROL DEL REACTOR
#  Pantalla de registro de usuario (US-01) y verificación de correo (US-02)
# =====================================================================
#
#  Cómo está organizado este archivo (de arriba hacia abajo):
#     1. IMPORTACIONES
#     2. CONFIGURACIÓN (tamaños, colores, correo, archivo .json)
#     3. INICIALIZACIÓN DE PYGAME (ventana y fuentes)
#     4. BASE DE DATOS (leer/escribir usuarios.json)
#     5. VALIDACIONES (usuario, correo, contraseña, API de correo)
#     6. ENVÍO DEL CORREO CON EL CÓDIGO
#     7. COMPONENTES VISUALES (clase CampoTexto y clase Boton)
#     8. LÓGICA DE CADA PANTALLA (procesar registro / verificar código)
#     9. DIBUJO DE CADA PANTALLA
#    10. BUCLE PRINCIPAL (el "corazón" de todo juego en pygame)
#
# =====================================================================


# =====================================================================
# 1. IMPORTACIONES
# =====================================================================
import pygame                      # La librería del juego
import json                        # Para leer/escribir usuarios.json
import os                          # Para construir la ruta del archivo .json
import re                          # Expresiones regulares (validar formatos)
import time                        # Para saber cuándo expira un código
import hashlib                     # Para "encriptar" (hashear) las contraseñas
import secrets                     # Para generar códigos y sales aleatorias seguras
import smtplib                     # Para enviar correos (protocolo SMTP)
import ssl                         # Conexión segura con el servidor de correo
import urllib.request              # Para llamar a la API de validación de correo
import urllib.parse                # Para codificar el correo dentro de la URL
from email.message import EmailMessage   # Para armar el correo


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
SMTP_USUARIO = os.environ.get("REACTOR_SMTP_USER", "tu_correo@gmail.com")
SMTP_CLAVE = os.environ.get("REACTOR_SMTP_PASS", "tu_contrasena_de_aplicacion")

# --- Código de verificación ---
MINUTOS_VALIDEZ_CODIGO = 15        # Después de este tiempo el código expira


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
#     "correo_verificado": false,
#     "codigo_verificacion": "123456",
#     "codigo_expira": 1700000000.0
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
    Devuelve (sal, hash). Al iniciar sesión (US futura) se calcula el hash
    de lo que escriba el usuario con la MISMA sal y se compara.
    """
    if sal is None:
        sal = secrets.token_hex(16)            # Sal aleatoria única por usuario
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256", contrasena.encode("utf-8"), bytes.fromhex(sal), 200_000
    )
    return sal, hash_bytes.hex()


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
# 6. ENVÍO DEL CORREO CON EL CÓDIGO
# =====================================================================

def generar_codigo():
    """Genera un código aleatorio de 6 dígitos (como texto)."""
    return str(secrets.randbelow(900000) + 100000)


def enviar_correo_codigo(destino, usuario, codigo):
    """
    Envía el correo con el código de verificación.
    Devuelve (se_envio, mensaje_de_error).
    """
    # Comprobamos que el programador haya configurado el correo emisor
    if "tu_correo" in SMTP_USUARIO:
        return False, "Configura SMTP_USUARIO y SMTP_CLAVE al inicio del archivo."

    # Armamos el correo
    mensaje = EmailMessage()
    mensaje["Subject"] = "Tu código de verificación - Control del Reactor"
    mensaje["From"] = SMTP_USUARIO
    mensaje["To"] = destino
    mensaje.set_content(
        f"Hola {usuario},\n\n"
        f"Tu código de verificación es: {codigo}\n\n"
        f"Es válido por {MINUTOS_VALIDEZ_CODIGO} minutos.\n"
        "Si no creaste una cuenta en Control del Reactor, ignora este mensaje."
    )

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


# =====================================================================
# 7. COMPONENTES VISUALES
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


# =====================================================================
# 8. LÓGICA DE CADA PANTALLA
# =====================================================================

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
    if cuenta_pendiente is not None:
        # Era un reintento: quitamos el registro viejo para reemplazarlo
        usuarios = [u for u in usuarios if u is not cuenta_pendiente]
    usuarios.append(cuenta)
    guardar_usuarios(usuarios)
    return usuario, ""


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


# =====================================================================
# 9. DIBUJO DE CADA PANTALLA
# =====================================================================

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


# --- Medidas y elementos de la pantalla de REGISTRO ---------------------
PANEL_REGISTRO = calcular_panel(780)
MARGEN = 60                                       # Espacio entre el borde del panel y los campos
X_CAMPOS = PANEL_REGISTRO.x + MARGEN
ANCHO_CAMPOS = PANEL_REGISTRO.width - 2 * MARGEN
ALTO_CAMPO = 46
SEPARACION = 108                                  # Distancia vertical entre campos (deja sitio al error)
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


def dibujar_registro(mensaje_general, color_mensaje):
    """Dibuja todos los elementos de la pantalla de registro."""
    dibujar_panel(PANEL_REGISTRO)
    centro_x = PANEL_REGISTRO.centerx

    dibujar_texto_centrado("¿Eres nuevo? Crea tu cuenta", FUENTE_TITULO, AZUL_CLARO,
                           centro_x, PANEL_REGISTRO.y + 40)

    for campo in CAMPOS_REGISTRO:
        campo.dibujar(VENTANA)

    boton_crear.dibujar(VENTANA)

    # Mensaje general (errores del servidor de correo, "Procesando...", etc.)
    if mensaje_general:
        dibujar_texto_centrado(mensaje_general, FUENTE_ERROR, color_mensaje,
                               centro_x, PANEL_REGISTRO.y + 622)

    dibujar_texto_centrado("¿Ya tienes una cuenta? Inicia sesión", FUENTE_TEXTO, AZUL_CLARO,
                           centro_x, PANEL_REGISTRO.y + 654)
    boton_ir_login.dibujar(VENTANA)


# --- Medidas y elementos de la pantalla de VERIFICACIÓN -----------------
PANEL_VERIFICACION = calcular_panel(560)
X_V = PANEL_VERIFICACION.x + MARGEN

campo_codigo = CampoTexto(X_V, PANEL_VERIFICACION.y + 250, ANCHO_CAMPOS, ALTO_CAMPO,
                          "Código de verificación", max_caracteres=6)
boton_confirmar = Boton(X_V, PANEL_VERIFICACION.y + 360, ANCHO_CAMPOS, 52, "Confirmar")
boton_volver = Boton(X_V, PANEL_VERIFICACION.y + 470, ANCHO_CAMPOS, 52, "Volver")


def dibujar_verificacion(correo_destino, mensaje_exito):
    """Dibuja todos los elementos de la pantalla de verificación de correo."""
    dibujar_panel(PANEL_VERIFICACION)
    centro_x = PANEL_VERIFICACION.centerx

    dibujar_texto_centrado("Verifica tu correo electrónico", FUENTE_TITULO, AZUL_CLARO,
                           centro_x, PANEL_VERIFICACION.y + 40)
    dibujar_texto_centrado("Escribe aquí el código que te enviamos.", FUENTE_TEXTO, AZUL_CLARO,
                           centro_x, PANEL_VERIFICACION.y + 110)
    dibujar_texto_centrado(f"Enviado a: {correo_destino}", FUENTE_ERROR, AZUL_CLARO,
                           centro_x, PANEL_VERIFICACION.y + 150)

    campo_codigo.dibujar(VENTANA)
    boton_confirmar.dibujar(VENTANA)

    if mensaje_exito:
        dibujar_texto_centrado(mensaje_exito, FUENTE_ERROR, VERDE,
                               centro_x, PANEL_VERIFICACION.y + 425)

    boton_volver.dibujar(VENTANA)


def cambiar_foco(campos):
    """Pasa el cursor al siguiente campo de la lista (tecla TAB)."""
    indice_actual = -1
    for i, campo in enumerate(campos):
        if campo.activo:
            indice_actual = i
        campo.activo = False
    campos[(indice_actual + 1) % len(campos)].activo = True


# =====================================================================
# 10. BUCLE PRINCIPAL
# =====================================================================
# Todo juego de pygame repite 3 pasos muchas veces por segundo:
#     A) Leer eventos (teclado, mouse, cerrar ventana)
#     B) Actualizar la lógica
#     C) Dibujar la pantalla

def main():
    pantalla = "registro"          # Pantalla actual: "registro" o "verificacion"
    usuario_pendiente = ""         # Usuario que está verificando su correo
    correo_pendiente = ""          # Su correo (para mostrarlo en pantalla)
    mensaje_general = ""           # Texto bajo el botón "Crear cuenta"
    color_mensaje = ROJO
    mensaje_exito = ""             # Texto verde de la pantalla de verificación
    verificado = False             # ¿Ya se verificó correctamente?

    campo_usuario.activo = True    # El primer campo empieza listo para escribir

    ejecutando = True
    while ejecutando:

        # ---------- A) EVENTOS ----------
        for evento in pygame.event.get():

            # Cerrar la ventana
            if evento.type == pygame.QUIT:
                ejecutando = False

            # ===== Eventos de la pantalla de REGISTRO =====
            if pantalla == "registro":
                for campo in CAMPOS_REGISTRO:
                    campo.manejar_evento(evento)

                # TAB cambia de campo; ENTER equivale a presionar "Crear cuenta"
                presiono_enter = False
                if evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_TAB:
                        cambiar_foco(CAMPOS_REGISTRO)
                    elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        presiono_enter = True

                if boton_crear.fue_presionado(evento) or presiono_enter:
                    # Mostramos "Procesando..." ANTES de la tarea lenta (API + correo)
                    # porque mientras se ejecuta la ventana queda congelada unos segundos.
                    VENTANA.fill(NEGRO)
                    dibujar_registro("Procesando, por favor espera...", AZUL_CLARO)
                    pygame.display.flip()

                    creado, mensaje_general = procesar_registro(
                        campo_usuario, campo_correo, campo_clave, campo_confirmar)
                    color_mensaje = ROJO

                    if creado:
                        # Todo salió bien: pasamos a la pantalla de verificación
                        usuario_pendiente = creado
                        correo_pendiente = campo_correo.texto.strip()
                        campo_codigo.limpiar()
                        campo_codigo.activo = True
                        mensaje_exito = ""
                        verificado = False
                        mensaje_general = ""
                        pantalla = "verificacion"

                if boton_ir_login.fue_presionado(evento):
                    pass  # Por ahora no hace nada (se programará más adelante)

            # ===== Eventos de la pantalla de VERIFICACIÓN =====
            elif pantalla == "verificacion":
                campo_codigo.manejar_evento(evento)

                presiono_enter = (evento.type == pygame.KEYDOWN
                                  and evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER))

                if boton_confirmar.fue_presionado(evento) or presiono_enter:
                    if procesar_verificacion(campo_codigo, usuario_pendiente):
                        verificado = True
                        mensaje_exito = "¡Correo verificado! Tu cuenta ya está activa."

                if boton_volver.fue_presionado(evento):
                    # Regresamos a la pantalla anterior
                    if verificado:
                        # Si ya terminó, dejamos el formulario limpio
                        for campo in CAMPOS_REGISTRO:
                            campo.limpiar()
                    pantalla = "registro"
                    mensaje_general = ""
                    for campo in CAMPOS_REGISTRO:
                        campo.activo = False
                    campo_usuario.activo = True

        # ---------- C) DIBUJAR ----------
        VENTANA.fill(NEGRO)                    # Borramos el cuadro anterior
        if pantalla == "registro":
            dibujar_registro(mensaje_general, color_mensaje)
        else:
            dibujar_verificacion(correo_pendiente, mensaje_exito)

        pygame.display.flip()                  # Mostramos lo que dibujamos
        RELOJ.tick(FPS)                        # Limita el juego a 60 cuadros por segundo

    pygame.quit()


# Esta condición hace que main() solo se ejecute al correr este archivo directamente
if __name__ == "__main__":
    main()