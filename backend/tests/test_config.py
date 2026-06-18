from pathlib import Path

from app.core.config import Settings


def test_settings_uses_default_local_paths() -> None:
    settings = Settings()

    assert settings.app_name == "Dota 2 RAG Assistant"
    assert settings.sqlite_path == Path("data/sqlite/dota2_rag.db")
    assert settings.vector_data_path == Path("data/milvus")
    assert str(settings.ollama_base_url) == "http://localhost:11434"


def test_cors_origins_are_parsed_from_comma_separated_text() -> None:
    settings = Settings(cors_origins="http://localhost:5173,http://127.0.0.1:5173")

    assert settings.cors_origin_list == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
