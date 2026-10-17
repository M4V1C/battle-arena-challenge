from fastapi import FastAPI

app = FastAPI(title="Battle Arena Challenge")


@app.get("/health")
def health():
    return {"status": "ok"}