import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, application_auth, applications, auth, profile, settings as admin_settings
from app.core.config import settings
from app.core.cookies import clear_legacy_parent_auth_cookies
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


@app.middleware("http")
async def expire_legacy_parent_auth_cookies(request, call_next):
    response = await call_next(request)
    clear_legacy_parent_auth_cookies(response)
    return response

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(applications.router)
app.include_router(application_auth.router)
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

