# Webapp de estadísticas

Se sirve desde FastAPI en `http://127.0.0.1:8000/webapp/`.

## Funciones

- Inicio de sesión con usuario y contraseña.
- Inicio de sesión con Google cuando está configurado OAuth.
- Resumen de partidas, victorias, puntaje y mejor puntaje.
- Historial del usuario conectado.
- Ranking global.

## Ejecución

Desde la raíz del proyecto:

```powershell
docker compose up --build server
```

Abrir `http://127.0.0.1:8000/webapp/` en el navegador.

La cuenta y los resultados se leen de los archivos JSON administrados por el servidor.
