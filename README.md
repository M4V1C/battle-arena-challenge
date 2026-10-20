# Battle Arena Challenge

Guía técnica para preparar el entorno de desarrollo del equipo. Los comandos de esta guía usan **PowerShell en Windows** y parten de la raíz del repositorio, salvo que se indique lo contrario.

La descripción del producto, el MVP, la arquitectura, los sprints y el equipo están en [`docs/README.md`](docs/README.md). La **Wiki y el Board permanecen en Azure DevOps**; **GitHub se usa para control de versiones y CI**.

## Estructura del repositorio

```text
.
├── .github/workflows/ci.yml  # CI en GitHub Actions
├── client/                  # Cliente local de dos jugadores con Pygame
├── docs/                    # Documentación del producto
├── server/                  # API FastAPI, Dockerfile, dependencias y pruebas
├── .env.example             # Plantilla de configuración local de PostgreSQL
├── docker-compose.yml       # API y PostgreSQL 16
└── README.md
```

## Requisitos

- [Git](https://git-scm.com/downloads).
- [Python](https://www.python.org/downloads/) **3.12 recomendado**, para coincidir con Docker y CI. Es necesario para ejecutar la API y las pruebas fuera de Docker.
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) con Docker Compose y el motor de contenedores Linux. En Windows, habilitar el backend WSL2 y la virtualización; seguir los requisitos del instalador y reiniciar si lo solicita.
- [VS Code](https://code.visualstudio.com/) recomendado, con las extensiones **Python** y **Pylance** de Microsoft.
- Acceso al repositorio de GitHub y al Board/Wiki de Azure DevOps del equipo.

Docker ejecuta su propio Python dentro del contenedor; no utiliza el entorno virtual local. No se necesita instalar PostgreSQL directamente en Windows.

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

Editar `.env` y asignar una contraseña local propia a `POSTGRES_PASSWORD`. `POSTGRES_USER` y `POSTGRES_DB` definen el usuario y la base de datos iniciales. El archivo `.env` está ignorado por Git; no compartir contraseñas ni confirmarlo en commits.

Docker Compose lee este archivo para configurar PostgreSQL. Actualmente la API solo expone `/health`: **todavía no tiene conexión a la base de datos**, por lo que estas variables no configuran una conexión de FastAPI.

## Ejecutar con Docker

Desde la raíz del repositorio:

```powershell
docker compose up --build -d
docker compose ps
Invoke-RestMethod http://localhost:8000/health
docker compose exec db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Comprobar que ambos contenedores estén en ejecución, que `/health` devuelva `{"status":"ok"}` (PowerShell lo muestra como un objeto) y que PostgreSQL indique `accepting connections`. El endpoint comprueba la API, no la conectividad con PostgreSQL.

- API: http://localhost:8000
- Documentación interactiva de FastAPI: http://localhost:8000/docs
- PostgreSQL: puerto `5432` dentro de la red de Compose; no está publicado al equipo anfitrión.

Comandos de uso diario:

```powershell
docker compose logs -f
docker compose down
```

`down` detiene y elimina los contenedores, pero conserva los datos en el volumen `dbdata`. **No usar `docker compose down -v` salvo que se quiera borrar la base de datos local.** Cambiar las variables de PostgreSQL en `.env` no modifica usuarios, contraseñas ni bases ya inicializados en ese volumen.

La imagen no monta el código local: después de modificar el servidor, ejecutar nuevamente `docker compose up --build -d`.

## Ejecutar el cliente de juego

Con Docker Compose arriba y el entorno virtual activado:

```powershell
python -m pip install -r .\client\requirements.txt
python .\client\client.py
```

La ventana muestra dos cuadrados: **rojo** se mueve con `W`, `A`, `S`, `D`; **azul** con las flechas. El cliente se conecta al servidor TCP en `127.0.0.1:9000`. Para conectarse a un servidor en otra dirección, pasar el host:

```powershell
python .\client\client.py 192.168.1.25
```

También se pueden configurar `SERVER_HOST` y `SERVER_PORT`. El cliente envía las entradas y representa el estado que devuelve el servidor; el cálculo y los límites de movimiento viven en el servidor. Pygame permanece en su hilo principal y un hilo de red separado evita bloquear la ventana.

## Ejecutar la API sin Docker (opcional)

Con el entorno virtual activado, desde la raíz:

```powershell
python -m uvicorn app.main:app --app-dir .\server --reload --port 8000
```

Detener con `Ctrl+C`. No ejecutar a la vez este servidor y el contenedor de la API en el puerto `8000`. Si se necesita mantener ambos, usar otro puerto local, por ejemplo `--port 8001`. Para que el cliente funcione, el servidor TCP en `9000` también debe estar en ejecución.

## Pruebas y CI

Con el entorno virtual activado, desde la raíz:

```powershell
python -m pytest .\server\tests
```

Si la terminal ya está en la carpeta `server`, usar `python -m pytest`. Las pruebas actuales verifican `/health` y una ruta inexistente; no requieren Docker ni una base de datos.

El workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) usa Python 3.12, instala las dependencias del servidor, ejecuta `python -m pytest` desde `server` y construye las imágenes con Docker Compose. Se activa en cada *push* a `main` y en cada *pull request* dirigido a `main`; no se ejecuta por un *push* a `develop` por sí solo.

## Problemas frecuentes

| Síntoma | Qué revisar |
|---------|-------------|
| `python` apunta a `C:\msys64\...`, o no encuentra `pip`/`pytest` | Activar `.venv` en esa terminal o usar directamente `.\.venv\Scripts\python.exe` desde la raíz. No instalar las dependencias en el Python de MSYS2. |
| `docker` no se reconoce | Verificar la instalación de Docker Desktop y reiniciar VS Code por completo para recargar el PATH. |
| Docker muestra error de conexión o HTTP 500 | Revisar el estado y los avisos de Docker Desktop; ejecutar `docker version` y `wsl --list --verbose`. En el backend WSL2 debe estar disponible `docker-desktop`. Si la instalación solicita reiniciar Windows, hacerlo. No borrar distribuciones ni volúmenes para intentar repararlo. |
| El puerto `8000` está ocupado | Detener la otra instancia de la API o usar un puerto distinto al ejecutar Uvicorn localmente. |
| PostgreSQL aún no acepta conexiones | Esperar a que termine la inicialización y consultar `docker compose logs db`. El orden de arranque de Compose no garantiza que la base ya esté lista. |

## Flujo de trabajo con Git

- Usar `develop` como base de trabajo compartida y crear una rama por historia, por ejemplo `git switch -c feature/US-07-arena`.
- Antes de integrar cambios, ejecutar las pruebas y verificar el build con `docker compose build`.
- `main` debe recibir cambios mediante *pull request*, con el CI en verde y al menos una revisión.
- Usar mensajes [Conventional Commits](https://www.conventionalcommits.org/), por ejemplo `feat(server): agrega endpoint de salud`.
- Los commits referencian el work item de Azure DevOps (por ejemplo `AB#123`) para mantener trazabilidad con el Board.
- No versionar `.env`, `.venv`, credenciales ni datos locales de PostgreSQL.

## Documentación

- [`docs/README.md`](docs/README.md): producto, MVP, arquitectura, planificación y equipo.
- Wiki de Azure DevOps: documentación detallada del proyecto.
- Board de Azure DevOps: historias de usuario y seguimiento del trabajo.

## Licencia

Proyecto académico del TEC. Uso educativo.
