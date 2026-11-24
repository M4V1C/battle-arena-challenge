# Documentación del proyecto

## Battle Arena Challenge

Plataforma multijugador con integración hardware-software: dos jugadores se autentican, entran a una misma arena y controlan sus avatares en tiempo real con un dispositivo físico.

> Proyecto integrador del curso **CE-1105 Principios de Modelado en Ingeniería**
> Escuela de Ingeniería en Computadores, Instituto Tecnológico de Costa Rica (TEC) · II Semestre 2026

Esta página describe el producto, sus reglas y su estado. Para instalar herramientas, preparar el entorno, ejecutar el servidor y correr pruebas, consultar el [README técnico de la raíz](../README.md).

## Estado del proyecto

| Sprint | Enfoque | Entrega | Estado |
|--------|---------|---------|--------|
| Sprint 1 | Análisis, comprensión y planificación | 24 sep 2026 | Entregado |
| Sprint 2 | Primera implementación (MVP) | 22 oct 2026 | Entregado |
| Sprint 3 | Evolución del producto | 23 nov 2026 | Implementado en `develop`; cierre de hallazgos de auditoría en curso |

Implementado hoy:

- Cuentas: registro, verificación de correo, inicio de sesión, recuperación de contraseña e inicio de sesión con Google. Perfil, historial con fecha, estadísticas y ranking global.
- Partida de dos jugadores en tiempo real: cada jugador usa su propio cliente (en el mismo equipo o en equipos distintos) y se identifica con su sesión.
- Dos escenarios (`arena_clasica` y `laberinto`), reactor con extracción de energía, obstáculos, puertas, trampas, guardianes y eventos especiales.
- Fin de partida por tiempo o por puntos, prórrogas de dos minutos ante empate, guardado único del resultado y ceremonia de victoria.
- Webapp de estadísticas usable desde el navegador del móvil.

## Flujo de una partida

```text
Usuario → autenticación → join TCP con token → escenario → partida → servidor autoritativo → resultado → historial y ranking
```

1. Cada jugador abre su cliente e inicia sesión. El cliente se une a la sala por TCP con el token de su sesión.
2. El primero en unirse ocupa el puesto rojo (anfitrión) y el segundo el azul. El anfitrión elige el escenario; la partida empieza sola cuando los dos están conectados.
3. Los jugadores se mueven con el mando de PS5 o el teclado. El servidor valida cada acción y envía el mismo estado a ambos clientes.
4. Al cumplirse la condición de fin, el servidor cierra la partida, guarda el resultado una sola vez y los clientes muestran la ceremonia.

## Arquitectura (resumen)

| Componente | Responsabilidad | Tecnología |
|------------|-----------------|------------|
| **API de cuentas y datos** | Registro, verificación, login (contraseña y Google), sesiones, perfil, historial, ranking y webapp | FastAPI (`server/app/main.py`), persistencia en JSON en `server/data/` |
| **Servidor de juego** | Sala de dos puestos, estado autoritativo, reglas, eventos y guardado del resultado | Servidor TCP con un hilo por conexión y simulación a 60 Hz (`server/app/socket_server.py`, `server/app/game_state.py`); corre en el mismo proceso que la API |
| **Cliente** | Menú, partida, HUD y ceremonia; lectura de teclado y mando | Python + Pygame (`client/`), pantallas de cuentas en `Epica 01-Gestion de usuarios/` |
| **Webapp** | Estadísticas, historial y ranking desde cualquier navegador | HTML, CSS y JavaScript servidos por la API en `/webapp/` |

El servidor simula el movimiento a 60 Hz a 240 píxeles por segundo, independiente de los FPS o de la frecuencia de paquetes. El cliente solo envía entradas (ejes y contadores de pulsaciones) y dibuja el estado que recibe.

El detalle de las vistas lógica, de despliegue y de componentes se mantiene en esta carpeta y en la **Wiki de Azure DevOps**. El modelo de datos está en [modelo-de-datos.md](modelo-de-datos.md).

## Reglas del juego

