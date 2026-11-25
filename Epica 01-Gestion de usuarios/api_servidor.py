import json
import os
import urllib.error
import urllib.request
import urllib.parse


BASE_URL = os.environ.get("BATTLE_API_URL", "http://127.0.0.1:8000").rstrip("/")


def llamar(metodo: str, ruta: str, datos: dict | None = None, token: str | None = None):
    cuerpo = None if datos is None else json.dumps(datos).encode("utf-8")
    cabeceras = {"Content-Type": "application/json"}
    if token:
        cabeceras["Authorization"] = f"Bearer {token}"
    peticion = urllib.request.Request(
        BASE_URL + ruta,
        data=cuerpo,
        method=metodo,
        headers=cabeceras,
    )
    try:
        with urllib.request.urlopen(peticion, timeout=8) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            detalle = json.loads(error.read().decode("utf-8")).get("detail", str(error))
        except (json.JSONDecodeError, AttributeError):
            detalle = str(error)
        raise ValueError(detalle) from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise ValueError("No se pudo conectar al servidor de cuentas.") from error


def registrar(usuario: str, correo: str, clave: str):
    return llamar("POST", "/auth/register", {"usuario": usuario, "correo": correo, "clave": clave})


def verificar(usuario: str, codigo: str):
    return llamar("POST", "/auth/verify", {"usuario": usuario, "codigo": codigo})


def login(identificador: str, clave: str):
    return llamar("POST", "/auth/login", {"identificador": identificador, "clave": clave})


def solicitar_recuperacion(correo: str):
    return llamar("POST", "/auth/recovery/request", {"correo": correo})


def perfil(usuario: str, token: str | None = None):
    usuario_codificado = urllib.parse.quote(usuario.strip(), safe="")
    return llamar("GET", f"/usuarios/{usuario_codificado}/perfil", token=token)


def ranking():
    return llamar("GET", "/ranking")


def historial(usuario: str, token: str | None = None):
    usuario_codificado = urllib.parse.quote(usuario.strip(), safe="")
    return llamar("GET", f"/usuarios/{usuario_codificado}/historial", token=token)


def restablecer(correo: str, codigo: str, clave_nueva: str):
    return llamar("POST", "/auth/recovery/reset", {"correo": correo, "codigo": codigo, "clave_nueva": clave_nueva})


def iniciar_google():
    return llamar("POST", "/auth/social/google/start", {})


def estado_google(state: str):
    return llamar("GET", f"/auth/social/google/status?state={state}")


def reenviar_verificacion(usuario: str):
    return llamar("POST", "/auth/verify/resend", {"usuario": usuario})
