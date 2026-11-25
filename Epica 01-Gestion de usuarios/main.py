# =====================================================================
#  main.py  -  PUNTO DE ENTRADA DEL JUEGO  (ejecuta este archivo)
# =====================================================================
#  Para jugar:      python main.py
#
#  Este archivo solo contiene el BUCLE PRINCIPAL. Todo lo demás está en
#  los otros módulos:
#     config.py              constantes (colores, correo, tiempos...)
#     recursos.py            ventana y fuentes de pygame
#     base_datos.py          lectura/escritura de usuarios.json
#     validaciones.py        reglas de usuario, correo y contraseña
#     correo.py              envío de correos
#     sesion.py              quién ha iniciado sesión
#     componentes.py         campos de texto, botones, avatar...
#     estado.py              estado del programa y navegación entre pantallas
#     logros.py              catálogo de logros
#     perfil_datos.py        estadísticas, ranking e historial
#     cuentas.py             lógica de registro, verificación, login y recuperación
#     pantalla_*.py          cada pantalla del juego
#
#  PANTALLAS (cada una es un "estado" del programa):
#     "registro"      -> crear cuenta                       (US-01)
#     "verificacion"  -> escribir el código del correo      (US-02)
#     "login"         -> iniciar sesión                     (US-03)
#     "perfil"        -> perfil del jugador                 (US-04)
#     "rec_solicitud" -> pedir código de recuperación       (US-05)
#     "rec_nueva"     -> código y nueva contraseña          (US-05)
#     "juego"         -> área de juego (solo con sesión)
# =====================================================================

import pygame

from config import FPS
from recursos import RELOJ
from sesion import SESION
from estado import Estado, PANTALLAS, PANTALLAS_PROTEGIDAS, ir_a, dibujar_pantalla
from componentes import barra_sesion_presionada

# IMPORTANTE: importar cada pantalla hace que se "registre" en estado.py
# (cada archivo llama a registrar_pantalla() al final). Aunque aquí no usemos
# estos nombres directamente, SIN estos imports las pantallas no existirían.
import pantalla_registro
import pantalla_verificacion
import pantalla_login
import pantalla_recuperacion
import pantalla_juego
import pantalla_perfil


# =====================================================================
# BUCLE PRINCIPAL
# =====================================================================
# Todo juego de pygame repite 3 pasos muchas veces por segundo:
#     A) Leer eventos (teclado, mouse, cerrar ventana)
#     B) Actualizar la lógica
#     C) Dibujar la pantalla

def main():
    estado = Estado()
    ir_a(estado, "registro")       # Empezamos en el registro, con el primer campo listo

    ejecutando = True
    while ejecutando:

        # ---------- A) EVENTOS ----------
        for evento in pygame.event.get():

            # Cerrar la ventana
            if evento.type == pygame.QUIT:
                ejecutando = False
                continue

            # Clic en el avatar/nombre de arriba a la derecha -> abre el perfil
            if estado.pantalla != "perfil" and barra_sesion_presionada(evento):
                ir_a(estado, "perfil")
                continue

            # Cualquier otro evento se lo pasamos a la función de eventos
            # de la pantalla actual
            PANTALLAS[estado.pantalla]["eventos"](evento, estado)

        # ---------- B) LÓGICA ----------
        # Protección: sin sesión iniciada NO se puede entrar al área de juego
        # ni al perfil. Si alguien llega ahí sin sesión, vuelve al login.
        if estado.pantalla in PANTALLAS_PROTEGIDAS and not SESION.activa:
            ir_a(estado, "login")

        # ---------- C) DIBUJAR ----------
        dibujar_pantalla(estado)
        pygame.display.flip()                  # Mostramos lo que dibujamos
        RELOJ.tick(FPS)                        # Limita el juego a 60 cuadros por segundo

    pygame.quit()


# Esta condición hace que main() solo se ejecute al correr este archivo directamente
if __name__ == "__main__":
    main()