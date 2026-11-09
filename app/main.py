"""Khởi tạo FastAPI, phục vụ API và trang tĩnh.

Chạy: .venv/Scripts/python -m uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import config, db, scheduler
from .routers import (admin, alerts, analytics, dashboard, dev, groups, kpis, notes, reports, session, shares,
                      snapshots, uploads)


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
for r in (reports, shares, alerts, dev, groups, notes, admin):
    app.include_router(r.router)


@app.middleware("http")
async def no_store(request: Request, call_next):
    """Dữ liệu API phụ thuộc người đang đăng nhập: không cho trình duyệt dùng lại bản cũ."""
    response = await call_next(request)
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/", include_in_schema=False)
def index():
    return RedirectResponse("/static/index.html")


app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")
