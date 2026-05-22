from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api import router
from backend.app.auth import seed_initial_admin
from backend.app.core.config import get_settings
from backend.app.db import Base, SessionLocal, engine
from backend.app import models  # noqa: F401


settings = get_settings()
app = FastAPI(title="Santoor AI Learning Platform", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_initial_admin(db)
    Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "santoor-ai-learning-platform"}


app.include_router(router)

dist_dir = Path("frontend/dist")
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")
