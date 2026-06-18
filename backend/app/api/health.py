from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.db.session import ServiceStatus, check_sqlite
from app.services.ollama import check_ollama
from app.vector_store.milvus import check_vector_store

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    app: str
    ok: bool
    services: list[ServiceStatus]


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    services = [
        ServiceStatus(name="backend", ok=True, detail="ready"),
        check_sqlite(settings.sqlite_path),
        check_vector_store(settings.vector_data_path),
        await check_ollama(str(settings.ollama_base_url)),
    ]
    return HealthResponse(
        app=settings.app_name,
        ok=all(service.ok for service in services),
        services=services,
    )
