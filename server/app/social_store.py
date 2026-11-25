import secrets
import time
import threading
from typing import Any

# Tiempo para completar el inicio de sesión en el proveedor.
VIGENCIA_FLUJO = 15 * 60
# Un flujo terminado (entregado, fallido o expirado) informa su resultado
# durante este tiempo y después se elimina de memoria.
RETENCION_FLUJO = 2 * 60
TERMINADOS = ("entregado", "fallido", "expirado")


class AlmacenLoginSocial:
    """Flujos de autorización de proveedores sociales sin guardar secretos externos."""

    def __init__(self, cuentas, reloj=time.time):
        self._cuentas = cuentas
        self._reloj = reloj
        self._bloqueo = threading.RLock()
        self._flujos: dict[str, dict[str, Any]] = {}

    def iniciar_google(self, redirect_uri: str) -> dict[str, Any]:
        state = secrets.token_urlsafe(24)
        with self._bloqueo:
            self._purgar()
            self._flujos[state] = {
                "proveedor": "google",
                "estado": "pendiente",
                "creado": self._reloj(),
            }
        return {"state": state, "redirect_uri": redirect_uri}

    def completar_google(
        self,
        state: str,
        google_subject: str,
        correo: str,
        nombre: str | None = None,
        correo_verificado: bool = False,
    ) -> dict[str, Any]:
        if not state:
            raise ValueError("state requerido.")
        if not google_subject:
            raise ValueError("Identidad de Google requerida.")

        with self._bloqueo:
            flujo = self._flujo_vigente(state)
            if flujo is None:
                raise ValueError("Flujo social no encontrado.")
            if flujo["estado"] != "pendiente":
                raise ValueError("El flujo social ya fue procesado.")

            try:
                login = self._cuentas.login_social_google(
                    google_subject=google_subject,
                    correo=correo,
                    nombre=nombre,
                    correo_verificado=correo_verificado,
                )
            except ValueError as error:
                self._terminar(flujo, "fallido", str(error))
                raise
            flujo["estado"] = "completado"
            flujo["resultado"] = login
            return login

    def fallar_google(self, state: str, mensaje: str) -> None:
        """Marca como fallido un flujo pendiente (cancelado o con error del proveedor)."""
        with self._bloqueo:
            flujo = self._flujo_vigente(state)
            if flujo is not None and flujo["estado"] == "pendiente":
                self._terminar(flujo, "fallido", mensaje)

    def estado_google(self, state: str) -> dict[str, Any]:
        with self._bloqueo:
            self._purgar()
            flujo = self._flujo_vigente(state)
            if flujo is None:
                return {"estado": "desconocido"}
            if flujo["estado"] == "completado":
                # El token se entrega una sola vez y no queda guardado en el flujo.
                resultado = flujo.pop("resultado")
                self._terminar(flujo, "entregado")
                return {"estado": "completado", "resultado": resultado}
            respuesta = {"estado": flujo["estado"]}
            if "mensaje" in flujo:
                respuesta["mensaje"] = flujo["mensaje"]
            return respuesta

    def _flujo_vigente(self, state: Any) -> dict[str, Any] | None:
        flujo = self._flujos.get(state) if isinstance(state, str) else None
        if (flujo is not None and flujo["estado"] in ("pendiente", "completado")
                and self._reloj() - flujo["creado"] > VIGENCIA_FLUJO):
            flujo.pop("resultado", None)
            self._terminar(flujo, "expirado")
        return flujo

    def _terminar(self, flujo: dict[str, Any], estado: str, mensaje: str | None = None) -> None:
        flujo["estado"] = estado
        flujo["terminado"] = self._reloj()
        if mensaje:
            flujo["mensaje"] = mensaje

    def _purgar(self) -> None:
        ahora = self._reloj()
        for state, flujo in list(self._flujos.items()):
            vencido = ahora - flujo["creado"] > VIGENCIA_FLUJO + RETENCION_FLUJO
            informado = flujo["estado"] in TERMINADOS and ahora - flujo["terminado"] > RETENCION_FLUJO
            if vencido or informado:
                del self._flujos[state]
