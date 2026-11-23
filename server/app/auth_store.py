import hashlib
import json
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any


ARCHIVO_USUARIOS = Path(__file__).resolve().parents[1] / "data" / "usuarios.json"
ARCHIVO_SESIONES = Path(__file__).resolve().parents[1] / "data" / "sesiones.json"


class AlmacenCuentas:
    def __init__(self, ruta_usuarios: Path = ARCHIVO_USUARIOS, ruta_sesiones: Path = ARCHIVO_SESIONES):
        self.ruta_usuarios = ruta_usuarios
        self.ruta_sesiones = ruta_sesiones
        self._bloqueo = threading.RLock()
        self.ruta_usuarios.parent.mkdir(parents=True, exist_ok=True)
        self.ruta_sesiones.parent.mkdir(parents=True, exist_ok=True)
        self._usuarios = self._leer_lista(self.ruta_usuarios)
        self._sesiones = self._leer_dict(self.ruta_sesiones)

    @staticmethod
    def _leer_lista(ruta: Path) -> list[dict[str, Any]]:
        if not ruta.exists():
            return []
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            return datos if isinstance(datos, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    @staticmethod
    def _leer_dict(ruta: Path) -> dict[str, Any]:
        if not ruta.exists():
            return {}
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            return datos if isinstance(datos, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _guardar_json(self, ruta: Path, datos: Any) -> None:
        temporal = ruta.with_suffix(ruta.suffix + ".tmp")
        temporal.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(temporal, ruta)

    @staticmethod
    def hashear(clave: str, sal: str | None = None) -> tuple[str, str]:
        sal = sal or secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), bytes.fromhex(sal), 200_000)
        return sal, digest.hex()

    @staticmethod
    def comparar(cuenta: dict[str, Any], clave: str) -> bool:
        sal = cuenta.get("contrasena_sal")
        hash_guardado = cuenta.get("contrasena_hash")
        if not sal or not hash_guardado:
            return False
        _, hash_calculado = AlmacenCuentas.hashear(clave, sal)
        return secrets.compare_digest(hash_guardado, hash_calculado)

    def registrar(self, usuario: str, correo: str, clave: str) -> dict[str, Any]:
        usuario = usuario.strip()
        correo = correo.strip().lower()
        with self._bloqueo:
            if any(u["usuario"].lower() == usuario.lower() for u in self._usuarios):
                raise ValueError("El usuario ya existe.")
            if any(u["correo"].lower() == correo.lower() for u in self._usuarios):
                raise ValueError("El correo ya está registrado.")
            sal, hash_clave = self.hashear(clave)
            codigo = f"{secrets.randbelow(900000) + 100000}"
            cuenta = {
                "usuario": usuario,
                "correo": correo,
                "contrasena_sal": sal,
                "contrasena_hash": hash_clave,
                "correo_verificado": False,
                "codigo_verificacion": codigo,
                "codigo_expira": time.time() + 15 * 60,
                "estadisticas": {"partidas": 0, "victorias": 0, "derrotas": 0, "puntaje_total": 0},
                "historial": [],
            }
            self._usuarios.append(cuenta)
            self._guardar_json(self.ruta_usuarios, self._usuarios)
            return {"ok": True, "usuario": usuario, "codigo_verificacion": codigo}

    def verificar(self, usuario: str, codigo: str) -> dict[str, Any]:
        with self._bloqueo:
            cuenta = self._buscar_usuario(usuario)
            if cuenta is None:
                raise ValueError("Cuenta no encontrada.")
            if time.time() > cuenta.get("codigo_expira", 0):
                raise ValueError("El código expiró.")
            if str(cuenta.get("codigo_verificacion", "")) != str(codigo):
                raise ValueError("Código incorrecto.")
            cuenta["correo_verificado"] = True
            cuenta.pop("codigo_verificacion", None)
            cuenta.pop("codigo_expira", None)
            self._guardar_json(self.ruta_usuarios, self._usuarios)
            return {"ok": True}

    def login(self, identificador: str, clave: str) -> dict[str, Any]:
        identificador = identificador.strip().lower()
        with self._bloqueo:
            cuenta = next((u for u in self._usuarios if u["usuario"].lower() == identificador or u["correo"].lower() == identificador), None)
            if cuenta is None or not self.comparar(cuenta, clave):
                raise ValueError("Usuario o contraseña incorrectos.")
            if not cuenta.get("correo_verificado", False):
                return {
                    "ok": False,
                    "no_verificado": True,
                    "usuario": cuenta["usuario"],
                    "correo": cuenta["correo"],
                }
            token = secrets.token_urlsafe(24)
            self._sesiones[token] = {"usuario": cuenta["usuario"], "expira": time.time() + 24 * 60 * 60}
            self._guardar_json(self.ruta_sesiones, self._sesiones)
            return {
                "ok": True,
                "token": token,
                "usuario": cuenta["usuario"],
                "correo": cuenta["correo"],
                "avatar": cuenta.get("avatar", "default"),
            }

    def validar_sesion(self, token: Any) -> str | None:
        if not isinstance(token, str):
            return None
        with self._bloqueo:
            sesion = self._sesiones.get(token)
            if not sesion or time.time() > sesion.get("expira", 0):
                self._sesiones.pop(token, None)
                return None
            return sesion["usuario"]

    def solicitar_recuperacion(self, correo: str) -> dict[str, Any]:
        correo = correo.strip().lower()
        with self._bloqueo:
            cuenta = next((u for u in self._usuarios if u["correo"].lower() == correo), None)
            if cuenta is None:
                return {"ok": True}
            codigo = f"{secrets.randbelow(900000) + 100000}"
            cuenta["recuperacion_codigo"] = codigo
            cuenta["recuperacion_expira"] = time.time() + 15 * 60
            cuenta["recuperacion_intentos"] = 0
            self._guardar_json(self.ruta_usuarios, self._usuarios)
            return {"ok": True, "codigo_recuperacion": codigo}

    def recuperar(self, correo: str, codigo: str, clave_nueva: str) -> dict[str, Any]:
        correo = correo.strip().lower()
        with self._bloqueo:
            cuenta = next((u for u in self._usuarios if u["correo"].lower() == correo), None)
            if cuenta is None or time.time() > cuenta.get("recuperacion_expira", 0):
                raise ValueError("Código incorrecto o expirado.")
            if str(cuenta.get("recuperacion_codigo", "")) != str(codigo):
                cuenta["recuperacion_intentos"] = cuenta.get("recuperacion_intentos", 0) + 1
                self._guardar_json(self.ruta_usuarios, self._usuarios)
                raise ValueError("Código incorrecto.")
            sal, hash_clave = self.hashear(clave_nueva)
            cuenta["contrasena_sal"] = sal
            cuenta["contrasena_hash"] = hash_clave
            cuenta.pop("recuperacion_codigo", None)
            cuenta.pop("recuperacion_expira", None)
            cuenta.pop("recuperacion_intentos", None)
            self._guardar_json(self.ruta_usuarios, self._usuarios)
            return {"ok": True}

    def reenviar_verificacion(self, usuario: str) -> dict[str, Any]:
        with self._bloqueo:
            cuenta = self._buscar_usuario(usuario)
            if cuenta is None:
                raise ValueError("Cuenta no encontrada.")
            if cuenta.get("correo_verificado", False):
                return {"ok": True, "ya_verificado": True}
            codigo = f"{secrets.randbelow(900000) + 100000}"
            cuenta["codigo_verificacion"] = codigo
            cuenta["codigo_expira"] = time.time() + 15 * 60
            self._guardar_json(self.ruta_usuarios, self._usuarios)
            return {"ok": True, "codigo_verificacion": codigo}

    def login_social_google(self, google_subject: str, correo: str, nombre: str | None = None) -> dict[str, Any]:
        correo = correo.strip().lower()
        nombre = (nombre or correo.split("@", 1)[0]).strip()
        with self._bloqueo:
            cuenta = next((u for u in self._usuarios if u.get("google_subject") == google_subject), None)
            if cuenta is None:
                cuenta = next((u for u in self._usuarios if u["correo"].lower() == correo), None)
            if cuenta is None:
                cuenta = {
                    "usuario": nombre[:20],
                    "correo": correo,
                    "contrasena_sal": "",
                    "contrasena_hash": "",
                    "correo_verificado": True,
                    "estadisticas": {"partidas": 0, "victorias": 0, "derrotas": 0, "puntaje_total": 0},
                    "historial": [],
                    "avatar": "default",
                }
                base = cuenta["usuario"]
                sufijo = 1
                while any(u["usuario"].lower() == cuenta["usuario"].lower() for u in self._usuarios):
                    cuenta["usuario"] = f"{base[:15]}_{sufijo}"[:20]
                    sufijo += 1
                self._usuarios.append(cuenta)

            cuenta["google_subject"] = google_subject
            cuenta["correo"] = correo
            cuenta["correo_verificado"] = True
            self._guardar_json(self.ruta_usuarios, self._usuarios)

            token = secrets.token_urlsafe(24)
            self._sesiones[token] = {"usuario": cuenta["usuario"], "expira": time.time() + 24 * 60 * 60}
            self._guardar_json(self.ruta_sesiones, self._sesiones)
            return {
                "ok": True,
                "token": token,
                "usuario": cuenta["usuario"],
                "correo": cuenta["correo"],
                "avatar": cuenta.get("avatar", "default"),
                "proveedor": "google",
            }

    def perfil(self, usuario: str) -> dict[str, Any]:
        cuenta = self._buscar_usuario(usuario)
        if cuenta is None:
            raise ValueError("Cuenta no encontrada.")
        estadisticas = cuenta.setdefault("estadisticas", {
            "partidas_jugadas": 0,
            "victorias": 0,
            "derrotas": 0,
            "puntaje_total": 0,
            "mejor_puntaje": 0,
            "tiempo_total_seg": 0,
        })
        cuenta.setdefault("historial", [])
        cuenta.setdefault("logros", [])
        partidas = estadisticas["partidas_jugadas"]
        return {
            "usuario": cuenta["usuario"],
            "correo": cuenta["correo"],
            "correo_verificado": cuenta.get("correo_verificado", False),
            "avatar": cuenta.get("avatar", "default"),
            "fecha_registro": cuenta.get("fecha_registro", "Desconocida"),
            "estadisticas": {
                **estadisticas,
                "porcentaje_victorias": estadisticas["victorias"] * 100 / partidas if partidas else 0,
                "puntaje_promedio": estadisticas["puntaje_total"] / partidas if partidas else 0,
                "duracion_promedio_seg": estadisticas["tiempo_total_seg"] / partidas if partidas else 0,
            },
            "logros": cuenta["logros"],
            "historial": list(reversed(cuenta["historial"])),
        }

    def listar(self) -> list[dict[str, Any]]:
        with self._bloqueo:
            return [{"usuario": u["usuario"], "correo": u["correo"], "correo_verificado": u.get("correo_verificado", False)} for u in self._usuarios]

    def _buscar_usuario(self, usuario: str) -> dict[str, Any] | None:
        usuario = usuario.lower()
        return next((u for u in self._usuarios if u["usuario"].lower() == usuario), None)
