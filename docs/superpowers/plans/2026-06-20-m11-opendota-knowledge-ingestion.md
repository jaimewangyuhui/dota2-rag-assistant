# M11 OpenDota Knowledge Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an OpenDota hero and item knowledge loader that crawls OpenDota constants, converts them into RAG documents, and stores them through the existing document ingestion/vector pipeline.

**Architecture:** Keep source fetching/parsing in a new `opendota_knowledge.py` module and keep vector writes inside the existing ingestion job. Extend ingestion to accept multiple optional document loaders so seed, official Dota, and OpenDota knowledge documents can be composed without coupling sources to storage.

**Tech Stack:** Python 3.12-compatible FastAPI backend, Pydantic models, `httpx`, existing deterministic embedder, existing local JSON vector store, pytest.

---

## File Structure

- Create `backend/app/data_sources/opendota_knowledge.py`: OpenDota constants client, typed records, parsers, text document builders, and combined loader.
- Create `backend/tests/fixtures/opendota_heroes_constants_sample.json`: fixture with Axe and Crystal Maiden-style hero constants.
- Create `backend/tests/fixtures/opendota_items_constants_sample.json`: fixture with Blink Dagger and Black King Bar-style item constants.
- Create `backend/tests/test_opendota_knowledge_source.py`: unit tests for parsing and document conversion.
- Modify `backend/app/jobs/ingest_documents.py`: support multiple optional document loaders while preserving the current official loader compatibility.
- Modify `backend/tests/test_ingest_job.py`: test injected OpenDota knowledge documents are chunked, embedded, and retrievable.
- Modify `backend/app/core/config.py`: add `opendota_knowledge_sources_enabled`.
- Modify `backend/app/api/ingest.py`: include OpenDota knowledge loader when enabled and allow test injection through app state.
- Modify `backend/tests/test_ingest_api.py`: test API ingestion includes injected OpenDota knowledge documents without network.

## Backend Test Command

Use this backend test command from the repository root:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -v -p no:cacheprovider --basetemp .tmp\pytest-m11"
```

Expected final result: all backend tests pass.

---

### Task 1: OpenDota Knowledge Source

**Files:**
- Create: `backend/app/data_sources/opendota_knowledge.py`
- Create: `backend/tests/fixtures/opendota_heroes_constants_sample.json`
- Create: `backend/tests/fixtures/opendota_items_constants_sample.json`
- Create: `backend/tests/test_opendota_knowledge_source.py`

- [ ] **Step 1: Add hero and item fixture JSON**

Create `backend/tests/fixtures/opendota_heroes_constants_sample.json`:

```json
{
  "npc_dota_hero_axe": {
    "id": 2,
    "name": "npc_dota_hero_axe",
    "localized_name": "Axe",
    "primary_attr": "str",
    "attack_type": "Melee",
    "roles": ["Initiator", "Durable", "Disabler", "Carry"],
    "legs": 2
  },
  "npc_dota_hero_crystal_maiden": {
    "id": 5,
    "name": "npc_dota_hero_crystal_maiden",
    "localized_name": "Crystal Maiden",
    "primary_attr": "int",
    "attack_type": "Ranged",
    "roles": ["Support", "Disabler", "Nuker"],
    "legs": 2
  }
}
```

Create `backend/tests/fixtures/opendota_items_constants_sample.json`:

```json
{
  "blink": {
    "id": 1,
    "dname": "Blink Dagger",
    "qual": "component",
    "cost": 2250,
    "notes": "Teleport to a target point up to 1200 units away.",
    "attrib": [],
    "components": null,
    "hint": ["Great for initiation and mobility."]
  },
  "black_king_bar": {
    "id": 116,
    "dname": "Black King Bar",
    "qual": "epic",
    "cost": 4050,
    "notes": "Provides spell immunity-style protection through Avatar in many Dota versions.",
    "attrib": [
      {"key": "bonus_strength", "display": "+ {value} Strength", "value": "10"},
      {"key": "bonus_damage", "display": "+ {value} Damage", "value": "24"}
    ],
    "components": ["ogre_axe", "mithril_hammer", "recipe_black_king_bar"],
    "hint": ["Useful against heavy magical control."]
  }
}
```

- [ ] **Step 2: Write failing parser and document tests**

Create `backend/tests/test_opendota_knowledge_source.py`:

```python
from pathlib import Path

