from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class ServiceStatus(BaseModel):
    name: str
    ok: bool
    detail: str


def create_sqlite_engine(database_path: Path) -> Engine:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{database_path}", future=True)


def check_sqlite(database_path: Path) -> ServiceStatus:
    try:
        engine = create_sqlite_engine(database_path)
        with engine.connect() as connection:
            connection.execute(text("select 1"))
        return ServiceStatus(name="sqlite", ok=True, detail="ready")
    except Exception as exc:
        return ServiceStatus(name="sqlite", ok=False, detail=str(exc))
