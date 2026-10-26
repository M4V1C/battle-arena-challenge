# =====================================================================
#  perfil_datos.py  -  DATOS DEL PERFIL (US-04)
# =====================================================================
#  La "lógica" del perfil, sin dibujar nada:
#     - campos_perfil_iniciales(): datos de perfil de una cuenta nueva
#     - registrar_partida():       ¡LA FUNCIÓN QUE TU JUEGO DEBE LLAMAR al terminar
#                                   una partida! Actualiza estadísticas, logros e historial
#     - calcular_ranking():        posición del jugador y los mejores jugadores
#     - obtener_perfil():          junta todo lo que muestra la pantalla de perfil
#
#  Todo se guarda dentro de la cuenta del jugador en usuarios.json:
#     "estadisticas": {partidas_jugadas, victorias, derrotas, puntaje_total,
#                      mejor_puntaje, tiempo_total_seg}
#     "logros":       ["primera_partida", "primera_victoria", ...]
#     "historial":    [{"fecha", "resultado", "puntaje", "duracion_seg"}, ...]
#
#  Como se guarda en el archivo, los datos persisten entre sesiones
#  (el jugador los ve aunque haya cerrado y vuelto a abrir el juego).
# =====================================================================

import time

from config import PUNTOS_POR_NIVEL
from base_datos import cargar_usuarios, guardar_usuarios, buscar_cuenta_por_usuario
from logros import CATALOGO_LOGROS, evaluar_logros

# Nombres de las estadísticas que se guardan por jugador
CLAVES_ESTADISTICAS = ("partidas_jugadas", "victorias", "derrotas",
                       "puntaje_total", "mejor_puntaje", "tiempo_total_seg")


# ---------------------------------------------------------------------
# FECHAS Y FORMATOS
# ---------------------------------------------------------------------
def fecha_hoy():
    """Fecha actual, por ejemplo '25/10/2026'."""
    return time.strftime("%d/%m/%Y")


def fecha_hora_ahora():
    """Fecha y hora actuales, por ejemplo '25/10/2026 14:30'."""
    return time.strftime("%d/%m/%Y %H:%M")


def formatear_duracion(segundos):
    """Convierte segundos en un texto legible: '45 s', '12 min 05 s' o '2 h 03 min'."""
    segundos = int(segundos)
    horas, resto = divmod(segundos, 3600)       # divmod devuelve (cociente, resto)
    minutos, seg = divmod(resto, 60)
    if horas:
        return f"{horas} h {minutos:02d} min"
    if minutos:
        return f"{minutos} min {seg:02d} s"
    return f"{seg} s"


# ---------------------------------------------------------------------
# CAMPOS DEL PERFIL EN LA CUENTA
# ---------------------------------------------------------------------
def campos_perfil_iniciales():
    """Datos de perfil que se añaden a una cuenta NUEVA (se llama al registrarse)."""
    return {
        "avatar": "default",
        "fecha_registro": fecha_hoy(),
        "estadisticas": {clave: 0 for clave in CLAVES_ESTADISTICAS},
        "logros": [],
        "historial": [],
    }


def asegurar_campos_perfil(cuenta):
    """
    Rellena los campos de perfil que falten. Sirve para las cuentas creadas
    ANTES de existir el perfil, que no tienen estadísticas ni historial.
    """
    cuenta.setdefault("avatar", "default")
    cuenta.setdefault("fecha_registro", "Desconocida")
    estadisticas = cuenta.setdefault("estadisticas", {})
    for clave in CLAVES_ESTADISTICAS:
        estadisticas.setdefault(clave, 0)
    cuenta.setdefault("logros", [])
    cuenta.setdefault("historial", [])
    return cuenta


