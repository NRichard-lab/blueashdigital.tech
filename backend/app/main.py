import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api import admin, applications, auth, profile
from app.core.config import settings

logger = structlog.get_logger()

app = FastAPI(title=settings.app_name, docs_url=None if settings.is_production else "/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, https_only=settings.is_production, same_site="lax")

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(applications.router)
app.include_router(admin.router)


@app.on_event("startup")
async def startup() -> None:
    logger.info("portal_startup", app_env=settings.app_env)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "blueash-portal-backend"}

