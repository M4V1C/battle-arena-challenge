# =====================================================================
#  componentes.py  -  PIEZAS VISUALES REUTILIZABLES
# =====================================================================
#  Todo lo que se dibuja en más de una pantalla está aquí:
#     - CampoTexto, Boton, EnlaceTexto  (clases)
#     - dibujar_avatar y la barra de sesión (arriba a la derecha)
#     - funciones para dibujar paneles y textos
#     - funciones para manejar el teclado en los campos (TAB / ENTER)
# =====================================================================

import math
import pygame

from config import (ANCHO, ALTO, ANCHO_PANEL, NEGRO, AZUL_CLARO, AZUL_OSCURO, AZUL_HOVER, ROJO)
from recursos import (VENTANA, FUENTE_TEXTO, FUENTE_ETIQUETA, FUENTE_ERROR)
from sesion import SESION


# =====================================================================
# CLASES: CampoTexto, Boton, EnlaceTexto
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

    def dibujar(self, ventana, seleccionado=False):
        """
        'seleccionado=True' lo dibuja "encendido" (relleno y borde grueso).
        Se usa en las pestañas del perfil para marcar la pestaña actual.
        """
        # ¿El mouse está encima? Entonces rellenamos con azul oscuro
        encima = self.rect.collidepoint(pygame.mouse.get_pos())
        fondo = AZUL_OSCURO if (encima or seleccionado) else NEGRO
        grosor = 3 if seleccionado else 2
        pygame.draw.rect(ventana, fondo, self.rect, border_radius=8)
        pygame.draw.rect(ventana, AZUL_CLARO, self.rect, grosor, border_radius=8)

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


# =====================================================================
# FUNCIONES DE DIBUJO GENERALES
# =====================================================================
def calcular_panel(alto_panel, ancho_panel=ANCHO_PANEL):
    """Devuelve un rectángulo centrado en la ventana (para el recuadro de cada pantalla)."""
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


def dibujar_texto(texto, fuente, color, x, y):
    """Dibuja un texto alineado a la IZQUIERDA (x, y = esquina superior izquierda)."""
    VENTANA.blit(fuente.render(texto, True, color), (x, y))


def dibujar_texto_derecha(texto, fuente, color, x_derecha, y):
    """Dibuja un texto alineado a la DERECHA (termina justo en x_derecha)."""
    superficie = fuente.render(texto, True, color)
    VENTANA.blit(superficie, superficie.get_rect(topright=(x_derecha, y)))


def recortar_texto(texto, fuente, ancho_maximo):
    """Si el texto no cabe en 'ancho_maximo' píxeles, lo acorta y le añade '...'."""
    if fuente.size(texto)[0] <= ancho_maximo:
        return texto
    while len(texto) > 1 and fuente.size(texto + "...")[0] > ancho_maximo:
        texto = texto[:-1]
    return texto + "..."


def dibujar_mensaje(estado, centro_x, y):
    """Dibuja el mensaje general de la pantalla (errores del servidor, éxito, 'Procesando...')."""
    if estado.mensaje:
        dibujar_texto_centrado(estado.mensaje, FUENTE_ERROR, estado.color_mensaje, centro_x, y)


# =====================================================================
# AVATAR Y BARRA DE SESIÓN
# =====================================================================
def dibujar_avatar(centro, radio, avatar="default"):
    """
    Dibuja el avatar del jugador: un círculo con una silueta (cabeza y hombros).
    'avatar' indica cuál mostrar. Por ahora solo existe "default"; cuando
    quieras permitir elegir avatares, aquí se dibujaría o cargaría el elegido
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


# Zona de la esquina superior derecha donde se dibuja el avatar y el nombre
RECT_BARRA_SESION = pygame.Rect(ANCHO - 280, 20, 260, 70)


def dibujar_barra_sesion():
    """
    Dibuja en la esquina superior derecha el avatar y el nombre del jugador
    que tiene la sesión iniciada. Se llama desde TODAS las pantallas, así que
    el jugador siempre se ve identificado. Al hacer clic aquí se abre su perfil.
    """
    if not SESION.activa:
        return
    encima = RECT_BARRA_SESION.collidepoint(pygame.mouse.get_pos())
    color = AZUL_HOVER if encima else AZUL_CLARO
    dibujar_avatar((ANCHO - 70, 55), 28, SESION.avatar)
    nombre = FUENTE_TEXTO.render(SESION.usuario, True, color)
    VENTANA.blit(nombre, nombre.get_rect(midright=(ANCHO - 112, 55)))


def barra_sesion_presionada(evento):
    """True si el jugador hizo clic en su avatar/nombre (esquina superior derecha)."""
    return (SESION.activa
            and evento.type == pygame.MOUSEBUTTONDOWN
            and evento.button == 1
            and RECT_BARRA_SESION.collidepoint(evento.pos))


# =====================================================================
# TECLADO EN LOS CAMPOS
# =====================================================================
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

    ENTER se detecta al SOLTAR la tecla (KEYUP) y no al presionarla (KEYDOWN):
    como activamos la repetición de teclas, mantener ENTER presionado generaría
    muchos KEYDOWN seguidos y se enviaría el formulario (¡y los correos!) varias veces.
    """
    for campo in campos:
        campo.manejar_evento(evento)

    if evento.type == pygame.KEYDOWN and evento.key == pygame.K_TAB:
        cambiar_foco(campos)
    elif evento.type == pygame.KEYUP and evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        return True
    return False