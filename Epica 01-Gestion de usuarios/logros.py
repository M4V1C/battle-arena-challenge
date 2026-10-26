# =====================================================================
#  logros.py  -  CATÁLOGO DE LOGROS
# =====================================================================
#  Aquí defines TODOS los logros del juego. Cada logro tiene:
#     "id"          -> identificador interno (se guarda en usuarios.json)
#     "nombre"      -> nombre que ve el jugador
#     "descripcion" -> qué hay que hacer para conseguirlo
#     "condicion"   -> una función que recibe las estadísticas del jugador
#                      y devuelve True cuando ya cumple el logro
#
#  (La palabra 'lambda' crea una función pequeña en una sola línea:
#   "lambda e: e['victorias'] >= 1"  significa  "dado e, devuelve si e['victorias'] >= 1")
#
#  Los de abajo son EJEMPLOS temáticos: cámbialos, bórralos o agrega los tuyos
#  según las reglas reales de tu juego. Para agregar uno, copia un bloque y
#  cambia su id, nombre, descripción y condición.
#
#  Las "estadisticas" disponibles son:
#     partidas_jugadas, victorias, derrotas, puntaje_total,
#     mejor_puntaje, tiempo_total_seg
# =====================================================================

CATALOGO_LOGROS = [
    {
        "id": "primera_partida",
        "nombre": "Primer encendido",
        "descripcion": "Juega tu primera partida.",
        "condicion": lambda e: e["partidas_jugadas"] >= 1,
    },
    {
        "id": "primera_victoria",
        "nombre": "Reactor estable",
        "descripcion": "Gana tu primera partida.",
        "condicion": lambda e: e["victorias"] >= 1,
    },
    {
        "id": "cinco_victorias",
        "nombre": "Jefe de turno",
        "descripcion": "Gana 5 partidas.",
        "condicion": lambda e: e["victorias"] >= 5,
    },
    {
        "id": "diez_partidas",
        "nombre": "Operador veterano",
        "descripcion": "Juega 10 partidas.",
        "condicion": lambda e: e["partidas_jugadas"] >= 10,
    },
    {
        "id": "puntaje_alto",
        "nombre": "Máxima potencia",
        "descripcion": "Consigue 1000 puntos en una sola partida.",
        "condicion": lambda e: e["mejor_puntaje"] >= 1000,
    },
    {
        "id": "turno_doble",
        "nombre": "Turno doble",
        "descripcion": "Acumula 1 hora de juego.",
        "condicion": lambda e: e["tiempo_total_seg"] >= 3600,
    },
]


def evaluar_logros(estadisticas, ya_desbloqueados):
    """
    Revisa el catálogo y devuelve la lista de ids de los logros que el jugador
    cumple AHORA y que todavía no tenía desbloqueados.
    """
    nuevos = []
    for logro in CATALOGO_LOGROS:
        if logro["id"] not in ya_desbloqueados and logro["condicion"](estadisticas):
            nuevos.append(logro["id"])
    return nuevos