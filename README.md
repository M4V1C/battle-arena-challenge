# Battle Arena Challenge

Plataforma multijugador con integración hardware-software: dos jugadores se autentican, entran a una misma arena y controlan sus avatares en tiempo real con un dispositivo físico.

> Proyecto integrador del curso **CE-1105 Principios de Modelado en Ingeniería**
> Escuela de Ingeniería en Computadores, Instituto Tecnológico de Costa Rica (TEC) · II Semestre 2026

## Estado del proyecto

| Sprint | Enfoque | Entrega | Estado |
|--------|---------|---------|--------|
| Sprint 1 | Análisis, comprensión y planificación | 24 sep 2026 | Entregado |
| Sprint 2 | Primera implementación (MVP) | 22 oct 2026 | En desarrollo |
| Sprint 3 | Evolución del producto | 23 nov 2026 | Pendiente |

## Flujo que demuestra el MVP

```
Usuario → autenticación → partida → servidor → hardware → comunicación → avatar → arena
```

## Arquitectura (resumen)

El sistema se compone de tres piezas principales:

| Componente | Responsabilidad | Tecnología |
|------------|-----------------|------------|
| **API de cuentas y datos** | Registro, verificación de correo, login, perfil, avatares, configuración y persistencia | _TODO: framework_ + _TODO: base de datos_ |
| **Servidor de juego** | Estado autoritativo de la partida en tiempo real: salas, posiciones, puntuación, ganador | _TODO: protocolo (p. ej. WebSocket)_ |
| **Cliente** | Pantallas, arena, audio y lectura del control físico | Python + pygame |

El detalle (vistas lógica, de despliegue y de componentes, patrones y justificación) está en la carpeta [`docs/`](docs/) y en la Wiki del proyecto.

## Estructura del repositorio

```
.
├── server/                  # API y servidor de juego (se ejecutan en Docker)
├── client/                  # Cliente pygame (se ejecuta en el equipo del jugador)
├── docs/                    # Modelo de datos, arquitectura, protocolo, bitácora
├── docker-compose.yml       # Orquestación de contenedores
├── azure-pipelines.yml      # Pipeline de CI (build y pruebas)
└── README.md
```

## Requisitos

- Git
- Docker y Docker Compose
- Python 3.12 o superior (para el cliente)
- Dispositivo de entrada: control de PS5 (o teclado en modo simulación)

## Cómo ejecutar

> Los comandos exactos se confirmarán al terminar el esqueleto del sistema.

**Servidor y base de datos**

```bash
docker compose up --build
```

**Cliente**

```bash
cd client
pip install -r requirements.txt
python main.py
```

## Pruebas

```bash
pytest server/tests
```

Cada historia de usuario cuenta con al menos una prueba positiva y una negativa. El pipeline de CI las ejecuta automáticamente en cada *pull request*.

## Flujo de trabajo con Git

- `main` es una rama protegida: solo recibe cambios mediante *pull request* con el CI en verde y al menos una revisión.
- Cada historia de usuario se desarrolla en una rama propia: `feature/US-07-arena`, `feature/US-12-control-fisico`, etc.
- Los commits referencian el work item de Azure DevOps (por ejemplo `AB#123`) para mantener trazabilidad con el Board.

## Equipo

| Integrante | Épica(s) a cargo |
|------------|------------------|
| _TODO: nombre_ | E1 — Gestión de usuarios |
| _TODO: nombre_ | E2 — Avatar y representación gráfica · E3 — Movimiento |
| _TODO: nombre_ | E4 — Proceso del juego |

## Documentación

- Wiki del proyecto (Azure DevOps)
- [`docs/`](docs/): modelo de datos, arquitectura, contrato de mensajes en tiempo real y bitácora

## Licencia

Proyecto académico del TEC. Uso educativo.
