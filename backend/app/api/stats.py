from fastapi import APIRouter, HTTPException, Request

from app.data_sources.opendota import OpenDotaClient
from app.db.repositories import HeroStatsRepository
from app.db.session import create_sqlite_engine
from app.jobs.refresh_stats import RefreshStatsResult, refresh_hero_stats

router = APIRouter(prefix="/api", tags=["stats"])


@router.post("/refresh/stats", response_model=RefreshStatsResult)
def refresh_stats(request: Request) -> RefreshStatsResult:
    settings = request.app.state.settings
    repository = HeroStatsRepository(create_sqlite_engine(settings.sqlite_path))
    client = getattr(request.app.state, "opendota_client", None)
    if client is None:
        client = OpenDotaClient(base_url=settings.opendota_base_url)
    refreshed_at = getattr(request.app.state, "stats_refreshed_at", None)
    try:
        return refresh_hero_stats(
            repository=repository,
            client=client,
            refreshed_at=refreshed_at,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
