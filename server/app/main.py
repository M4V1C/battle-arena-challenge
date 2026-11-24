import logging
import os
import threading
from contextlib import asynccontextmanager

from pathlib import Path
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.socket_server import HOST, PORT, crear_socket_servidor, guardar_resultado_final, servir
from app.auth_store import AlmacenCuentas, CorreoNoVerificado
from app.game_state import EstadoJuego
from app.resultados_store import AlmacenResultados
from app.social_store import AlmacenLoginSocial

bitacora = logging.getLogger("battle_arena.api")

# Context manager para el ciclo de vida del servidor de sockets
@asynccontextmanager
async def lifespan(app: FastAPI):
    srv = crear_socket_servidor(HOST, PORT)
    threading.Thread(
        target=servir,
        args=(srv,),
        kwargs={
            "validar_sesion": cuentas.validar_sesion,
            "resultados": resultados,
            "estado_juego": partida,
        },
        daemon=True,
    ).start()
    print(f"Servidor de sockets escuchando en {HOST}:{PORT}", flush=True)
    try:
        yield
    finally:
        srv.close()


app = FastAPI(title="Battle Arena Challenge", lifespan=lifespan)
WEB_DIR = Path(__file__).resolve().parents[1] / "web"
app.mount("/webapp", StaticFiles(directory=WEB_DIR, html=True), name="webapp")

cuentas = AlmacenCuentas()
resultados = AlmacenResultados()
social = AlmacenLoginSocial(cuentas)
# Partida compartida con el servidor TCP; guarda en el almacén vigente al cerrar.
partida = EstadoJuego(guardar_resultado=lambda resultado: guardar_resultado_final(resultados, resultado))


