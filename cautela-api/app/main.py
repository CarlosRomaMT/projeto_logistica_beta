from fastapi import FastAPI

from app.api import frota

app = FastAPI(title="Sistema de Cautela - Frota (MVP)")
app.include_router(frota.router)


@app.get("/health")
def health():
    return {"status": "ok"}
