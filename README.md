# Battle Arena Challenge

Guía técnica para preparar el entorno de desarrollo del equipo. Los comandos de esta guía usan **PowerShell en Windows** y parten de la raíz del repositorio, salvo que se indique lo contrario.

La descripción del producto, el MVP, la arquitectura, los sprints y el equipo están en [`docs/README.md`](docs/README.md). La **Wiki y el Board permanecen en Azure DevOps**; **GitHub se usa para control de versiones y CI**.

## Estructura del repositorio

```text
.
├── .github/workflows/ci.yml          # CI en GitHub Actions
├── client/                           # Cliente Pygame de un jugador (menú, partida, HUD, ceremonia)
├── Epica 01-Gestion de usuarios/     # Pantallas de cuentas y perfil que usa el cliente
├── docs/                             # Documentación del producto y modelo de datos
├── server/
│   ├── app/                          # API FastAPI y servidor de juego TCP
│   ├── data/                         # Reglas, escenarios, configuración y datos persistentes
│   ├── web/                          # Webapp de estadísticas (también para el móvil)
│   └── tests/                        # Pruebas del servidor
├── .env.example                      # Plantilla de variables (Google, SMTP, EXPOSE_CODES)
├── docker-compose.yml                # Contenedor del servidor (API 8000 y TCP 9000)
└── README.md
```

## Requisitos

