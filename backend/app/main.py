import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api import admin, applications, auth, profile, settings as admin_settings
from app.core.config import settings
from app.database.session import SessionLocal
from app.services.permission_service import ensure_permission_catalog

logger = structlog.get_logger()

app = FastAPI(title=settings.app_name, docs_url=None if settings.is_production else "/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, https_only=settings.is_production, same_site="lax")

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(applications.router)
app.include_router(admin.router)
app.include_router(admin_settings.router)


@app.on_event("startup")
async def startup() -> None:
    with SessionLocal() as db:
        ensure_permission_catalog(db)
    logger.info("portal_startup", app_env=settings.app_env)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "blueash-portal-backend"}