Los valores salen de `server/data/reglas.json` y de las constantes de `server/app/game_state.py` y `server/app/eventos.py`.

### Puntuación

- **Extracción del reactor.** Un jugador cuyo centro está a 60 px o menos del centro del reactor pulsa *interactuar* y pasa a ser su operador. Mientras opera no se mueve ni dispara y suma `puntos_por_energia` (1) cada `intervalo_extraccion` (0,5 s). Vuelve a pulsar *interactuar* para soltarlo.
- Solo hay un operador a la vez. El operador pierde el reactor si un guardián lo toca, si cae en una trampa, si empieza una sobrecarga o si se desconecta; los puntos ya sumados se conservan.
- **Energía extra.** El primer jugador que toca el ícono suma `puntos_energia_extra` (3).
- **No dan puntos:** moverse, disparar, pulsar fuera de rango, repetir un mensaje ya procesado (los contadores de pulsaciones son acumulativos) ni ninguna acción antes de empezar o después de terminar.
- El disparo es solo visual: el proyectil desaparece al chocar y no afecta al rival.
- Acciones rechazadas y su código: fuera de rango (`out_of_range`), reactor ocupado (`reactor_busy`), sobrecarga (`reactor_overload`), jugador aturdido (`player_stunned`) o atrapado (`player_trapped`), partida inactiva (`match_not_active`) y cerrar una puerta sobre un jugador (`door_occupied`). El motivo aparece en el HUD del jugador.

### Fin de partida y empates

- La condición se configura en el cliente (`points` o `time`). Con puntos, gana el primero que alcanza el objetivo. Con tiempo, la partida dura los minutos indicados y gana quien tenga más puntos. Por defecto: 20 puntos.
- Si hay empate al cerrar, empieza una prórroga de dos minutos: se conservan los puntajes y el `match_id`, los jugadores y guardianes vuelven a su posición inicial, las trampas se recolocan y no hay eventos. Se repite hasta que haya ganador.
- Al terminar, el servidor congela la partida, guarda el resultado y todos los clientes reciben el mismo resultado y las mismas posiciones.
- Antes de guardar, el servidor compara cada puntaje con el mejor puntaje personal y el mejor global de las partidas ya guardadas, y lo envía en `match.result.records` (`previous_best`, `personal_best`, `global_best`). La ceremonia muestra los récords batidos.

### Obstáculos, puertas y trampas

- **Barreras** bloquean a jugadores, guardianes y disparos. Las zonas fuera de `zonas_transitables` bloquean a jugadores y guardianes. Nadie sale de la arena de 1600 × 900.
- **Puertas.** *Interactuar* a 90 px o menos del centro de una puerta la abre o la cierra. Cerrada es sólida; no se puede cerrar con un jugador dentro.
- **Trampas.** En cada partida se colocan al azar tres trampas distintas, lejos del reactor y de las apariciones. Al entrar, el jugador queda inmovilizado y sus acciones se rechazan:

| Trampa | Inmoviliza | Efecto adicional |
|---|---|---|
| Jaula | 2,5 s | Ninguno |
| Arenas movedizas | 1,75 s | Luego se mueve a la mitad de velocidad durante 2 s |
| Inversión | 1,25 s | El avatar se dibuja de cabeza |

### Guardianes

- Hay cuatro guardianes de 40 px, uno en cada esquina del escenario.
- Cada guardián persigue al jugador más cercano que no esté inmovilizado (por trampa o aturdimiento). Si los dos están inmovilizados, espera quieto.
- Se mueven a `velocidad_guardian` (120 px/s) y respetan barreras, puertas cerradas, zonas no transitables y los límites.
- Al tocar a un jugador (aunque ya esté atrapado) le suman `duracion_aturdimiento` (2 s) de inmovilización y lo marcan como aturdido. Si era el operador, suelta el reactor. Un contacto continuo cuenta una sola vez.
- No modifican puntajes. Durante la *tregua* se detienen y no aturden.

### Eventos especiales

