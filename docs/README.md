# Documentación del proyecto

## Battle Arena Challenge

Plataforma multijugador con integración hardware-software: dos jugadores se autentican, entran a una misma arena y controlan sus avatares en tiempo real con un dispositivo físico.

> Proyecto integrador del curso **CE-1105 Principios de Modelado en Ingeniería**
> Escuela de Ingeniería en Computadores, Instituto Tecnológico de Costa Rica (TEC) · II Semestre 2026

Esta página describe el producto y su alcance previsto. Para instalar herramientas, preparar el entorno, ejecutar el servidor y correr pruebas, consultar el [README técnico de la raíz](../README.md).

## Estado del proyecto

| Sprint | Enfoque | Entrega | Estado |
|--------|---------|---------|--------|
| Sprint 1 | Análisis, comprensión y planificación | 24 sep 2026 | Entregado |
| Sprint 2 | Primera implementación (MVP) | 22 oct 2026 | En desarrollo |
| Sprint 3 | Evolución del producto | 23 nov 2026 | Pendiente |

La implementación actual incluye una API base con FastAPI, un endpoint `/health`, una arena compartida con movimiento de dos jugadores, pruebas automatizadas y un entorno Docker con PostgreSQL 16. Las funcionalidades de juego descritas a continuación son el alcance previsto, no funcionalidades ya implementadas.

## Flujo que demuestra el MVP

```text
Usuario → autenticación → partida → servidor → hardware → comunicación → avatar → arena
```

El dispositivo de entrada previsto es un control de PS5, con teclado como alternativa en modo simulación.

## Arquitectura (resumen)

El sistema se compone de tres piezas principales:

| Componente | Responsabilidad prevista | Tecnología / estado |
|------------|-------------------------|---------------------|
| **API de cuentas y datos** | Registro, verificación de correo, login, perfil, avatares, configuración y persistencia | Base FastAPI y PostgreSQL 16 en Docker; funcionalidades y conexión a la base de datos pendientes |
| **Servidor de juego** | Procesa entradas y mantiene el estado autoritativo de los dos cuadrados en una arena compartida | FastAPI y servidor TCP con hilos por conexión; la lógica de movimiento está en `server/app/game_state.py` |
| **Cliente** | Ventana local de dos jugadores, lectura de teclado y representación del estado recibido | Python + pygame; rojo usa WASD y azul las flechas |

El cliente mantiene Pygame en el hilo principal y delega la comunicación TCP a un hilo de red. El servidor simula el movimiento a 60 Hz con una velocidad de 240 píxeles por segundo, independiente de los FPS o la frecuencia de paquetes; normaliza las diagonales y limita las posiciones a la arena. El estado compartido se sincroniza para atender conexiones concurrentes. Este prototipo ofrece una arena compartida y controles locales de dos jugadores; no implementa todavía salas independientes ni asignación de jugadores remotos.

El detalle de las vistas lógica, de despliegue y de componentes, patrones y justificación se mantiene en esta carpeta y en la **Wiki de Azure DevOps**.

## Criterios de pruebas del producto

Cada historia de usuario debe contar con al menos una prueba positiva y una negativa. Actualmente se prueban la respuesta de `/health` y el error 404 de una ruta inexistente. Las instrucciones para ejecutar las pruebas y el CI están en el [README técnico](../README.md#pruebas-y-ci).

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