import pytest

from app.data_sources.opendota_knowledge import (
    OpenDotaKnowledgeClient,
    OpenDotaKnowledgeParseError,
    hero_records_to_documents,
    item_records_to_documents,
    load_opendota_knowledge_documents,
    parse_hero_constants,
    parse_item_constants,
)


FIXTURES = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeOpenDotaKnowledgeClient:
    base_url = "https://api.opendota.com/api"

    def fetch_heroes(self) -> str:
        return read_fixture("opendota_heroes_constants_sample.json")

    def fetch_items(self) -> str:
        return read_fixture("opendota_items_constants_sample.json")


def test_parse_hero_constants_reads_dictionary_payload() -> None:
    records = parse_hero_constants(
        read_fixture("opendota_heroes_constants_sample.json"),
        refreshed_at="2026-06-20",
        base_url="https://api.opendota.com/api",
    )

    assert len(records) == 2
    axe = records[0]
    assert axe.hero_id == 2
    assert axe.key == "npc_dota_hero_axe"
    assert axe.localized_name == "Axe"
    assert axe.primary_attr == "str"
    assert axe.attack_type == "Melee"
    assert axe.roles == ["Initiator", "Durable", "Disabler", "Carry"]
    assert axe.aliases == ["axe", "npc dota hero axe"]
    assert axe.source_url == "https://api.opendota.com/api/constants/heroes/2"


def test_parse_item_constants_reads_dictionary_payload() -> None:
    records = parse_item_constants(
        read_fixture("opendota_items_constants_sample.json"),
        refreshed_at="2026-06-20",
        base_url="https://api.opendota.com/api",
    )

    assert len(records) == 2
    blink = records[0]
    assert blink.key == "blink"
    assert blink.item_id == 1
    assert blink.display_name == "Blink Dagger"
    assert blink.cost == 2250
    assert blink.components == []
    assert "Teleport to a target point" in blink.notes
    assert blink.source_url == "https://api.opendota.com/api/constants/items/blink"


def test_records_to_documents_create_searchable_metadata() -> None:
    heroes = parse_hero_constants(
        read_fixture("opendota_heroes_constants_sample.json"),
        refreshed_at="2026-06-20",
        base_url="https://api.opendota.com/api",
    )
    items = parse_item_constants(
        read_fixture("opendota_items_constants_sample.json"),
        refreshed_at="2026-06-20",
        base_url="https://api.opendota.com/api",
    )

    hero_doc = hero_records_to_documents(heroes)[0]
    item_doc = item_records_to_documents(items)[0]

    assert hero_doc.metadata.source_name == "OpenDota Hero: Axe"
    assert hero_doc.metadata.entity_type == "hero"
    assert hero_doc.metadata.entity_name == "Axe"
    assert "Roles: Initiator, Durable, Disabler, Carry." in hero_doc.text
    assert "Aliases: axe, npc dota hero axe." in hero_doc.text

    assert item_doc.metadata.source_name == "OpenDota Item: Blink Dagger"
    assert item_doc.metadata.entity_type == "item"
    assert item_doc.metadata.entity_name == "Blink Dagger"
    assert "Cost: 2250." in item_doc.text
    assert "mobility" in item_doc.text.lower()


def test_load_opendota_knowledge_documents_combines_heroes_and_items() -> None:
    documents = load_opendota_knowledge_documents(
        client=FakeOpenDotaKnowledgeClient(),
        refreshed_at="2026-06-20",
    )

    assert len(documents) == 4
    assert {document.metadata.entity_type for document in documents} == {"hero", "item"}
    assert "OpenDota Hero: Axe" in {document.metadata.source_name for document in documents}
    assert "OpenDota Item: Black King Bar" in {
        document.metadata.source_name for document in documents
    }


def test_parse_hero_constants_rejects_empty_payload() -> None:
    with pytest.raises(OpenDotaKnowledgeParseError, match="No OpenDota hero constants"):
        parse_hero_constants("{}", refreshed_at="2026-06-20", base_url="https://api.opendota.com/api")


def test_parse_item_constants_rejects_empty_payload() -> None:
    with pytest.raises(OpenDotaKnowledgeParseError, match="No OpenDota item constants"):
        parse_item_constants("{}", refreshed_at="2026-06-20", base_url="https://api.opendota.com/api")


