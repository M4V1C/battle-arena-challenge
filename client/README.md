# Cliente del juego

Cliente local de dos jugadores, organizado en módulos y clases:

- `client.py`: punto de entrada y configuración del host.
- `game.py`: clase `Juego`, ciclo gráfico de Pygame, teclado y representación.
- `network.py`: clase `ConexionServidor`; gestiona el protocolo TCP en un hilo
  para que las esperas de red no detengan la ventana.

Instalar las dependencias desde la raíz del repositorio y arrancar primero el
servidor (ver el [README principal](../README.md)):

```powershell
python -m pip install -r .\client\requirements.txt
python .\client\client.py
```

El cuadrado rojo se controla con `W`, `A`, `S`, `D`; el azul, con las flechas.
El cliente envía vectores de entrada y dibuja las posiciones calculadas por el
servidor. El servidor simula el movimiento a 60 Hz a 240 píxeles por segundo;
la velocidad usa tiempo transcurrido, así que no depende de los FPS ni del
intervalo de paquetes. El movimiento diagonal conserva la misma rapidez y los
límites de la arena se aplican en el servidor. Se puede indicar una dirección de servidor como primer argumento:
`python .\client\client.py 192.168.1.25`.