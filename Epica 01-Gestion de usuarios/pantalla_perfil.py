# =====================================================================
#  pantalla_perfil.py  -  PERFIL DEL JUGADOR (US-04)
# =====================================================================
#  La pantalla se divide en dos zonas:
#
#   IZQUIERDA (CA-05.1): datos básicos que siempre se ven
#       avatar, nombre de usuario, estado del correo, miembro desde, nivel...
#
#   DERECHA (CA-05.2): historial de partidas anteriores, en 4 pestañas
#       Estadísticas | Logros | Ranking | Historial
#
#  Los datos vienen de perfil_datos.obtener_perfil(), que lee usuarios.json;
#  por eso se conservan entre sesiones. Se cargan UNA vez al entrar a la
#  pantalla (en al_entrar_perfil) y no en cada cuadro, para no leer el
#  archivo 60 veces por segundo.
#
#  Se llega desde el botón "Mi perfil" del área de juego, o haciendo clic en
#  el avatar/nombre de arriba a la derecha.
# =====================================================================

import pygame

from config import (AZUL_CLARO, AZUL_HOVER, GRIS_AZUL, LINEA_TENUE, ROJO, VERDE)
from recursos import VENTANA, FUENTE_TITULO, FUENTE_TEXTO, FUENTE_ETIQUETA, FUENTE_ERROR
from componentes import (Boton, calcular_panel, dibujar_panel, dibujar_avatar,
                         dibujar_texto, dibujar_texto_centrado, dibujar_texto_derecha,
                         recortar_texto)
from estado import registrar_pantalla, ir_a
from sesion import SESION
from perfil_datos import obtener_perfil, formatear_duracion


# ---------------------------------------------------------------------
# 1) MEDIDAS Y ELEMENTOS
# ---------------------------------------------------------------------
PANEL = calcular_panel(740, 1240)               # Panel ancho, centrado en la ventana

# Columna izquierda (datos básicos)
X_COL_IZQ = PANEL.x + 200                       # Centro de la columna izquierda
ANCHO_COL_IZQ = 340                             # Ancho máximo para textos de esa columna
X_DIVISOR = PANEL.x + 400                       # Línea vertical que separa las dos zonas

# Zona derecha (pestañas)
X_DER = X_DIVISOR + 40
ANCHO_DER = PANEL.right - 40 - X_DER            # 760 píxeles
Y_CONTENIDO = PANEL.y + 120                     # Dónde empieza el contenido bajo las pestañas
FILAS_HISTORIAL = 9                             # Partidas visibles a la vez en el historial

# Pestañas: (identificador, texto del botón)
PESTANAS = [
    ("estadisticas", "Estadísticas"),
    ("logros", "Logros"),
    ("ranking", "Ranking"),
    ("historial", "Historial"),
]

# Un botón por pestaña, repartidos en una fila
ANCHO_PESTANA = (ANCHO_DER - 3 * 20) // 4
BOTONES_PESTANAS = {}
for i, (id_pestana, texto) in enumerate(PESTANAS):
    BOTONES_PESTANAS[id_pestana] = Boton(X_DER + i * (ANCHO_PESTANA + 20), PANEL.y + 30,
                                         ANCHO_PESTANA, 44, texto)

# Botones de la columna izquierda
boton_volver_juego = Boton(X_COL_IZQ - 140, PANEL.y + 590, 280, 52, "Volver al juego")
boton_cerrar_sesion = Boton(X_COL_IZQ - 140, PANEL.y + 650, 280, 52, "Cerrar sesión")


# ---------------------------------------------------------------------
# 2) DIBUJO - utilidades
# ---------------------------------------------------------------------
def linea_horizontal(y):
    """Línea separadora suave que cruza toda la zona derecha."""
    pygame.draw.line(VENTANA, LINEA_TENUE, (X_DER, y), (X_DER + ANCHO_DER, y), 1)