def test_client_fetches_hero_and_item_constants(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class FakeResponse:
        text = "{}"

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, timeout: float) -> FakeResponse:
        calls.append(f"{url}|{timeout}")
        return FakeResponse()

    monkeypatch.setattr("app.data_sources.opendota_knowledge.httpx.get", fake_get)

    client = OpenDotaKnowledgeClient(base_url="https://example.test/api", timeout=12.0)

    assert client.fetch_heroes() == "{}"
    assert client.fetch_items() == "{}"
    assert calls == [
        "https://example.test/api/constants/heroes|12.0",
        "https://example.test/api/constants/items|12.0",
    ]
```

- [ ] **Step 3: Run focused test to verify failure**

Run:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest backend/tests/test_opendota_knowledge_source.py -v -p no:cacheprovider --basetemp backend\.tmp\pytest-m11-source"
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.data_sources.opendota_knowledge'`.

- [ ] **Step 4: Implement OpenDota knowledge source**

Create `backend/app/data_sources/opendota_knowledge.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from app.rag.schemas import DocumentInput, SourceMetadata


class OpenDotaKnowledgeParseError(ValueError):
    pass


@dataclass(frozen=True)
class OpenDotaHeroKnowledgeRecord:
    hero_id: int
    key: str
    name: str
    localized_name: str
    primary_attr: str
    attack_type: str
    roles: list[str]
    legs: int | None
    aliases: list[str]
    source_url: str
    refreshed_at: str


@dataclass(frozen=True)
class OpenDotaItemKnowledgeRecord:
    item_id: int | None
    key: str
    display_name: str
    quality: str
    cost: int | None
    notes: str
    attributes: list[str]
    components: list[str]
    hints: list[str]
    source_url: str
    refreshed_at: str


class OpenDotaKnowledgeClient:
    def __init__(self, base_url: str = "https://api.opendota.com/api", timeout: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def fetch_heroes(self) -> str:
        response = httpx.get(f"{self.base_url}/constants/heroes", timeout=self.timeout)
        response.raise_for_status()
        return response.text

    def fetch_items(self) -> str:
        response = httpx.get(f"{self.base_url}/constants/items", timeout=self.timeout)
        response.raise_for_status()
        return response.text


def _today() -> str:
    return datetime.now(tz=UTC).date().isoformat()


def _payload_object(raw: str, source_name: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict) or not payload:
        raise OpenDotaKnowledgeParseError(f"No OpenDota {source_name} constants found")
    return payload


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _hero_aliases(key: str, localized_name: str) -> list[str]:
    aliases = [
        localized_name.lower(),
        key.replace("_", " ").replace("npc dota hero ", "").strip(),
        key.replace("_", " "),
    ]
    deduped: list[str] = []
    for alias in aliases:
        if alias and alias not in deduped:
            deduped.append(alias)
    return deduped


def _item_display_name(key: str, row: dict[str, Any]) -> str:
    return _text(row.get("dname")) or key.replace("_", " ").title()


def _attribute_lines(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    lines: list[str] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        display = _text(entry.get("display"))
        raw_value = _text(entry.get("value"))
        key = _text(entry.get("key"))
        if display and raw_value:
            lines.append(display.replace("{value}", raw_value))
        elif display:
            lines.append(display)
        elif key and raw_value:
            lines.append(f"{key}: {raw_value}")
        elif key:
            lines.append(key)
    return lines


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_text(item) for item in value if _text(item)]


def parse_hero_constants(
    raw: str,
    refreshed_at: str,
    base_url: str,
) -> list[OpenDotaHeroKnowledgeRecord]:
    payload = _payload_object(raw, "hero")
    records: list[OpenDotaHeroKnowledgeRecord] = []
    for key, row in payload.items():
        if not isinstance(row, dict):
            raise OpenDotaKnowledgeParseError("OpenDota hero constant row must be an object")
        hero_id = int(row["id"])
        localized_name = _text(row.get("localized_name")) or _text(row.get("name")) or key
        name = _text(row.get("name")) or key
        records.append(
            OpenDotaHeroKnowledgeRecord(
                hero_id=hero_id,
                key=key,
                name=name,
                localized_name=localized_name,
                primary_attr=_text(row.get("primary_attr")),
                attack_type=_text(row.get("attack_type")),
                roles=_string_list(row.get("roles")),
                legs=_optional_int(row.get("legs")),
                aliases=_hero_aliases(key, localized_name),
                source_url=f"{base_url.rstrip('/')}/constants/heroes/{hero_id}",
                refreshed_at=refreshed_at,
            )
        )
    if not records:
        raise OpenDotaKnowledgeParseError("No OpenDota hero constants found")
    return records


def parse_item_constants(
    raw: str,
    refreshed_at: str,
    base_url: str,
) -> list[OpenDotaItemKnowledgeRecord]:
    payload = _payload_object(raw, "item")
    records: list[OpenDotaItemKnowledgeRecord] = []
    for key, row in payload.items():
        if not isinstance(row, dict):
            raise OpenDotaKnowledgeParseError("OpenDota item constant row must be an object")
        records.append(
            OpenDotaItemKnowledgeRecord(
                item_id=_optional_int(row.get("id")),
                key=key,
                display_name=_item_display_name(key, row),
                quality=_text(row.get("qual")),
                cost=_optional_int(row.get("cost")),
                notes=_text(row.get("notes")),
                attributes=_attribute_lines(row.get("attrib")),
                components=_string_list(row.get("components")),
                hints=_string_list(row.get("hint")),
                source_url=f"{base_url.rstrip('/')}/constants/items/{key}",
                refreshed_at=refreshed_at,
            )
        )
    if not records:
        raise OpenDotaKnowledgeParseError("No OpenDota item constants found")
    return records


def hero_records_to_documents(records: list[OpenDotaHeroKnowledgeRecord]) -> list[DocumentInput]:
    documents: list[DocumentInput] = []
    for record in records:
        roles = ", ".join(record.roles) if record.roles else "Unknown"
        aliases = ", ".join(record.aliases) if record.aliases else "None"
        legs = str(record.legs) if record.legs is not None else "Unknown"
        text = (
            f"{record.localized_name} is an OpenDota hero constant. "
            f"Internal name: {record.name}. "
            f"Primary attribute: {record.primary_attr or 'Unknown'}. "
            f"Attack type: {record.attack_type or 'Unknown'}. "
            f"Roles: {roles}. "
            f"Legs: {legs}. "
            f"Aliases: {aliases}."
        )
        documents.append(
            DocumentInput(
                text=text,
                metadata=SourceMetadata(
                    source_url=record.source_url,
                    source_name=f"OpenDota Hero: {record.localized_name}",
                    patch_version=None,
                    entity_type="hero",
                    entity_name=record.localized_name,
                    updated_at=record.refreshed_at,
                ),
            )
        )
    return documents


def item_records_to_documents(records: list[OpenDotaItemKnowledgeRecord]) -> list[DocumentInput]:
    documents: list[DocumentInput] = []
    for record in records:
        cost = str(record.cost) if record.cost is not None else "Unknown"
        components = ", ".join(record.components) if record.components else "None"
        attributes = "; ".join(record.attributes) if record.attributes else "None"
        hints = " ".join(record.hints) if record.hints else ""
        text = (
            f"{record.display_name} is an OpenDota item constant. "
            f"Internal key: {record.key}. "
            f"Quality: {record.quality or 'Unknown'}. "
            f"Cost: {cost}. "
            f"Components: {components}. "
            f"Attributes: {attributes}. "
            f"Notes: {record.notes or 'No OpenDota notes available.'} "
            f"{hints}"
        ).strip()
        documents.append(
            DocumentInput(
                text=text,
                metadata=SourceMetadata(
                    source_url=record.source_url,
                    source_name=f"OpenDota Item: {record.display_name}",
                    patch_version=None,
                    entity_type="item",
                    entity_name=record.display_name,
                    updated_at=record.refreshed_at,
                ),
            )
        )
    return documents


def load_opendota_knowledge_documents(
    client: OpenDotaKnowledgeClient | None = None,
    refreshed_at: str | None = None,
) -> list[DocumentInput]:
    active_client = client or OpenDotaKnowledgeClient()
    active_refreshed_at = refreshed_at or _today()
    hero_records = parse_hero_constants(
        active_client.fetch_heroes(),
        refreshed_at=active_refreshed_at,
        base_url=active_client.base_url,
    )
    item_records = parse_item_constants(
        active_client.fetch_items(),
        refreshed_at=active_refreshed_at,
        base_url=active_client.base_url,
    )
    return hero_records_to_documents(hero_records) + item_records_to_documents(item_records)
```

