import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.socket_server import HOST, PORT, crear_socket_servidor, servir

# Context manager para el ciclo de vida del servidor de sockets
@asynccontextmanager
async def lifespan(app: FastAPI):
    srv = crear_socket_servidor(HOST, PORT)
    threading.Thread(target=servir, args=(srv,), daemon=True).start()
    print(f"Servidor de sockets escuchando en {HOST}:{PORT}", flush=True)
    try:
        yield
    finally:
        srv.close()


app = FastAPI(title="Battle Arena Challenge", lifespan=lifespan)

# Endpoint de verificación de estado del servidor
@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)