def texto_vacio(mensaje, y):
    """Mensaje centrado en la zona derecha cuando no hay datos que mostrar."""
    dibujar_texto_centrado(mensaje, FUENTE_TEXTO, GRIS_AZUL, X_DER + ANCHO_DER // 2, y)


# ---------------------------------------------------------------------
# 2) DIBUJO - columna izquierda (CA-05.1)
# ---------------------------------------------------------------------
def dibujar_columna_izquierda(perfil):
    """Avatar, nombre, estado del correo e información básica."""
    dibujar_texto_centrado("Mi perfil", FUENTE_TITULO, AZUL_CLARO, X_COL_IZQ, PANEL.y + 30)

    # Avatar
    dibujar_avatar((X_COL_IZQ, PANEL.y + 165), 80, perfil["avatar"])

    # Nombre de usuario (recortado con "..." si fuera muy largo)
    nombre = recortar_texto(perfil["usuario"], FUENTE_TITULO, ANCHO_COL_IZQ)
    dibujar_texto_centrado(nombre, FUENTE_TITULO, AZUL_CLARO, X_COL_IZQ, PANEL.y + 265)

    # Estado del correo: verde si está verificado, rojo si está pendiente
    if perfil["correo_verificado"]:
        dibujar_texto_centrado("Correo verificado", FUENTE_ETIQUETA, VERDE,
                               X_COL_IZQ, PANEL.y + 315)
    else:
        dibujar_texto_centrado("Correo pendiente de verificación", FUENTE_ETIQUETA, ROJO,
                               X_COL_IZQ, PANEL.y + 315)

    correo = recortar_texto(perfil["correo"], FUENTE_ERROR, ANCHO_COL_IZQ)
    dibujar_texto_centrado(correo, FUENTE_ERROR, AZUL_CLARO, X_COL_IZQ, PANEL.y + 345)

    # Línea separadora e información básica
    pygame.draw.line(VENTANA, LINEA_TENUE,
                     (X_COL_IZQ - 140, PANEL.y + 385), (X_COL_IZQ + 140, PANEL.y + 385), 1)
    dibujar_texto_centrado("Información básica", FUENTE_ETIQUETA, GRIS_AZUL,
                           X_COL_IZQ, PANEL.y + 400)
    dibujar_texto_centrado(f"Miembro desde: {perfil['fecha_registro']}", FUENTE_TEXTO,
                           AZUL_CLARO, X_COL_IZQ, PANEL.y + 430)
    dibujar_texto_centrado(f"Nivel: {perfil['nivel']}", FUENTE_TEXTO, AZUL_CLARO,
                           X_COL_IZQ, PANEL.y + 462)
    dibujar_texto_centrado(f"Partidas jugadas: {perfil['estadisticas']['partidas_jugadas']}",
                           FUENTE_TEXTO, AZUL_CLARO, X_COL_IZQ, PANEL.y + 494)


# ---------------------------------------------------------------------
# 2) DIBUJO - pestaña ESTADÍSTICAS
# ---------------------------------------------------------------------
def dibujar_pestana_estadisticas(perfil):
    est = perfil["estadisticas"]

    # Cada fila es (nombre de la estadística, valor ya convertido a texto)
    filas = [
        ("Partidas jugadas", str(est["partidas_jugadas"])),
        ("Victorias", str(est["victorias"])),
        ("Derrotas", str(est["derrotas"])),
        ("Porcentaje de victorias", f"{est['porcentaje_victorias']:.1f} %"),
        ("Puntaje total", str(est["puntaje_total"])),
        ("Mejor puntaje en una partida", str(est["mejor_puntaje"])),
        ("Puntaje promedio por partida", f"{est['puntaje_promedio']:.0f}"),
        ("Tiempo total jugado", formatear_duracion(est["tiempo_total_seg"])),
        ("Duración promedio de partida", formatear_duracion(est["duracion_promedio_seg"])),
    ]

    y = Y_CONTENIDO
    for etiqueta, valor in filas:
        dibujar_texto(etiqueta, FUENTE_TEXTO, AZUL_CLARO, X_DER, y + 12)
        dibujar_texto_derecha(valor, FUENTE_TEXTO, AZUL_HOVER, X_DER + ANCHO_DER, y + 12)
        linea_horizontal(y + 48)
        y += 52

    if est["partidas_jugadas"] == 0:
        texto_vacio("Aún no has jugado partidas. Tus estadísticas aparecerán aquí.", y + 20)


# ---------------------------------------------------------------------
# 2) DIBUJO - pestaña LOGROS
# ---------------------------------------------------------------------
def dibujar_pestana_logros(perfil):
    logros = perfil["logros"]
    desbloqueados = sum(1 for logro in logros if logro["desbloqueado"])
    dibujar_texto(f"Logros desbloqueados: {desbloqueados} de {len(logros)}",
                  FUENTE_TEXTO, AZUL_HOVER, X_DER, Y_CONTENIDO)

    y = Y_CONTENIDO + 45
    for logro in logros:
        # Un logro bloqueado se dibuja "apagado" (gris azulado)
        color = AZUL_CLARO if logro["desbloqueado"] else GRIS_AZUL
        dibujar_texto(logro["nombre"], FUENTE_TEXTO, color, X_DER, y + 8)
        dibujar_texto(logro["descripcion"], FUENTE_ERROR, color, X_DER, y + 38)

        if logro["desbloqueado"]:
            dibujar_texto_derecha("Desbloqueado", FUENTE_ETIQUETA, VERDE,
                                  X_DER + ANCHO_DER, y + 22)
        else:
            dibujar_texto_derecha("Bloqueado", FUENTE_ETIQUETA, GRIS_AZUL,
                                  X_DER + ANCHO_DER, y + 22)
        linea_horizontal(y + 68)
        y += 74


# ---------------------------------------------------------------------
# 2) DIBUJO - pestaña RANKING
# ---------------------------------------------------------------------
def dibujar_pestana_ranking(perfil):
    ranking = perfil["ranking"]

    # Posición del jugador
    if ranking["posicion"] is not None:
        dibujar_texto(f"Tu posición: #{ranking['posicion']} de {ranking['total']} jugadores",
                      FUENTE_TEXTO, AZUL_HOVER, X_DER, Y_CONTENIDO)
    else:
        dibujar_texto("Sin clasificar: juega una partida para entrar al ranking.",
                      FUENTE_TEXTO, GRIS_AZUL, X_DER, Y_CONTENIDO)

    # Cabecera de la tabla
    y = Y_CONTENIDO + 50
    dibujar_texto("Pos.", FUENTE_ETIQUETA, GRIS_AZUL, X_DER, y)
    dibujar_texto("Jugador", FUENTE_ETIQUETA, GRIS_AZUL, X_DER + 90, y)
    dibujar_texto_derecha("Puntaje total", FUENTE_ETIQUETA, GRIS_AZUL, X_DER + ANCHO_DER, y)
    linea_horizontal(y + 28)
    y += 36

    if not ranking["top"]:
        texto_vacio("Todavía nadie ha jugado partidas.", y + 30)
        return

    # Filas: los mejores jugadores. El propio jugador se resalta en verde.
    filas = [(f["posicion"], f["usuario"], f["puntaje"]) for f in ranking["top"]]

    # Si el jugador no está entre los mejores, añadimos "..." y su propia fila al final
    if ranking["posicion"] is not None and ranking["posicion"] > len(ranking["top"]):
        filas.append(None)                                   # None = fila con puntos suspensivos
        filas.append((ranking["posicion"], perfil["usuario"], ranking["mi_puntaje"]))

    for fila in filas:
        if fila is None:
            dibujar_texto("...", FUENTE_TEXTO, GRIS_AZUL, X_DER + 90, y + 8)
        else:
            posicion, usuario, puntaje = fila
            es_yo = usuario.lower() == perfil["usuario"].lower()
            color = VERDE if es_yo else AZUL_CLARO
            dibujar_texto(f"#{posicion}", FUENTE_TEXTO, color, X_DER, y + 8)
            dibujar_texto(recortar_texto(usuario, FUENTE_TEXTO, 400), FUENTE_TEXTO, color,
                          X_DER + 90, y + 8)
            dibujar_texto_derecha(str(puntaje), FUENTE_TEXTO, color, X_DER + ANCHO_DER, y + 8)
        linea_horizontal(y + 44)
        y += 48


# ---------------------------------------------------------------------
# 2) DIBUJO - pestaña HISTORIAL
# ---------------------------------------------------------------------
def dibujar_pestana_historial(perfil, scroll):
    historial = perfil["historial"]          # La partida más reciente va primero

    if not historial:
        texto_vacio("Aún no has jugado partidas. Tu historial aparecerá aquí.", Y_CONTENIDO + 40)
        return

    # Cabecera de la tabla. Las columnas se colocan con desplazamientos desde X_DER.
    y = Y_CONTENIDO
    dibujar_texto("Fecha", FUENTE_ETIQUETA, GRIS_AZUL, X_DER, y)
    dibujar_texto("Resultado", FUENTE_ETIQUETA, GRIS_AZUL, X_DER + 250, y)
    dibujar_texto_derecha("Puntaje", FUENTE_ETIQUETA, GRIS_AZUL, X_DER + 570, y)
    dibujar_texto_derecha("Duración", FUENTE_ETIQUETA, GRIS_AZUL, X_DER + ANCHO_DER, y)
    linea_horizontal(y + 28)
    y += 36

    # Solo dibujamos las FILAS_HISTORIAL partidas que corresponden al desplazamiento actual
    visibles = historial[scroll: scroll + FILAS_HISTORIAL]
    for partida in visibles:
        color_resultado = VERDE if partida["resultado"] == "victoria" else ROJO
        dibujar_texto(partida["fecha"], FUENTE_TEXTO, AZUL_CLARO, X_DER, y + 6)
        dibujar_texto(partida["resultado"].capitalize(), FUENTE_TEXTO, color_resultado,
                      X_DER + 250, y + 6)
        dibujar_texto_derecha(str(partida["puntaje"]), FUENTE_TEXTO, AZUL_CLARO,
                              X_DER + 570, y + 6)
        dibujar_texto_derecha(formatear_duracion(partida["duracion_seg"]), FUENTE_TEXTO,
                              AZUL_CLARO, X_DER + ANCHO_DER, y + 6)
        linea_horizontal(y + 40)
        y += 44

    # Pie: qué partidas se están viendo y cómo desplazarse
    primera = scroll + 1
    ultima = scroll + len(visibles)
    pie = f"Mostrando {primera}-{ultima} de {len(historial)}"
    if len(historial) > FILAS_HISTORIAL:
        pie += "   |   Rueda del mouse o flechas arriba/abajo para desplazarte"
    dibujar_texto(pie, FUENTE_ERROR, GRIS_AZUL, X_DER, Y_CONTENIDO + 36 + 44 * FILAS_HISTORIAL + 12)


# ---------------------------------------------------------------------
# 2) DIBUJO - pantalla completa
# ---------------------------------------------------------------------
def dibujar_perfil(estado):
    dibujar_panel(PANEL)
    perfil = estado.perfil

    # Si por algún motivo no se pudo cargar el perfil, mostramos un aviso
    if perfil is None:
        dibujar_texto_centrado("No se pudo cargar el perfil.", FUENTE_TEXTO, ROJO,
                               PANEL.centerx, PANEL.y + 300)
        boton_volver_juego.dibujar(VENTANA)
        return

    # Zona izquierda
    dibujar_columna_izquierda(perfil)
    boton_volver_juego.dibujar(VENTANA)
    boton_cerrar_sesion.dibujar(VENTANA)

    # Línea vertical que separa las dos zonas
    pygame.draw.line(VENTANA, AZUL_CLARO, (X_DIVISOR, PANEL.y + 30),
                     (X_DIVISOR, PANEL.bottom - 30), 1)

    # Zona derecha: pestañas (la actual se dibuja "seleccionada") y su contenido
    for id_pestana, boton in BOTONES_PESTANAS.items():
        boton.dibujar(VENTANA, seleccionado=(id_pestana == estado.pestana_perfil))

    if estado.pestana_perfil == "estadisticas":
        dibujar_pestana_estadisticas(perfil)
    elif estado.pestana_perfil == "logros":
        dibujar_pestana_logros(perfil)
    elif estado.pestana_perfil == "ranking":
        dibujar_pestana_ranking(perfil)
    elif estado.pestana_perfil == "historial":
        dibujar_pestana_historial(perfil, estado.scroll_historial)


# ---------------------------------------------------------------------
# 3) EVENTOS
# ---------------------------------------------------------------------
def desplazar_historial(estado, cantidad):
    """Mueve la lista del historial 'cantidad' filas (negativo = hacia arriba)."""
    if estado.perfil is None:
        return
    maximo = max(0, len(estado.perfil["historial"]) - FILAS_HISTORIAL)
    estado.scroll_historial = min(maximo, max(0, estado.scroll_historial + cantidad))


def eventos_perfil(evento, estado):
    # Clic en una pestaña
    for id_pestana, boton in BOTONES_PESTANAS.items():
        if boton.fue_presionado(evento):
            estado.pestana_perfil = id_pestana
            estado.scroll_historial = 0

    # Desplazamiento del historial: rueda del mouse (y > 0 = rueda hacia arriba)
    if estado.pestana_perfil == "historial":
        if evento.type == pygame.MOUSEWHEEL:
            desplazar_historial(estado, -evento.y)
        elif evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_UP:
                desplazar_historial(estado, -1)
            elif evento.key == pygame.K_DOWN:
                desplazar_historial(estado, 1)

    # Botones de la columna izquierda
    if boton_volver_juego.fue_presionado(evento):
        ir_a(estado, "juego")

    if estado.perfil is not None and boton_cerrar_sesion.fue_presionado(evento):
        SESION.cerrar()
        ir_a(estado, "login")


def al_entrar_perfil(estado):
    """
    Se ejecuta cada vez que se entra al perfil: lee los datos ACTUALES desde
    usuarios.json (así siempre se ve lo último) y vuelve a la primera pestaña.
    """
    estado.pestana_perfil = "estadisticas"
    estado.scroll_historial = 0
    estado.perfil = obtener_perfil(SESION.usuario) if SESION.activa else None


# ---------------------------------------------------------------------
# REGISTRO DE LA PANTALLA
# ---------------------------------------------------------------------
registrar_pantalla("perfil", dibujar_perfil, eventos_perfil, al_entrar=al_entrar_perfil)