- [ ] **Step 5: Run focused source tests**

Run:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest backend/tests/test_opendota_knowledge_source.py -v -p no:cacheprovider --basetemp backend\.tmp\pytest-m11-source"
```

Expected: PASS.

- [ ] **Step 6: Commit source module**

```powershell
git add backend/app/data_sources/opendota_knowledge.py backend/tests/fixtures/opendota_heroes_constants_sample.json backend/tests/fixtures/opendota_items_constants_sample.json backend/tests/test_opendota_knowledge_source.py
git commit -m "feat: add opendota knowledge source"
```

---

### Task 2: Ingestion Job Loader Composition

**Files:**
- Modify: `backend/app/jobs/ingest_documents.py`
- Modify: `backend/tests/test_ingest_job.py`

- [ ] **Step 1: Add failing ingestion test for extra OpenDota documents**

Append to `backend/tests/test_ingest_job.py`:

```python
def opendota_test_documents() -> list[DocumentInput]:
    return [
        DocumentInput(
            text=(
                "Axe is an OpenDota hero constant. Primary attribute: str. "
                "Roles: Initiator, Durable, Disabler, Carry."
            ),
            metadata=SourceMetadata(
                source_url="https://api.opendota.com/api/constants/heroes/2",
                source_name="OpenDota Hero: Axe",
                patch_version=None,
                entity_type="hero",
                entity_name="Axe",
                updated_at="2026-06-20",
            ),
        ),
        DocumentInput(
            text=(
                "Blink Dagger is an OpenDota item constant. Cost: 2250. "
                "Notes: Teleport to a target point up to 1200 units away."
            ),
            metadata=SourceMetadata(
                source_url="https://api.opendota.com/api/constants/items/blink",
                source_name="OpenDota Item: Blink Dagger",
                patch_version=None,
                entity_type="item",
                entity_name="Blink Dagger",
                updated_at="2026-06-20",
            ),
        ),
    ]


