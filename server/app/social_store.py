import secrets
import time
import threading
from typing import Any


class AlmacenLoginSocial:
    """Flujos de autorización de proveedores sociales sin guardar secretos externos."""

    def __init__(self, cuentas):
        self._cuentas = cuentas
        self._bloqueo = threading.RLock()
        self._flujos: dict[str, dict[str, Any]] = {}

    def iniciar_google(self, redirect_uri: str) -> dict[str, Any]:
        state = secrets.token_urlsafe(24)
        with self._bloqueo:
            self._flujos[state] = {
                "proveedor": "google",
                "estado": "pendiente",
                "creado": time.time(),
            }
        return {"state": state, "redirect_uri": redirect_uri}

    def completar_google(
        self,
        state: str,
        google_subject: str,
        correo: str,
        nombre: str | None = None,
    ) -> dict[str, Any]:
        if not state:
            raise ValueError("state requerido.")
        if not google_subject:
            raise ValueError("Identidad de Google requerida.")

        with self._bloqueo:
            flujo = self._flujos.get(state)
            if flujo is None:
                raise ValueError("Flujo social no encontrado.")
            if flujo["estado"] != "pendiente":
                raise ValueError("El flujo social ya fue procesado.")

            login = self._cuentas.login_social_google(
                google_subject=google_subject,
                correo=correo,
                nombre=nombre,
            )
            flujo["estado"] = "completado"
            flujo["resultado"] = login
            return login

    def estado_google(self, state: str) -> dict[str, Any]:
        with self._bloqueo:
            flujo = self._flujos.get(state)
            if flujo is None:
                return {"estado": "desconocido"}
            if time.time() - flujo["creado"] > 15 * 60:
                flujo["estado"] = "expirado"
            if flujo["estado"] == "completado":
                return {"estado": "completado", "resultado": flujo["resultado"]}
            return {"estado": flujo["estado"]}
