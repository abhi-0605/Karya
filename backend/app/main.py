"""KaryaOS FastAPI application entrypoint."""
from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import events, workflows, approvals, human_queue, admin, chat, auth

log = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("KaryaOS backend starting", env=settings.app_env)
    yield
    log.info("KaryaOS backend shutting down")


app = FastAPI(
    title="KaryaOS API",
    description="AI-Native HR Services Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(events.router, prefix="/api/events", tags=["events"])
app.include_router(workflows.router, prefix="/api/workflows", tags=["workflows"])
app.include_router(approvals.router, prefix="/api/approvals", tags=["approvals"])
app.include_router(human_queue.router, prefix="/api/queue", tags=["human-queue"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "karyaos-backend"}