def usuario_autenticado(authorization: str | None = Header(default=None)) -> str:
    """Devuelve el usuario dueño del token `Authorization: Bearer <token>` o responde 401."""
    esquema, _, token = (authorization or "").partition(" ")
    if esquema.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=401,
            detail="Inicia sesión para consultar estos datos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    usuario = cuentas.validar_sesion(token.strip())
    if usuario is None:
        raise HTTPException(
            status_code=401,
            detail="La sesión no es válida o expiró. Inicia sesión de nuevo.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario


def exigir_mismo_usuario(usuario: str, autenticado: str) -> str:
    """Responde 403 si la ruta pide datos de otra cuenta; devuelve el nombre canónico."""
    if usuario.strip().lower() != autenticado.lower():
        raise HTTPException(status_code=403, detail="Solo puedes consultar tus propios datos.")
    return autenticado


def participa(partida: dict, usuario: str) -> bool:
    return any(
        str(datos.get("usuario") or "").lower() == usuario.lower()
        for datos in partida.get("jugadores", {}).values()
    )


CODIGOS_DE_UN_SOLO_USO = ("codigo_verificacion", "codigo_recuperacion")


def sin_codigos(respuesta: dict) -> dict:
    """Quita los códigos de la respuesta salvo en modo demo (EXPOSE_CODES=1)."""
    if os.environ.get("EXPOSE_CODES", "0").strip() == "1":
        return respuesta
    return {clave: valor for clave, valor in respuesta.items() if clave not in CODIGOS_DE_UN_SOLO_USO}


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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register")
def registrar(datos: Registro):
    try:
        return sin_codigos(cuentas.registrar(datos.usuario, datos.correo, datos.clave))
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
        return sin_codigos(cuentas.reenviar_verificacion(str(datos.get("usuario", ""))))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/auth/recovery/request")
def solicitar_recuperacion(datos: RecuperacionSolicitud):
    return sin_codigos(cuentas.solicitar_recuperacion(datos.correo))


@app.post("/auth/recovery/reset")
def restablecer(datos: RecuperacionRestablecer):
    try:
        return cuentas.recuperar(datos.correo, datos.codigo, datos.clave_nueva)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/auth/usuarios")
def listar_usuarios():
    # Lista pública: nunca incluye correos.
    return {"usuarios": [
        {"usuario": cuenta["usuario"], "correo_verificado": cuenta["correo_verificado"]}
        for cuenta in cuentas.listar()
    ]}


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


MENSAJE_GOOGLE_CANCELADO = "Se canceló el inicio de sesión con Google."
MENSAJE_GOOGLE_FALLO = "No se pudo completar el inicio de sesión con Google. Inténtalo de nuevo."


def volver_a_la_web(**parametros: str) -> RedirectResponse:
    return RedirectResponse(url="/webapp/?" + urlencode(parametros), status_code=303)


@app.get("/auth/social/google/callback")
def google_callback(state: str = "", code: str = "", error: str = ""):
    import json
    import os
    import urllib.parse
    import urllib.request

    if not code:
        # Google vuelve sin código si el usuario cancela (error=access_denied) o si falla.
        cancelado = error in ("", "access_denied")
        social.fallar_google(state, MENSAJE_GOOGLE_CANCELADO if cancelado else MENSAJE_GOOGLE_FALLO)
        return volver_a_la_web(google_error="cancelado" if cancelado else "fallo")

    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    redirect_uri = os.environ.get(
        "GOOGLE_REDIRECT_URI",
        "http://127.0.0.1:8000/auth/social/google/callback",
    )
    if not client_id or not client_secret:
        social.fallar_google(state, MENSAJE_GOOGLE_FALLO)
        return volver_a_la_web(google_error="fallo")

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

        social.completar_google(
            state,
            google_subject=str(perfil["sub"]),
            correo=str(perfil.get("email", "")),
            nombre=perfil.get("name"),
            correo_verificado=perfil.get("email_verified") in (True, "true"),
        )
    except CorreoNoVerificado:
        return volver_a_la_web(google_error="correo_no_verificado")
    except (OSError, KeyError, TypeError, ValueError) as fallo:
        # El detalle queda solo en el registro del servidor; al usuario se le da un mensaje genérico.
        bitacora.warning("Fallo el inicio de sesión con Google: %s: %s", type(fallo).__name__, fallo)
        social.fallar_google(state, MENSAJE_GOOGLE_FALLO)
        return volver_a_la_web(google_error="fallo")

    return volver_a_la_web(google_state=state)


@app.get("/auth/social/google/status")
def google_estado(state: str):
    return social.estado_google(state)


@app.post("/auth/validate")
def validar_sesion(token: dict):
    usuario = cuentas.validar_sesion(token.get("token"))
    if usuario is None:
        raise HTTPException(status_code=401, detail="Sesión inválida.")
    return {"usuario": usuario}


@app.get("/resultados")
def listar_resultados(autenticado: str = Depends(usuario_autenticado)):
    # Los resultados los guarda el servidor de juego en proceso; aquí solo se consultan.
    return {"partidas": [p for p in resultados.listar() if participa(p, autenticado)]}


@app.get("/resultados/{match_id}")
def obtener_resultado(match_id: str, autenticado: str = Depends(usuario_autenticado)):
    resultado = resultados.obtener(match_id)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Resultado no encontrado.")
    if not participa(resultado, autenticado):
        raise HTTPException(status_code=403, detail="Solo puedes consultar tus propias partidas.")
    return resultado


@app.get("/ranking")
def ranking():
    ranking_ordenado = resultados.ranking()
    return {"ranking": ranking_ordenado, "total": len(ranking_ordenado)}


def estado_publico(estado: dict) -> dict:
    """Resumen de la partida sin posiciones, tokens ni correos."""
    datos_partida = estado["match"]
    limite = datos_partida["time_limit"]
    return {
        "match_id": datos_partida["match_id"],
        "iniciada": datos_partida["started"],
        "finalizada": datos_partida["finished"],
        "en_curso": datos_partida["started"] and not datos_partida["finished"],
        "escenario": estado["scenario"]["name"],
        "condicion": datos_partida["condition"],
        "objetivo": datos_partida["value"],
        "tiempo": {
            "transcurrido": datos_partida["elapsed"],
            "limite": limite,
            "restante": max(0.0, limite - datos_partida["elapsed"]) if limite is not None else None,
            "prorrogas": datos_partida["overtime"],
        },
        "ganador": datos_partida["winner"],
        "reactor": {"estado": estado["reactor"]["status"], "operador": estado["reactor"]["operator"]},
        "jugadores": {
            puesto: {
                "usuario": jugador["username"],
                "puntaje": jugador["score"],
                "conectado": jugador["connected"],
                "estado": jugador["status"],
            }
            for puesto, jugador in estado["players"].items()
        },
        "eventos_activos": [
            {"tipo": evento["type"], "restante": evento["remaining"]}
            for evento in estado["events"] if evento["status"] == "active"
        ],
    }


@app.get("/partida/estado")
def estado_partida():
    return estado_publico(partida.estado())


@app.get("/usuarios/{usuario}/historial")
def historial_usuario(usuario: str, autenticado: str = Depends(usuario_autenticado)):
    usuario = exigir_mismo_usuario(usuario, autenticado)
    return {"usuario": usuario, "historial": resultados.historial(usuario)}


@app.get("/usuarios/{usuario}/perfil")
def perfil_usuario(usuario: str, autenticado: str = Depends(usuario_autenticado)):
    usuario = exigir_mismo_usuario(usuario, autenticado)
    try:
        cuenta = cuentas.perfil(usuario)
    except ValueError:
        cuenta = {}
    ranking_ordenado = resultados.ranking()
    posicion = next((fila["posicion"] for fila in ranking_ordenado if fila["usuario"] == usuario), None)
    historial = resultados.historial(usuario)
    victorias = sum(1 for partida in historial if partida["resultado"] == "victoria")
    puntaje_total = sum(partida["score"] for partida in historial)
    tiempo_total = sum(float(partida["elapsed"]) for partida in historial)
    partidas_jugadas = len(historial)
    return {
        "usuario": usuario,
        "correo": cuenta.get("correo", ""),
        "correo_verificado": cuenta.get("correo_verificado", False),
        "avatar": cuenta.get("avatar", "default"),
        "fecha_registro": cuenta.get("fecha_registro", "Desconocida"),
        "logros": cuenta.get("logros", []),
        "posicion": posicion,
        "estadisticas": {
            "partidas_jugadas": partidas_jugadas,
            "victorias": victorias,
            "derrotas": partidas_jugadas - victorias,
            "puntaje_total": puntaje_total,
            "mejor_puntaje": max((partida["score"] for partida in historial), default=0),
            "tiempo_total_seg": int(tiempo_total),
            "porcentaje_victorias": victorias * 100 / partidas_jugadas if partidas_jugadas else 0,
            "puntaje_promedio": puntaje_total / partidas_jugadas if partidas_jugadas else 0,
            "duracion_promedio_seg": tiempo_total / partidas_jugadas if partidas_jugadas else 0,
        },
        "historial": historial,
    }



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
