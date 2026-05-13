from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.config import settings
from app.db.base import init_db
from app.services.rocketride_service import rocketride
from app.auth.github_oauth import router as auth_router
from app.api.repos import router as repos_router
from app.api.prs import router as prs_router
from app.api.analyze import router as analyze_router
from app.api.chat import router as chat_router
from app.api.criteria import router as criteria_router
from app.api.review import router as review_router
logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database tables...")
    await init_db()
    logger.info("Database ready.")
    logger.info("Starting Rocketride pipeline...")
    await rocketride.startup()
    yield
    await rocketride.shutdown()


app = FastAPI(
    lifespan=lifespan,
    title="PR Analyzer API",
    description="AI-powered GitHub Pull Request analysis backend",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(repos_router, prefix="/repos", tags=["repos"])
app.include_router(prs_router, prefix="/prs", tags=["prs"])
app.include_router(analyze_router, prefix="/analyze", tags=["analyze"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(criteria_router, prefix="/criteria", tags=["criteria"])
app.include_router(review_router, prefix="/review", tags=["review"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