def test_ingest_seed_documents_can_include_multiple_extra_document_loaders(tmp_path: Path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    embedder = DeterministicEmbedder(dimensions=64)

    result = ingest_seed_documents(
        store=store,
        embedder=embedder,
        document_loaders=[official_test_documents, opendota_test_documents],
    )

    assert result.documents == 7
    assert "Official Dota 2: Axe" in result.sources
    assert "OpenDota Hero: Axe" in result.sources
    assert "OpenDota Item: Blink Dagger" in result.sources

    retriever = Retriever(store=store, embedder=embedder)
    hero_result = retriever.retrieve("Axe roles strength initiator", limit=1)[0]
    item_result = retriever.retrieve("Blink Dagger cost mobility", limit=1)[0]

    assert hero_result.chunk.metadata.source_name == "OpenDota Hero: Axe"
    assert item_result.chunk.metadata.source_name == "OpenDota Item: Blink Dagger"
```

- [ ] **Step 2: Run focused ingestion test to verify failure**

Run:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest backend/tests/test_ingest_job.py::test_ingest_seed_documents_can_include_multiple_extra_document_loaders -v -p no:cacheprovider --basetemp backend\.tmp\pytest-m11-ingest-job"
```

Expected: FAIL with `TypeError: ingest_seed_documents() got an unexpected keyword argument 'document_loaders'`.

- [ ] **Step 3: Update ingestion job to compose loaders**

Modify `backend/app/jobs/ingest_documents.py` to:

```python
from collections.abc import Callable, Sequence

from pydantic import BaseModel

from app.data_sources.seed_documents import load_seed_documents
from app.rag.chunker import chunk_document
from app.rag.embeddings import Embedder
from app.rag.schemas import DocumentInput
from app.vector_store.milvus import LocalVectorStore


class IngestResult(BaseModel):
    documents: int
    chunks: int
    sources: list[str]


DocumentLoader = Callable[[], list[DocumentInput]]
OfficialDocumentsLoader = DocumentLoader


def ingest_seed_documents(
    store: LocalVectorStore,
    embedder: Embedder,
    official_documents_loader: OfficialDocumentsLoader | None = None,
    document_loaders: Sequence[DocumentLoader] | None = None,
) -> IngestResult:
    documents = load_seed_documents()
    active_loaders: list[DocumentLoader] = []
    if official_documents_loader is not None:
        active_loaders.append(official_documents_loader)
    if document_loaders is not None:
        active_loaders.extend(document_loaders)
    for loader in active_loaders:
        documents.extend(loader())

    chunks = [chunk for document in documents for chunk in chunk_document(document)]
    entries = [(chunk, embedder.embed(chunk.text)) for chunk in chunks]
    store.upsert(entries)
    return IngestResult(
        documents=len(documents),
        chunks=len(chunks),
        sources=store.list_sources(),
    )
```

- [ ] **Step 4: Run focused ingestion tests**

Run:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest backend/tests/test_ingest_job.py -v -p no:cacheprovider --basetemp backend\.tmp\pytest-m11-ingest-job"
```

Expected: PASS.

- [ ] **Step 5: Commit ingestion composition**

```powershell
git add backend/app/jobs/ingest_documents.py backend/tests/test_ingest_job.py
git commit -m "feat: compose document ingestion loaders"
```

---

### Task 3: API And Configuration Integration

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/api/ingest.py`
- Modify: `backend/tests/test_ingest_api.py`

- [ ] **Step 1: Add failing API test for injected OpenDota loader**

Append to `backend/tests/test_ingest_api.py`:

```python
from app.rag.schemas import DocumentInput, SourceMetadata


def opendota_api_test_documents() -> list[DocumentInput]:
    return [
        DocumentInput(
            text="Blink Dagger is an OpenDota item constant. Cost: 2250. Mobility item.",
            metadata=SourceMetadata(
                source_url="https://api.opendota.com/api/constants/items/blink",
                source_name="OpenDota Item: Blink Dagger",
                patch_version=None,
                entity_type="item",
                entity_name="Blink Dagger",
                updated_at="2026-06-20",
            ),
        )
    ]


def test_ingest_documents_can_include_injected_opendota_knowledge_loader(client: TestClient) -> None:
    client.app.state.opendota_knowledge_documents_loader = opendota_api_test_documents

    response = client.post("/api/ingest/documents")

    assert response.status_code == 200
    payload = response.json()
    assert payload["documents"] == 4
    assert "OpenDota Item: Blink Dagger" in payload["sources"]
```

- [ ] **Step 2: Run focused API test to verify failure**

Run:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest backend/tests/test_ingest_api.py::test_ingest_documents_can_include_injected_opendota_knowledge_loader -v -p no:cacheprovider --basetemp backend\.tmp\pytest-m11-ingest-api"
```

Expected: FAIL because the API does not yet read `opendota_knowledge_documents_loader`.

- [ ] **Step 3: Add setting**

Modify `backend/app/core/config.py`:

```python
class Settings(BaseSettings):
    app_name: str = "Dota 2 RAG Assistant"
    sqlite_path: Path = Path("data/sqlite/dota2_rag.db")
    vector_data_path: Path = Path("data/milvus")
    vector_index_path: Path = Path("data/milvus/text_chunks.json")
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "qwen2.5:7b"
    official_dota_sources_enabled: bool = False
    opendota_knowledge_sources_enabled: bool = True
    opendota_base_url: str = "https://api.opendota.com/api"
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        description="Comma-separated browser origins allowed to call the API.",
    )
