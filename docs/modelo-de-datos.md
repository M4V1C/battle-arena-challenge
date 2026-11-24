# Modelo de datos - Battle Arena Challenge

La persistencia se guarda en archivos JSON. Los datos compartidos viven en `server/data/` y los administra el servidor; Docker Compose monta esa carpeta como volumen (`./server/data:/app/data`). El cliente de escritorio solo guarda localmente la selección de avatares.

| Archivo | Lo escribe | En Git |
|---|---|---|
| `server/data/usuarios.json` | `server/app/auth_store.py` | No (datos locales) |
| `server/data/sesiones.json` | `server/app/auth_store.py` | No |
| `server/data/resultados.json` | `server/app/resultados_store.py` | No |
| `server/data/game_config.json` | `server/app/game_config.py` | Sí (valor inicial) |
| `server/data/reglas.json` | Edición manual | Sí |
| `server/data/escenarios/*.json` | Edición manual | Sí |
| `client/data/avatars.json` y `client/data/custom_avatars/` | `client/avatar_repository.py`, `client/avatar_images.py` | No |

## Archivos y datos persistentes

### Cuentas

Archivo: `server/data/usuarios.json` (lista de cuentas).

```json
{
  "usuario": "ana",
  "correo": "ana@example.com",
  "contrasena_sal": "valor-hexadecimal",
  "contrasena_hash": "hash-pbkdf2-sha256",
  "correo_verificado": true,
  "codigo_verificacion": "123456",
  "codigo_expira": 1795000000.0,
  "google_subject": "identificador-de-google",
  "avatar": "default"
}
```

- `codigo_verificacion` y `codigo_expira` solo existen mientras la cuenta no está verificada; el código vale 15 minutos. `recuperacion_codigo`, `recuperacion_expira` y `recuperacion_intentos` solo existen durante una recuperación de contraseña (15 minutos).
- El servidor no envía correos. La API solo devuelve esos códigos en modo demo (`EXPOSE_CODES=1`, ver el README).
- `google_subject` aparece cuando la cuenta se vinculó con Google. Las cuentas creadas con Google no tienen contraseña local (sal y hash vacíos) y nunca se guarda la contraseña del proveedor.
- `estadisticas` e `historial` dentro de la cuenta son campos heredados del Sprint 2: las estadísticas que muestran el perfil y la web se calculan con `resultados.json`.
- La contraseña se guarda como sal + hash PBKDF2-SHA256 con 200 000 iteraciones.

### Sesiones

Archivo: `server/data/sesiones.json` (objeto indexado por token).

```json
{
  "token-aleatorio": {"usuario": "ana", "expira": 1795000000.0}
}
```

El token se crea al iniciar sesión (contraseña o Google) y vence a las 24 horas. Lo exigen el `join` TCP y las rutas privadas de la API, en la cabecera `Authorization: Bearer <token>`.

### Resultados de partidas

Archivo: `server/data/resultados.json`.

```json
{
  "partidas": [
    {
      "match_id": "3bf9433fbb1346888c37445c1ffe1c80",
      "fecha": "2026-11-24T21:05:00+00:00",
      "winner": "red",
      "elapsed": 60.0,
      "overtime": 0,
      "condition": "time",
      "value": 1,
      "jugadores": {
        "red": {"usuario": "ana", "score": 61, "avatar": null},
        "blue": {"usuario": "beto", "score": 3, "avatar": null}
      }
    }
  ]
}
```

| Campo | Significado |
|---|---|
| `match_id` | Identificador único (uuid4 hexadecimal). Se conserva durante las prórrogas. |
| `fecha` | Momento en que se guardó el resultado, en ISO 8601 y UTC. Los registros anteriores a este campo no lo tienen y se leen igual (`null`). |
| `winner` | Puesto ganador: `red` o `blue`. |
| `elapsed` | Duración en segundos, incluidas las prórrogas. |
| `overtime` | Número de prórrogas de dos minutos. |
| `condition`, `value` | Condición de fin configurada (`points` o `time`) y su valor (puntos o minutos). |
| `jugadores.<puesto>` | Usuario autenticado que ocupó el puesto, puntaje final y avatar. |

Solo el servidor de juego escribe resultados: lo hace una vez, al cerrar la partida, en el mismo proceso que la API (`server/app/game_state.py` y `guardar_resultado_final` en `server/app/socket_server.py`). La API no tiene rutas para escribir resultados.

El historial de un usuario (`GET /usuarios/{usuario}/historial`, con su token) devuelve por partida: `match_id`, `fecha`, `puesto`, `resultado` (`victoria` o `derrota`), `score`, `winner`, `elapsed`, `overtime`, `condition` y `value`. El perfil agrega `partidas_jugadas`, `victorias`, `derrotas`, `puntaje_total`, `mejor_puntaje` y `tiempo_total_seg`.

### Avatares

Archivo de selección en cada equipo cliente: `client/data/avatars.json`

```json
{
  "red": "avatar_1",
  "blue": "avatar_2"
}
```

Los avatares personalizados se copian a `client/data/custom_avatars/` y se identifican con `custom_<uuid>.<extension>`. Esta selección es local: cada equipo dibuja los avatares según su propio archivo. El servidor tiene un almacén de avatares en memoria (`server/app/avatar_store.py`) que no se persiste.

