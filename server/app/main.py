import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.socket_server import HOST, PORT, crear_socket_servidor, servir
from app.auth_store import AlmacenCuentas
from app.resultados_store import AlmacenResultados
from app.social_store import AlmacenLoginSocial

# Context manager para el ciclo de vida del servidor de sockets
@asynccontextmanager
async def lifespan(app: FastAPI):
    srv = crear_socket_servidor(HOST, PORT)
    threading.Thread(target=servir, args=(srv,), kwargs={"validar_sesion": cuentas.validar_sesion}, daemon=True).start()
    print(f"Servidor de sockets escuchando en {HOST}:{PORT}", flush=True)
    try:
        yield
    finally:
        srv.close()


app = FastAPI(title="Battle Arena Challenge", lifespan=lifespan)
cuentas = AlmacenCuentas()
resultados = AlmacenResultados()
social = AlmacenLoginSocial(cuentas)


class Registro(BaseModel):
    usuario: str = Field(min_length=3, max_length=20)
    correo: str
    clave: str = Field(min_length=8)


class Verificar(BaseModel):
    usuario: str
    codigo: str


class Login(BaseModel):
    identificador: str
    clave: str


class RecuperacionSolicitud(BaseModel):
    correo: str


class RecuperacionRestablecer(BaseModel):
    correo: str
    codigo: str
    clave_nueva: str = Field(min_length=8)


class Resultado(BaseModel):
    match_id: str
    jugadores: dict
    winner: str | None = None
    elapsed: float = 0.0
    overtime: int = 0
    condition: str | None = None
    value: int | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register")
def registrar(datos: Registro):
    try:
        return cuentas.registrar(datos.usuario, datos.correo, datos.clave)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/auth/verify")
def verificar(datos: Verificar):
    try:
        return cuentas.verificar(datos.usuario, datos.codigo)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/auth/login")
def login(datos: Login):
    try:
        return cuentas.login(datos.identificador, datos.clave)
    except ValueError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error


@app.post("/auth/verify/resend")
def reenviar_verificacion(datos: dict):
    try:
        return cuentas.reenviar_verificacion(str(datos.get("usuario", "")))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/auth/recovery/request")
def solicitar_recuperacion(datos: RecuperacionSolicitud):
    return cuentas.solicitar_recuperacion(datos.correo)


@app.post("/auth/recovery/reset")
def restablecer(datos: RecuperacionRestablecer):
    try:
        return cuentas.recuperar(datos.correo, datos.codigo, datos.clave_nueva)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/auth/usuarios")
def listar_usuarios():
    return {"usuarios": cuentas.listar()}


@app.post("/auth/social/google/start")
def iniciar_google(datos: dict):
    redirect_uri = datos.get("redirect_uri", "http://127.0.0.1:8000/auth/social/google/callback")
    flujo = social.iniciar_google(redirect_uri)
    import os
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    if not client_id:
        raise HTTPException(status_code=503, detail="Google OAuth no está configurado.")
    from urllib.parse import urlencode
    params = urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": flujo["state"],
        "access_type": "online",
        "prompt": "select_account",
    })
    return {
        "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?" + params,
        "state": flujo["state"],
    }


@app.get("/auth/social/google/callback")
def google_callback(code: str, state: str):
    import json
    import os
    import urllib.parse
    import urllib.request
    import urllib.error

    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    redirect_uri = os.environ.get(
        "GOOGLE_REDIRECT_URI",
        "http://127.0.0.1:8000/auth/social/google/callback",
    )
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth no está configurado.")

    try:
        body = urllib.parse.urlencode({
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }).encode("utf-8")
        with urllib.request.urlopen(
            urllib.request.Request("https://oauth2.googleapis.com/token", data=body, method="POST"),
            timeout=10,
        ) as respuesta:
            tokens = json.loads(respuesta.read().decode("utf-8"))

        access_token = tokens["access_token"]
        peticion = urllib.request.Request("https://openidconnect.googleapis.com/v1/userinfo")
        peticion.add_header("Authorization", "Bearer " + access_token)
        with urllib.request.urlopen(peticion, timeout=10) as respuesta:
            perfil = json.loads(respuesta.read().decode("utf-8"))

        login = social.completar_google(
            state,
            google_subject=str(perfil["sub"]),
            correo=str(perfil.get("email", "")),
            nombre=perfil.get("name"),
        )
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError) as error:
        raise HTTPException(status_code=400, detail=f"No se pudo completar Google login: {error}") from error

    return login


@app.get("/auth/social/google/status")
def google_estado(state: str):
    return social.estado_google(state)


@app.post("/auth/validate")
def validar_sesion(token: dict):
    usuario = cuentas.validar_sesion(token.get("token"))
    if usuario is None:
        raise HTTPException(status_code=401, detail="Sesión inválida.")
    return {"usuario": usuario}


@app.post("/resultados")
def guardar_resultado(datos: Resultado):
    try:
        return resultados.guardar_resultado(
            datos.match_id,
            datos.jugadores,
            datos.winner,
            datos.elapsed,
            datos.overtime,
            datos.condition,
            datos.value,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/resultados")
def listar_resultados():
    return {"partidas": resultados.listar()}


@app.get("/resultados/{match_id}")
def obtener_resultado(match_id: str):
    resultado = resultados.obtener(match_id)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Resultado no encontrado.")
    return resultado


@app.get("/ranking")
def ranking():
    ranking_ordenado = resultados.ranking()
    return {"ranking": ranking_ordenado, "total": len(ranking_ordenado)}


@app.get("/usuarios/{usuario}/historial")
def historial_usuario(usuario: str):
    usuario = usuario.strip().lower()
    return {"usuario": usuario, "historial": resultados.historial(usuario)}


@app.get("/usuarios/{usuario}/perfil")
def perfil_usuario(usuario: str):
    usuario = usuario.strip().lower()
    ranking_ordenado = resultados.ranking()
    posicion = next((fila["posicion"] for fila in ranking_ordenado if fila["usuario"] == usuario), None)
    historial = resultados.historial(usuario)
    victorias = sum(1 for partida in historial if partida["resultado"] == "victoria")
    puntaje_total = sum(partida["score"] for partida in historial)
    tiempo_total = sum(float(partida["elapsed"]) for partida in historial)
    return {
        "usuario": usuario,
        "posicion": posicion,
        "estadisticas": {
            "partidas_jugadas": len(historial),
            "victorias": victorias,
            "derrotas": len(historial) - victorias,
            "puntaje_total": puntaje_total,
            "mejor_puntaje": max((partida["score"] for partida in historial), default=0),
            "tiempo_total_seg": int(tiempo_total),
        },
        "historial": historial,
    }



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)