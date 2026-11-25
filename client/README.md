# Cliente del juego

Cliente de escritorio en Pygame. Cada proceso representa **a un jugador**: una partida necesita dos clientes, en el mismo equipo o en equipos distintos, conectados al mismo servidor.

- `client.py`: punto de entrada; lee el host y el puerto.
- `screens.py`: menú (inicio de sesión, inicio, avatares, configuración y selección de escenario).
- `game.py`: clase `Juego`: ventana de la partida, controles, HUD y dibujo del estado que envía el servidor.
- `network.py`: clase `ConexionServidor`; gestiona el protocolo TCP en un hilo para que las esperas de red no detengan la ventana.
- `controller.py`: lectura del mando con SDL GameController.
- `victory_screen.py`: ceremonia de fin de partida.
- `gestion_usuarios.py`: integra las pantallas de cuentas y perfil de `Epica 01-Gestion de usuarios`.

Instalar las dependencias desde la raíz del repositorio y arrancar primero el servidor (ver el [README principal](../README.md)):

```powershell
python -m pip install -r .\client\requirements.txt
python .\client\client.py
```

Uso:

1. Iniciar sesión con usuario o correo y contraseña, o con Google. Sin sesión no se entra a la partida: el `join` TCP exige el token.
2. *Empezar* → elegir escenario → *Confirmar escenario*. El primero en unirse es el rojo (anfitrión) y su escenario es el que se usa. La partida arranca sola cuando los dos jugadores están conectados.
3. *Configuracion* define la condición de fin (puntos o tiempo). Para guardar, la pantalla se une a la sala con la sesión y ocupa un puesto mientras está abierta.
4. *Avatares* guarda la selección en `client/data/avatars.json`, solo en este equipo.

Controles: el puesto rojo usa `W` `A` `S` `D`, `E` (interactuar) y `Q` (disparar); el azul, las flechas, `U` y `O`. Se cambian en `keybindings.json`. Con un mando de PS5: stick izquierdo para mover, X para interactuar y R2 para disparar.

Conexión: TCP en `127.0.0.1:9000` (`SERVER_HOST`, `SERVER_PORT` o el host como primer argumento: `python .\client\client.py 192.168.1.25`) y API de cuentas en `http://127.0.0.1:8000` (`BATTLE_API_URL`).

El cliente envía vectores de entrada y contadores de pulsaciones, y dibuja el estado calculado por el servidor. El servidor simula el movimiento a 60 Hz a 240 píxeles por segundo; la velocidad usa tiempo transcurrido, así que no depende de los FPS ni del intervalo de paquetes, y los límites de la arena se aplican en el servidor.