### Configuración de partida

Archivo: `server/data/game_config.json`

```json
{
  "condition": "points",
  "value": 20,
  "sensitivity": 1.0
}
```

`condition` puede ser `points` o `time`. `value` es un entero mayor que cero: puntos objetivo o minutos. `sensitivity` es un número positivo reservado: hoy no cambia la velocidad. La configuración se lee al iniciar cada partida; cambiarla después no afecta la partida en curso. Por TCP, `get_config` es libre y `save_config` exige haber hecho `join`.

### Escenarios

Archivos: `server/data/escenarios/*.json` (`arena_clasica` y `laberinto`), validados por `server/app/escenarios.py`.

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
  "obstaculos": [{"x": 300, "y": 250, "ancho": 200, "alto": 40}],
  "puertas": [{"id": "puerta_central", "x": 600, "y": 400, "ancho": 40, "alto": 120}],
  "zonas_transitables": [{"x": 0, "y": 0, "ancho": 1600, "alto": 900}],
  "guardianes": [{"id": "noroeste", "x": 20, "y": 20}],
  "trampas": [{"tipo": "jaula", "duracion": 2.5}],
  "tema": {"background": [30, 30, 40], "obstacle": [110, 110, 125],
           "door_closed": [230, 145, 65], "door_open": [90, 215, 130],
           "reactor": [250, 210, 40]}
}
```

- Las dimensiones deben ser enteros positivos y, para jugar, exactamente 1600 × 900. Todo rectángulo debe quedar dentro de la arena.
- Las posiciones iniciales no pueden caer dentro de obstáculos, del reactor ni de puertas, y deben quedar completas dentro de una zona transitable.
- `zonas_transitables` es opcional; por defecto es toda la arena. Fuera de esas zonas no se puede caminar.
- `trampas` define tipo y duración; la **posición** de cada trampa se elige al azar al iniciar cada partida. El campo `zonas_trampas` existe en los archivos actuales pero el servidor no lo usa.
- Sin `guardianes`, el servidor coloca cuatro en las esquinas.

### Reglas

Archivo: `server/data/reglas.json`, validado por `server/app/reglas.py` (todos los valores deben ser positivos).

```json
{
  "puntos_por_energia": 1,
  "intervalo_extraccion": 0.5,
  "duracion_aturdimiento": 2.0,
  "velocidad_guardian": 120.0,
  "puntos_energia_extra": 3
}
```

| Clave | Uso |
|---|---|
| `puntos_por_energia` | Puntos que suma el operador del reactor en cada extracción. |
| `intervalo_extraccion` | Segundos de operación continua entre una extracción y la siguiente. |
| `duracion_aturdimiento` | Segundos que suma el contacto de un guardián al tiempo inmovilizado del jugador. |
| `velocidad_guardian` | Velocidad de los guardianes en píxeles por segundo. |
| `puntos_energia_extra` | Puntos que recibe quien toma una energía extra. |

Las reglas completas del juego están en [`docs/README.md`](README.md#reglas-del-juego).

## Datos temporales del servidor

- `EstadoJuego` (`server/app/game_state.py`): sala, puestos, posiciones, puntajes, reactor, puertas, trampas, guardianes, eventos y prórrogas. Vive en memoria mientras corre el proceso; si los dos jugadores se desconectan antes del final, la sala se vacía y la partida se descarta sin guardar resultado.
- `AlmacenAvatares` (`server/app/avatar_store.py`): selecciones e imágenes recibidas por TCP; solo en memoria.
- Notificaciones: las últimas 20 (rechazos, eventos, contactos de guardián, fin de partida), con identificador creciente, dentro de cada estado.
- Flujos de inicio de sesión con Google: en memoria. Un flujo pendiente vence a los 15 minutos. Si el usuario cancela o el proveedor falla, el flujo queda `fallido` con un mensaje genérico. El token se entrega una sola vez (después el estado es `entregado`). Los flujos terminados se borran 2 minutos después.
- Solo se vincula una cuenta local por su correo, o se crea una cuenta nueva, si Google confirma el correo (`email_verified`).

## Integridad actual

- Usuario y correo se buscan sin distinguir mayúsculas; no puede haber dos cuentas con el mismo usuario ni con el mismo correo.
- Cada archivo JSON se escribe primero en un archivo temporal y luego se reemplaza con `os.replace`, de modo que nunca queda a medio escribir.
- Cada almacén usa un candado (`threading`) para que las escrituras concurrentes de los hilos TCP y HTTP no se mezclen.
- Un resultado se guarda una sola vez por `match_id`: un reintento devuelve el registro existente sin modificarlo, incluida su `fecha`. El cierre de la partida también está protegido contra dobles llamadas.
- `resultados.json` en el formato anterior (lista con `id`/`players`/`username`) se migra al leerlo, sin perder historial.
- `game_config.json`, `reglas.json` y los escenarios se validan al cargarlos; un valor inválido se rechaza sin modificar el archivo.
- Límites conocidos: los almacenes cargan el archivo al iniciar y luego trabajan en memoria, así que solo un proceso del servidor debe usar `server/data/` a la vez. Los avatares del servidor no se persisten.

Esta representación describe únicamente archivos JSON y datos temporales del proceso.
