import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.socket_server import HOST, PORT, crear_socket_servidor, servir
from app.auth_store import AlmacenCuentas
from app.resultados_store import AlmacenResultados

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
    partidas = resultados.listar()
    totales: dict[str, dict[str, int]] = {}
    for partida in partidas:
        for puesto, datos in partida["jugadores"].items():
            usuario = datos.get("usuario")
            if not usuario:
                continue
            fila = totales.setdefault(usuario, {"puntaje_total": 0, "victorias": 0})
            fila["puntaje_total"] += int(datos.get("score", 0))
            if partida.get("winner") == puesto:
                fila["victorias"] += 1
    ranking_ordenado = sorted(
        ({"usuario": usuario, **valores} for usuario, valores in totales.items()),
        key=lambda fila: (-fila["puntaje_total"], -fila["victorias"], fila["usuario"].lower()),
    )
    return {"ranking": ranking_ordenado}


@app.get("/usuarios/{usuario}/perfil")
def perfil_usuario(usuario: str):
    try:
        return cuentas.perfil(usuario)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/usuarios/{usuario}/historial")
def historial_usuario(usuario: str):
    partidas = []
    for partida in resultados.listar():
        for puesto, datos in partida["jugadores"].items():
            if datos.get("usuario") == usuario:
                partidas.append({
                    "match_id": partida["match_id"],
                    "puesto": puesto,
                    "score": datos.get("score", 0),
                    "winner": partida.get("winner"),
                    "elapsed": partida.get("elapsed", 0),
                    "overtime": partida.get("overtime", 0),
                })
    return {"usuario": usuario, "historial": partidas}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)