```

- [ ] **Step 4: Wire OpenDota knowledge loader into API**

Modify `backend/app/api/ingest.py`:

```python
from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.data_sources.official_dota import load_official_dota_documents
from app.data_sources.opendota_knowledge import (
    OpenDotaKnowledgeClient,
    load_opendota_knowledge_documents,
)
from app.jobs.ingest_documents import DocumentLoader, IngestResult, ingest_seed_documents
from app.rag.embeddings import DeterministicEmbedder
from app.vector_store.milvus import LocalVectorStore

router = APIRouter(prefix="/api", tags=["ingestion"])


class SourcesResponse(BaseModel):
    sources: list[str]


def _store_for_request(request: Request) -> LocalVectorStore:
    settings = request.app.state.settings
    return LocalVectorStore(settings.vector_index_path)


def _opendota_loader_for_request(request: Request) -> DocumentLoader:
    settings = request.app.state.settings

    def load_documents() -> list:
        return load_opendota_knowledge_documents(
            client=OpenDotaKnowledgeClient(base_url=settings.opendota_base_url)
        )

    return load_documents


@router.post("/ingest/documents", response_model=IngestResult)
def ingest_documents(request: Request) -> IngestResult:
    store = _store_for_request(request)
    embedder = DeterministicEmbedder(dimensions=64)
    settings = request.app.state.settings

    document_loaders: list[DocumentLoader] = []

    official_documents_loader = getattr(request.app.state, "official_documents_loader", None)
    if official_documents_loader is None and settings.official_dota_sources_enabled:
        official_documents_loader = load_official_dota_documents
    if official_documents_loader is not None:
        document_loaders.append(official_documents_loader)

    opendota_knowledge_loader = getattr(
        request.app.state,
        "opendota_knowledge_documents_loader",
        None,
    )
    if opendota_knowledge_loader is None and settings.opendota_knowledge_sources_enabled:
        opendota_knowledge_loader = _opendota_loader_for_request(request)
    if opendota_knowledge_loader is not None:
        document_loaders.append(opendota_knowledge_loader)

    return ingest_seed_documents(
        store=store,
        embedder=embedder,
        document_loaders=document_loaders,
    )


