from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import appointments, auth, availability, public, services, staff

settings = get_settings()
settings.validate_runtime()

app = FastAPI(
    title=settings.app_name,
    description="Online appointment booking for salons and other appointment-based businesses.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(public.router, prefix=settings.api_v1_prefix)
app.include_router(services.router, prefix=settings.api_v1_prefix)
app.include_router(staff.router, prefix=settings.api_v1_prefix)
app.include_router(availability.router, prefix=settings.api_v1_prefix)
app.include_router(appointments.router, prefix=settings.api_v1_prefix)
app.include_router(services.public_router, prefix=settings.api_v1_prefix)
app.include_router(staff.public_router, prefix=settings.api_v1_prefix)
app.include_router(availability.public_router, prefix=settings.api_v1_prefix)
app.include_router(appointments.public_router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": settings.app_name, "docs": "/docs", "health": "/health"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
