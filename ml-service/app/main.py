import time
import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request

from app.config import settings
from app.ml.model_manager import ModelManager
from app.routers import feedback, health, model, predict

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    manager = ModelManager(model_path=settings.model_path, device=settings.device)
    await manager.load()
    app.state.model_manager = manager
    logger.info(
        "startup",
        app=settings.app_name,
        env=settings.app_env,
        model_loaded=manager.loaded,
        model_version=manager.metadata.get("version", "none"),
    )
    yield
    logger.info("shutdown", app=settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Microservicio de ML para categorización automática de transacciones",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(health.router)
app.include_router(predict.router)
app.include_router(feedback.router)
app.include_router(model.router)