# ---------------------------------------------------------------------
# REGISTRAR UNA PARTIDA (la llamará tu juego)
# ---------------------------------------------------------------------
def registrar_partida(nombre_usuario, resultado, puntaje, duracion_seg):
    """
    Guarda el resultado de una partida terminada. Ejemplo de uso desde el juego:

        from perfil_datos import registrar_partida
        nuevos = registrar_partida(SESION.usuario, "victoria", 850, 420)

    Parámetros:
        resultado:    "victoria" o "derrota"
        puntaje:      puntos conseguidos en la partida
        duracion_seg: cuánto duró la partida, en segundos

    Actualiza las estadísticas, añade la partida al historial y desbloquea los
    logros que correspondan. Devuelve la lista de ids de logros NUEVOS
    (para que el juego pueda avisar "¡Logro desbloqueado!"), o None si
    el usuario no existe.
    """
    if resultado not in ("victoria", "derrota"):
        raise ValueError("resultado debe ser 'victoria' o 'derrota'")

    usuarios = cargar_usuarios()
    cuenta = buscar_cuenta_por_usuario(usuarios, nombre_usuario)
    if cuenta is None:
        return None
    asegurar_campos_perfil(cuenta)

    # --- Estadísticas ---
    est = cuenta["estadisticas"]
    est["partidas_jugadas"] += 1
    if resultado == "victoria":
        est["victorias"] += 1
    else:
        est["derrotas"] += 1
    est["puntaje_total"] += int(puntaje)
    est["mejor_puntaje"] = max(est["mejor_puntaje"], int(puntaje))
    est["tiempo_total_seg"] += int(duracion_seg)

    # --- Historial (la partida más reciente queda al final de la lista) ---
    cuenta["historial"].append({
        "fecha": fecha_hora_ahora(),
        "resultado": resultado,
        "puntaje": int(puntaje),
        "duracion_seg": int(duracion_seg),
    })

    # --- Logros ---
    nuevos = evaluar_logros(est, cuenta["logros"])
    cuenta["logros"].extend(nuevos)

    guardar_usuarios(usuarios)
    return nuevos


# ---------------------------------------------------------------------
# RANKING
# ---------------------------------------------------------------------
def calcular_ranking(usuarios, nombre_usuario, tamano_top=5):
    """
    Ordena a todos los jugadores que han jugado al menos una partida por
    puntaje total (si empatan, gana quien tenga más victorias).

    Devuelve un diccionario:
        "posicion":   puesto del jugador (None si aún no ha jugado)
        "total":      cuántos jugadores hay en el ranking
        "mi_puntaje": puntaje total del jugador
        "top":        lista de los mejores [{"posicion", "usuario", "puntaje"}, ...]
    """
    jugadores = []
    for u in usuarios:
        est = u.get("estadisticas", {})
        if est.get("partidas_jugadas", 0) > 0:
            jugadores.append((u.get("usuario", ""),
                              est.get("puntaje_total", 0),
                              est.get("victorias", 0)))

    # Orden: mayor puntaje primero (por eso el signo menos), luego más victorias, luego nombre
    jugadores.sort(key=lambda j: (-j[1], -j[2], j[0].lower()))

    top = []
    for i, (nombre, puntaje, _) in enumerate(jugadores[:tamano_top]):
        top.append({"posicion": i + 1, "usuario": nombre, "puntaje": puntaje})

    posicion = None
    mi_puntaje = 0
    for i, (nombre, puntaje, _) in enumerate(jugadores):
        if nombre.lower() == nombre_usuario.lower():
            posicion = i + 1
            mi_puntaje = puntaje

    return {"posicion": posicion, "total": len(jugadores),
            "mi_puntaje": mi_puntaje, "top": top}


# ---------------------------------------------------------------------
# PERFIL COMPLETO (lo que muestra la pantalla de perfil)
# ---------------------------------------------------------------------
def obtener_perfil(nombre_usuario):
    """
    Lee usuarios.json y devuelve un diccionario con TODO lo que necesita la
    pantalla de perfil, o None si la cuenta no existe.
    """
    usuarios = cargar_usuarios()
    cuenta = buscar_cuenta_por_usuario(usuarios, nombre_usuario)
    if cuenta is None:
        return None
    asegurar_campos_perfil(cuenta)      # Solo en memoria: aquí no se guarda nada

    # --- Estadísticas, más algunas calculadas ---
    est = dict(cuenta["estadisticas"])
    partidas = est["partidas_jugadas"]
    est["porcentaje_victorias"] = est["victorias"] * 100 / partidas if partidas else 0
    est["puntaje_promedio"] = est["puntaje_total"] / partidas if partidas else 0
    est["duracion_promedio_seg"] = est["tiempo_total_seg"] / partidas if partidas else 0

    # --- Logros: TODOS los del catálogo, marcando cuáles tiene ---
    logros = []
    for logro in CATALOGO_LOGROS:
        logros.append({
            "nombre": logro["nombre"],
            "descripcion": logro["descripcion"],
            "desbloqueado": logro["id"] in cuenta["logros"],
        })

    return {
        "usuario": cuenta["usuario"],
        "correo": cuenta.get("correo", ""),
        "correo_verificado": cuenta.get("correo_verificado", False),
        "avatar": cuenta["avatar"],
        "fecha_registro": cuenta["fecha_registro"],
        "nivel": 1 + est["puntaje_total"] // PUNTOS_POR_NIVEL,
        "estadisticas": est,
        "logros": logros,
        "ranking": calcular_ranking(usuarios, cuenta["usuario"]),
        # reversed() da vuelta la lista: la partida MÁS RECIENTE primero
        "historial": list(reversed(cuenta["historial"])),
    }