El servidor programa el calendario al iniciar cada partida. El horizonte `H` es la duración configurada (minutos × 60) o, en modo puntos, el tiempo mínimo para alcanzar el objetivo (puntos × `intervalo_extraccion` / `puntos_por_energia`). Duración de cada evento = mínimo entre el tope y la fracción de `H` indicada (con un mínimo de 0,05 s).

| Evento | Cuándo empieza | Duración | Efecto |
|---|---|---|---|
| Energía extra (×3) | 8 %, 32 % y 58 % de `H` | 8 % de `H`, máx. 5 s | Ícono en una posición libre al azar; +3 al primero que lo toca |
| +5 guardianes | 22 % de `H` | 20 % de `H`, máx. 10 s | Cinco guardianes temporales en posiciones libres al azar; luego desaparecen |
| Sobrecarga (×2 o ×3) | Al azar entre 12-18 % y 52-58 % de `H`; con 50 % de probabilidad, otra entre 78-84 % | 8 % de `H`, máx. 4 s | El reactor no extrae, se suelta al operador y *interactuar* se rechaza |
| Impulso | 40 % de `H` | 12 % de `H`, máx. 5 s | Todos se mueven 50 % más rápido |
| Tregua | 70 % de `H` | 12 % de `H`, máx. 5 s | Los guardianes se detienen y no aturden |

Ejemplo con 3 minutos (`H` = 180 s): energías a los 14,4 s, 57,6 s y 104,4 s; guardianes extra a los 39,6 s; impulso a los 72 s; tregua a los 126 s. Cada evento empieza y termina una sola vez; al terminar se restauran las condiciones y al cerrar la partida se cierran los activos. El inicio y el fin de cada evento llegan como notificación y el HUD muestra los activos con su tiempo restante.

### Ranking global

`GET /ranking` es público y suma todas las partidas guardadas por usuario: puntaje total, victorias, partidas y mejor puntaje. El orden es:

1. Mayor puntaje total.
2. En empate, más victorias.
3. Si sigue el empate, nombre de usuario en orden alfabético (sin distinguir mayúsculas).

Una partida cuenta una sola vez (por `match_id`) y el ranking se recalcula en cada consulta, así que coincide siempre con el historial guardado.

## Acceso móvil

La webapp se abre desde el navegador del móvil en `http://<IP-del-servidor>:8000/webapp/`, con el móvil en la misma red que el servidor. Se adapta a pantallas de 900 px y de 560 px o menos. Permite iniciar sesión con usuario o correo y contraseña (o con Google, si está configurado) y consultar el resumen de estadísticas, el historial con fecha y el ranking global. Mientras el panel está abierto, muestra la partida en curso consultando `GET /partida/estado` cada 1,5 s. Las consultas privadas usan el token de la sesión; al cerrar sesión se borra del navegador.

## Criterios de pruebas del producto

Cada historia de usuario debe contar con al menos una prueba positiva y una negativa. Las pruebas del servidor están en `server/tests/` (API, control de acceso, TCP, reglas, escenarios, guardianes, eventos, fin de partida y persistencia) y las del cliente en `client/test_*.py` (HUD, pantallas, control, configuración y ceremonia). El CI las ejecuta en cada *push* y *pull request* hacia `main` o `develop`. Las instrucciones están en el [README técnico](../README.md#pruebas-y-ci).

## Equipo

| Integrante | Épica(s) a cargo |
|------------|------------------|
| _TODO: nombre_ | E1 — Gestión de usuarios |
| _TODO: nombre_ | E2 — Avatar y representación gráfica · E3 — Movimiento |
| _TODO: nombre_ | E4 — Proceso del juego |

## Organización de la documentación

- **Wiki de Azure DevOps:** documentación detallada del proyecto.
- **Board de Azure DevOps:** historias de usuario, work items y seguimiento de los sprints.
- **Esta carpeta:** modelo de datos, arquitectura, contrato de mensajes en tiempo real y bitácora, conforme se incorporen al repositorio.
- **GitHub:** control de versiones y pipeline de CI con GitHub Actions.