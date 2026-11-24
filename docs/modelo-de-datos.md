# Modelo de datos - Battle Arena Challenge

La persistencia actual se guarda en archivos JSON y archivos locales.

## Archivos y datos persistentes

### Cuentas y perfiles

Archivo: `Epica 01-Gestion de usuarios/usuarios.json`

```json
{
  "usuario": "nombre",
  "correo": "correo@example.com",
  "contrasena_sal": "valor-hexadecimal",
  "contrasena_hash": "hash-pbkdf2",
  "correo_verificado": true,
  "avatar": "avatar_1",
  "fecha_registro": "26/10/2026",
  "estadisticas": {
    "partidas_jugadas": 0,
    "victorias": 0,
    "derrotas": 0,
    "puntaje_total": 0,
    "mejor_puntaje": 0,
    "tiempo_total_seg": 0
  },
  "logros": [],
  "historial": []
}
```

Las cuentas se leen y escriben mediante `Epica 01-Gestion de usuarios/base_datos.py`. La contraseña no se guarda en texto plano: se conserva una sal y el hash PBKDF2-SHA256.

### Avatares

Archivo de selección: `client/data/avatars.json`

```json
{
  "red": "avatar_1",
  "blue": "avatar_2"
}
```

Los avatares personalizados se copian a `client/data/custom_avatars/` y se identifican con `custom_<uuid>.<extension>`.

### Configuración de partida

Archivo: `server/data/game_config.json`

```json
{
  "condition": "points",
  "value": 20,
  "sensitivity": 1.0
}
```

`condition` puede ser `points` o `time`. `value` es positivo: puntos objetivo o minutos según el modo seleccionado.

### Escenarios

Archivos: `server/data/escenarios/*.json`

```json
{
  "id": "arena_clasica",
  "nombre": "Arena clásica",
  "limites": {"ancho": 1600, "alto": 900},
  "posiciones_iniciales": {
    "red": {"x": 100, "y": 100},
    "blue": {"x": 1460, "y": 760}
  },
  "reactor": {"x": 780, "y": 430, "ancho": 40, "alto": 40},
  "obstaculos": [],
  "puertas": [],
  "zonas_trampas": []
}
```

### Reglas de puntuación

Archivo: `server/data/reglas.json`

```json
{
  "puntos_por_energia": 1,
  "intervalo_extraccion": 0.5
}
```

## Datos temporales del servidor

- `EstadoJuego`: posiciones, dirección, puntos, prórroga y estado de puertas/trampas/reactor; se conserva solo mientras corre el proceso.
- `AlmacenAvatares`: selecciones e imágenes recibidas; se conserva solo en memoria del servidor.
- Notificaciones: lista corta de rechazos y eventos entregada al cliente por estado.

## Integridad actual

- Usuario y correo se buscan sin distinguir mayúsculas.
- Contraseñas almacenadas como sal + hash PBKDF2-SHA256.
- Los JSON se escriben primero en archivos temporales y luego se renombran.
- Si `usuarios.json` está vacío o dañado, el módulo comienza con una lista vacía y conserva una copia `.bak` cuando corresponde.
- Los partidos no usan identificadores persistentes todavía. El historial se guarda dentro de cada cuenta local.

Esta representación describe únicamente archivos JSON y datos temporales del proceso.