@router.get("/sources", response_model=SourcesResponse)
def list_sources(request: Request) -> SourcesResponse:
    store = _store_for_request(request)
    return SourcesResponse(sources=store.list_sources())
```

If the existing test app does not disable network OpenDota ingestion, update the test fixture settings so `opendota_knowledge_sources_enabled=False` by default and rely on injection for this test.

- [ ] **Step 5: Run focused API tests**

Run:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest backend/tests/test_ingest_api.py backend/tests/test_config.py -v -p no:cacheprovider --basetemp backend\.tmp\pytest-m11-ingest-api"
```

Expected: PASS.

- [ ] **Step 6: Commit API integration**

```powershell
git add backend/app/core/config.py backend/app/api/ingest.py backend/tests/test_ingest_api.py
git commit -m "feat: ingest opendota knowledge documents"
```

---

### Task 4: Full Verification And Documentation Touch-Up

**Files:**
- Modify: `README.md`
- Modify: `docs/local-runbook.md`
- Modify: `docs/demo-checklist.md`

- [ ] **Step 1: Update docs for OpenDota knowledge ingestion**

In `README.md`, add OpenDota hero/item knowledge to `Current capabilities`:

```markdown
- OpenDota hero and item constants ingested into the local vector knowledge base.
```

In `docs/local-runbook.md`, add a note under document refresh:

```markdown
Document refresh includes seed knowledge and, by default, OpenDota hero/item constants. Official Dota sources remain controlled by `official_dota_sources_enabled`.
```

In `docs/demo-checklist.md`, add sample checks:

```markdown
- Ask `Blink Dagger cost mobility` and confirm the answer cites `OpenDota Item: Blink Dagger`.
- Ask `Axe roles strength initiator` and confirm the answer cites `OpenDota Hero: Axe`.
```

- [ ] **Step 2: Run full backend test suite**

Run:

```powershell
C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe -Command "`$env:TEMP='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp'; `$env:TMP=`$env:TEMP; `$env:PYTHONPATH='C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend\.tmp\py312-packages;C:\Users\jaime\OneDrive\Desktop\dota2-rag-assistant\backend'; C:\Users\jaime\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest -v -p no:cacheprovider --basetemp backend\.tmp\pytest-m11-final"
```

Expected: PASS.

- [ ] **Step 3: Run frontend regression tests**

Run:

```powershell
npm test
```

from `frontend`.

Expected: PASS.

- [ ] **Step 4: Run frontend build**

Run:

```powershell
npm run build
```

from `frontend`.

Expected: PASS.

- [ ] **Step 5: Commit documentation and final verification changes**

```powershell
git add README.md docs/local-runbook.md docs/demo-checklist.md
git commit -m "docs: describe opendota knowledge ingestion"
```

- [ ] **Step 6: Final status check**

Run:

```powershell
git status --short --branch
```

Expected: branch is ahead of origin with only committed M11 changes and no unstaged files.

## Self-Review

- Spec coverage: The plan implements OpenDota hero and item crawling, parsing, document conversion, ingestion composition, API integration, settings, retrievability tests, and documentation updates.
- Placeholder scan: The plan contains no placeholders or deferred implementation markers.
- Type consistency: The plan uses `DocumentLoader = Callable[[], list[DocumentInput]]`, keeps `official_documents_loader` backward compatible, and uses `opendota_knowledge_documents_loader` consistently in API tests and implementation.