- [Git](https://git-scm.com/downloads).
- [Python](https://www.python.org/downloads/) **3.12 recomendado**, para coincidir con Docker y CI. Es necesario para ejecutar la API y las pruebas fuera de Docker.
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) con Docker Compose y el motor de contenedores Linux. En Windows, habilitar el backend WSL2 y la virtualización; seguir los requisitos del instalador y reiniciar si lo solicita.
- [VS Code](https://code.visualstudio.com/) recomendado, con las extensiones **Python** y **Pylance** de Microsoft.
- Acceso al repositorio de GitHub y al Board/Wiki de Azure DevOps del equipo.

Docker ejecuta su propio Python dentro del contenedor; no utiliza el entorno virtual local.

## Preparación inicial (cada integrante)

### 1. Clonar el repositorio

```powershell
git clone https://github.com/M4V1C/battle-arena-challenge.git
cd battle-arena-challenge
git switch develop
```

Abrir esta carpeta como raíz del proyecto en VS Code. Para obtener cambios posteriores, usar `git pull --ff-only` en la rama compartida correspondiente, con el trabajo local guardado.

### 2. Verificar las herramientas

Abrir Docker Desktop y esperar a que indique que el motor está en ejecución.

```powershell
git --version
py -3.12 --version
docker --version
docker compose version
docker version
```

`docker version` debe mostrar las secciones **Client y Server**. Que funcione `docker --version` por sí solo no confirma que el motor esté listo.

### 3. Crear el entorno virtual e instalar dependencias

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\server\requirements.txt
python -c "import sys; print(sys.executable)"
```

La última línea debe apuntar a `.venv\Scripts\python.exe` dentro del repositorio. Si el comando `py` no está disponible, usar la ruta del intérprete de Python instalado para crear el entorno, verificando antes su versión; no usar por accidente el Python de MSYS2.

Cada integrante crea su propio entorno: **no copiar ni subir `.venv`**. La carpeta ya está excluida en [`.gitignore`](.gitignore).

En VS Code, ejecutar **Python: Select Interpreter** desde la paleta de comandos y seleccionar `.venv\Scripts\python.exe`. Abrir una terminal nueva; si no se activa automáticamente, ejecutar el comando de activación anterior.

Si PowerShell bloquea el script de activación y las políticas del equipo lo permiten, habilitarlo solo en esa sesión:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

También se puede usar el intérprete sin activar el entorno ni cambiar políticas:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\server\requirements.txt
.\.venv\Scripts\python.exe -m pytest .\server\tests
```

### 4. Preparar las variables de entorno

Copiar la plantilla **solo si todavía no existe un archivo `.env`**:

```powershell
Copy-Item .env.example .env
```

Editar `.env` solo para configurar las variables SMTP si se desean enviar códigos de correo. El archivo `.env` está ignorado por Git; no compartir contraseñas ni confirmarlo en commits. El proyecto no usa una conexión a datos externos.

#### Modo demo de códigos (`EXPOSE_CODES`)

El servidor **no envía correos**: los códigos de verificación de cuenta y de recuperación de contraseña se guardan en `server/data/usuarios.json`, pero por defecto la API **no** los devuelve en sus respuestas (`EXPOSE_CODES=0`). Así nadie puede verificar una cuenta ajena ni restablecer su contraseña con solo conocer el correo.

Para una demo o para desarrollo, se puede activar `EXPOSE_CODES=1` en `.env` (Docker Compose la pasa al contenedor) o en la terminal antes de arrancar la API:

```powershell
$env:EXPOSE_CODES = "1"
python -m uvicorn app.main:app --app-dir .\server --port 8000
```

Con `EXPOSE_CODES=1`, `POST /auth/register` y `POST /auth/verify/resend` incluyen `codigo_verificacion`, y `POST /auth/recovery/request` incluye `codigo_recuperacion`. Cualquier otro valor equivale a desactivado. No usar este modo fuera de una demo.

## Ejecutar con Docker

Desde la raíz del repositorio:

```powershell
docker compose up --build -d
docker compose ps
Invoke-RestMethod http://localhost:8000/health

```

Comprobar que el contenedor esté en ejecución y que `/health` devuelva `{"status":"ok"}` (PowerShell lo muestra como un objeto).

- API: http://localhost:8000
- Documentación interactiva de FastAPI: http://localhost:8000/docs
- Juego TCP: puerto `9000`

Comandos de uso diario:

```powershell
docker compose logs -f
docker compose down
```

`down` detiene y elimina los contenedores. El volumen `./server/data` conserva cuentas, sesiones, resultados y configuración de partida. La selección de avatares se guarda en el equipo de cada cliente (`client/data/`).

La imagen no monta el código local: después de modificar el servidor, ejecutar nuevamente `docker compose up --build -d`.

## Ejecutar el cliente de juego

Con el servidor arriba y el entorno virtual activado:

```powershell
python -m pip install -r .\client\requirements.txt
python .\client\client.py
```

Cada cliente representa **a un jugador**: para una partida se abren dos clientes, en el mismo equipo o en equipos distintos. En cada uno se inicia sesión, se pulsa *Empezar*, se elige escenario y se confirma. El primero en unirse ocupa el puesto rojo (anfitrión, su escenario es el que se usa) y el segundo el azul; la partida empieza sola cuando los dos están conectados.

| Acción | Teclado (puesto rojo) | Teclado (puesto azul) | Mando PS5 |
|---|---|---|---|
| Mover | `W` `A` `S` `D` | Flechas | Stick izquierdo |
| Interactuar (reactor, puertas) | `E` | `U` | Botón X |
| Disparar | `Q` | `O` | R2 |

Las teclas se cambian en [`client/keybindings.json`](client/keybindings.json). Cada cliente usa las del puesto que le asignó el servidor.

El cliente se conecta al servidor TCP en `127.0.0.1:9000` y a la API de cuentas en `http://127.0.0.1:8000`. Para otro servidor, pasar el host o usar variables de entorno:

```powershell
python .\client\client.py 192.168.1.25
$env:BATTLE_API_URL = "http://192.168.1.25:8000"
```

`SERVER_HOST` y `SERVER_PORT` cambian la dirección TCP. El cliente solo envía entradas y dibuja el estado que devuelve el servidor. La pantalla *Configuracion* se une a la sala con la sesión para guardar la condición de fin, así que ocupa un puesto mientras está abierta.

## Ejecutar la API sin Docker (opcional)

Con el entorno virtual activado, desde la raíz:

```powershell
python -m uvicorn app.main:app --app-dir .\server --reload --port 8000
```

Detener con `Ctrl+C`. No ejecutar a la vez este servidor y el contenedor de la API en el puerto `8000`. Si se necesita mantener ambos, usar otro puerto local, por ejemplo `--port 8001`. Al arrancar, la API levanta también el servidor de juego TCP en el puerto `9000`, en el mismo proceso y con los mismos datos.

## API y webapp

| Ruta | Acceso | Uso |
|---|---|---|
| `GET /health` | Pública | Estado del servicio |
| `POST /auth/register`, `/auth/verify`, `/auth/verify/resend` | Pública | Registro y verificación de correo |
| `POST /auth/login`, `/auth/validate` | Pública | Inicio de sesión (devuelve el token) y validación de un token |
| `POST /auth/recovery/request`, `/auth/recovery/reset` | Pública | Recuperación de contraseña |
| `POST /auth/social/google/start`, `GET /auth/social/google/callback`, `GET /auth/social/google/status` | Pública | Inicio de sesión con Google |
| `GET /auth/usuarios` | Pública | Usuarios y si su correo está verificado (sin correos) |
| `GET /ranking` | Pública | Ranking global |
| `GET /partida/estado` | Pública | Partida en curso: jugadores, puntaje, tiempo, reactor y eventos activos (sin posiciones, tokens ni correos) |
| `GET /usuarios/{usuario}/perfil`, `GET /usuarios/{usuario}/historial` | Token del mismo usuario | Perfil, estadísticas e historial |
| `GET /resultados`, `GET /resultados/{match_id}` | Token de un participante | Partidas propias (solo lectura) |
| `/webapp/` | Pública | Webapp de estadísticas |

Las rutas privadas exigen la cabecera `Authorization: Bearer <token>`: sin token o con un token inválido responden `401`, y con el token de otra cuenta, `403`. Los resultados solo los escribe el servidor de juego al terminar cada partida.

La webapp se abre en `http://localhost:8000/webapp/`. Desde un móvil en la misma red, usar la IP del equipo servidor, por ejemplo `http://192.168.1.25:8000/webapp/`.

## Pruebas y CI

Con el entorno virtual activado, desde la raíz:

```powershell
python -m pytest .\server\tests
$env:SDL_VIDEODRIVER = "dummy"; $env:SDL_AUDIODRIVER = "dummy"
python -m pytest .\client
```

Las pruebas del servidor cubren la API (cuentas, control de acceso, ranking, historial), el protocolo TCP y las reglas del juego; las del cliente, pantallas, HUD, control y ceremonia. No requieren Docker ni persistencia externa: usan archivos temporales. Las variables `SDL_*` permiten correr las pruebas de Pygame sin ventana.

El workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) usa Python 3.12, instala las dependencias del servidor y del cliente, ejecuta las pruebas del servidor y del cliente (con SDL en modo `dummy`) y construye la imagen con Docker Compose. Se activa en cada *push* y en cada *pull request* hacia `main` o `develop`.

## Problemas frecuentes

| Síntoma | Qué revisar |
|---------|-------------|
| `python` apunta a `C:\msys64\...`, o no encuentra `pip`/`pytest` | Activar `.venv` en esa terminal o usar directamente `.\.venv\Scripts\python.exe` desde la raíz. No instalar las dependencias en el Python de MSYS2. |
| `docker` no se reconoce | Verificar la instalación de Docker Desktop y reiniciar VS Code por completo para recargar el PATH. |
| Docker muestra error de conexión o HTTP 500 | Revisar el estado y los avisos de Docker Desktop; ejecutar `docker version` y `wsl --list --verbose`. En el backend WSL2 debe estar disponible `docker-desktop`. Si la instalación solicita reiniciar Windows, hacerlo. No borrar distribuciones ni volúmenes para intentar repararlo. |
| El puerto `8000` está ocupado | Detener la otra instancia de la API o usar un puerto distinto al ejecutar Uvicorn localmente. |
| El puerto `9000` está ocupado | Detener la instancia que usa el puerto o cambiar `SOCKET_PORT` y `SERVER_PORT` de forma coordinada. |

## Flujo de trabajo con Git

- Usar `develop` como base de trabajo compartida y crear una rama por historia, por ejemplo `git switch -c feature/US-07-arena`.
- Antes de integrar cambios, ejecutar las pruebas y verificar el build con `docker compose build`.
- `main` debe recibir cambios mediante *pull request*, con el CI en verde y al menos una revisión.
- Usar mensajes [Conventional Commits](https://www.conventionalcommits.org/), por ejemplo `feat(server): agrega endpoint de salud`.
- Los commits referencian el work item de Azure DevOps (por ejemplo `AB#123`) para mantener trazabilidad con el Board.
- No versionar `.env`, `.venv`, credenciales ni datos locales de cuentas o avatares.

## Documentación

- [`docs/README.md`](docs/README.md): producto, reglas del juego, arquitectura, planificación y equipo.
- [`docs/modelo-de-datos.md`](docs/modelo-de-datos.md): archivos JSON, esquemas e integridad de los datos.
- Wiki de Azure DevOps: documentación detallada del proyecto.
- Board de Azure DevOps: historias de usuario y seguimiento del trabajo.

## Licencia

Proyecto académico del TEC. Uso educativo.
