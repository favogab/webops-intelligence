
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging


settings = get_settings()
configure_logging()

logger = logging.getLogger("webops")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("WebOps Intelligence started")
    yield
    logger.info("WebOps Intelligence stopped")


app = FastAPI(
    title=settings.app_name,
    description="Website monitoring and AI-assisted incident response",
    version=settings.app_version,
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "webops-intelligence",
        "environment": settings.environment,
    }