"""Khởi tạo FastAPI, phục vụ API và trang tĩnh.

Chạy: .venv/Scripts/python -m uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import config, db, scheduler
from .routers import analytics, dashboard, kpis, session, snapshots, uploads


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    if config.scheduler_enabled():
        scheduler.start()
    yield
    scheduler.stop()


app = FastAPI(title="BizBoard prototype", lifespan=lifespan)
app.include_router(session.router)
app.include_router(kpis.router)
app.include_router(uploads.router)
app.include_router(dashboard.router)
app.include_router(snapshots.router)
app.include_router(analytics.router)


@app.get("/", include_in_schema=False)
def index():
    return RedirectResponse("/static/index.html")


app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")
