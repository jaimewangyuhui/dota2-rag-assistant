from pathlib import Path

from app.db.session import ServiceStatus


def check_vector_store(vector_data_path: Path) -> ServiceStatus:
    try:
        vector_data_path.mkdir(parents=True, exist_ok=True)
        return ServiceStatus(
            name="milvus",
            ok=True,
            detail="local vector directory ready",
        )
    except Exception as exc:
        return ServiceStatus(name="milvus", ok=False, detail=str(exc))
