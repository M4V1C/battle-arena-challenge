
import pygame

from hud_notifications import NotificacionesHUD


def test_agregar_notificacion(monkeypatch):
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 1000)

    hud = NotificacionesHUD()
    hud.agregar("Trampa activada", duracion=3000)

    assert len(hud._notificaciones) == 1
    assert hud._notificaciones[0].mensaje == "Trampa activada"
    assert hud._notificaciones[0].expiracion == 4000


def test_notificacion_no_expirada(monkeypatch):
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 1000)

    hud = NotificacionesHUD()
    hud.agregar("Puerta bloqueada", duracion=3000)

    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 3999)
    hud.actualizar()

    assert len(hud._notificaciones) == 1


def test_notificacion_expirada(monkeypatch):
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 1000)

    hud = NotificacionesHUD()
    hud.agregar("Guardian cercano", duracion=3000)

    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 4000)
    hud.actualizar()

    assert len(hud._notificaciones) == 0


def test_varias_notificaciones(monkeypatch):
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 1000)

    hud = NotificacionesHUD()
    hud.agregar("Trampa activada")
    hud.agregar("Puerta abierta")
    hud.agregar("Reactor disponible")

    assert len(hud._notificaciones) == 3


def test_color_personalizado(monkeypatch):
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 1000)

    hud = NotificacionesHUD()
    hud.agregar("Accion rechazada", (255, 100, 100))

    assert hud._notificaciones[0].color == (255, 100, 100)
