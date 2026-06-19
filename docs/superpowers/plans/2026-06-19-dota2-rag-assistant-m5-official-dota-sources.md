# Dota 2 RAG Assistant M5 Official Dota Sources Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add official Dota 2 hero and patch note source adapters that convert official website data into existing RAG `DocumentInput` objects and ingest them alongside seed documents.

**Architecture:** M5 adds a focused `backend/app/data_sources/official_dota.py` module with typed records, fixture-friendly parsers, document converters, and a small HTTP client. The existing ingestion job remains responsible for chunking, embedding, and vector upsert; it accepts an optional official-document loader so tests stay offline and deterministic.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, httpx, pytest, existing deterministic embedder, existing local vector store, official Dota 2 website URLs.

---

## File Structure

- Create `backend/app/data_sources/official_dota.py`: official client, records, parsers, converters, and combined loader.
- Create `backend/tests/fixtures/official_heroes_sample.json`: stable hero fixture with two heroes.
- Create `backend/tests/fixtures/official_patch_sample.json`: stable patch fixture with one patch.
- Create `backend/tests/test_official_dota_source.py`: parser, converter, client, and loader tests.
- Modify `backend/app/jobs/ingest_documents.py`: add `official_documents_loader` injection and count seed plus official documents.
- Modify `backend/app/api/ingest.py`: use official loader for runtime ingestion.
- Modify `backend/tests/test_ingest_job.py`: verify official docs are indexed when loader is provided.
- Modify `backend/tests/test_ingest_api.py`: override official loader in app state and assert official sources return.
- Modify `README.md`: add M5 official heroes/patches ingestion note.

## Task 1: Official Hero Source Parser and Converter

**Files:**
- Create: `backend/app/data_sources/official_dota.py`
- Create: `backend/tests/fixtures/official_heroes_sample.json`
- Create: `backend/tests/test_official_dota_source.py`

- [ ] **Step 1: Write hero fixture**

Create `backend/tests/fixtures/official_heroes_sample.json`:

```json
{
  "heroes": [
    {
      "name": "npc_dota_hero_axe",
      "localized_name": "Axe",
      "roles": ["Initiator", "Durable", "Disabler"],
      "primary_attribute": "str",
      "summary": "Axe thrives in the chaos of battle, forcing enemies to attack him and punishing clustered opponents.",
      "updated_at": "2026-06-19"
    },
    {
      "name": "npc_dota_hero_juggernaut",
      "localized_name": "Juggernaut",
      "roles": ["Carry", "Pusher", "Escape"],
      "primary_attribute": "agi",
      "summary": "Juggernaut combines lane sustain, spell immunity timing, and burst damage from Omnislash.",
      "updated_at": "2026-06-19"
    }
  ]
}
```

- [ ] **Step 2: Write failing hero source tests**

Create `backend/tests/test_official_dota_source.py`:

```python
from pathlib import Path

from app.data_sources.official_dota import (
    hero_records_to_documents,
    parse_hero_records,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_parse_hero_records_from_official_fixture() -> None:
    records = parse_hero_records(
        read_fixture("official_heroes_sample.json"),
        source_url="https://www.dota2.com/heroes",
    )

    assert [record.localized_name for record in records] == ["Axe", "Juggernaut"]
    assert records[0].roles == ["Initiator", "Durable", "Disabler"]
    assert records[0].primary_attribute == "str"
    assert records[0].source_url == "https://www.dota2.com/heroes/axe"


def test_hero_records_convert_to_documents() -> None:
    records = parse_hero_records(
        read_fixture("official_heroes_sample.json"),
        source_url="https://www.dota2.com/heroes",
    )

    documents = hero_records_to_documents(records)

    assert len(documents) == 2
    assert documents[0].metadata.source_name == "Official Dota 2: Axe"
    assert documents[0].metadata.entity_type == "hero"
    assert documents[0].metadata.entity_name == "Axe"
    assert documents[0].metadata.patch_version is None
    assert "Roles: Initiator, Durable, Disabler" in documents[0].text
    assert "Axe thrives in the chaos of battle" in documents[0].text
```

- [ ] **Step 3: Run hero source tests and verify RED**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_official_dota_source.py -v -p no:cacheprovider --basetemp .tmp\pytest-m5-official-source
```

Expected: FAIL because `app.data_sources.official_dota` does not exist.

- [ ] **Step 4: Add minimal hero parser and converter**

Create `backend/app/data_sources/official_dota.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass

from app.rag.schemas import DocumentInput, SourceMetadata


class OfficialDotaParseError(ValueError):
    pass


def _slug(value: str) -> str:
    return value.lower().replace(" ", "-").replace("'", "")


@dataclass(frozen=True)
class OfficialHeroRecord:
    name: str
    localized_name: str
    roles: list[str]
    primary_attribute: str
    summary: str
    source_url: str
    updated_at: str


def parse_hero_records(raw: str, source_url: str) -> list[OfficialHeroRecord]:
    payload = json.loads(raw)
    heroes = payload.get("heroes")
    if not isinstance(heroes, list) or not heroes:
        raise OfficialDotaParseError(f"No hero records found in {source_url}")

    records: list[OfficialHeroRecord] = []
    for hero in heroes:
        localized_name = str(hero["localized_name"])
        records.append(
            OfficialHeroRecord(
                name=str(hero["name"]),
                localized_name=localized_name,
                roles=[str(role) for role in hero.get("roles", [])],
                primary_attribute=str(hero.get("primary_attribute", "")),
                summary=str(hero["summary"]),
                source_url=f"{source_url.rstrip('/')}/{_slug(localized_name)}",
                updated_at=str(hero["updated_at"]),
            )
        )
    return records


def hero_records_to_documents(records: list[OfficialHeroRecord]) -> list[DocumentInput]:
    documents: list[DocumentInput] = []
    for record in records:
        roles = ", ".join(record.roles) if record.roles else "Unknown"
        text = (
            f"{record.localized_name} is an official Dota 2 hero. "
            f"Primary attribute: {record.primary_attribute}. "
            f"Roles: {roles}. "
            f"{record.summary}"
        )
        documents.append(
            DocumentInput(
                text=text,
                metadata=SourceMetadata(
                    source_url=record.source_url,
                    source_name=f"Official Dota 2: {record.localized_name}",
                    patch_version=None,
                    entity_type="hero",
                    entity_name=record.localized_name,
                    updated_at=record.updated_at,
                ),
            )
        )
    return documents
```

- [ ] **Step 5: Run hero source tests and verify GREEN**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_official_dota_source.py -v -p no:cacheprovider --basetemp .tmp\pytest-m5-official-source
```

Expected: PASS for hero parser and converter tests.

- [ ] **Step 6: Commit hero source parser**

Run:

```powershell
git add backend/app/data_sources/official_dota.py backend/tests/fixtures/official_heroes_sample.json backend/tests/test_official_dota_source.py
git commit -m "feat: parse official dota hero sources"
```

## Task 2: Official Patch Parser and Combined Loader

**Files:**
- Modify: `backend/app/data_sources/official_dota.py`
- Create: `backend/tests/fixtures/official_patch_sample.json`
- Modify: `backend/tests/test_official_dota_source.py`

- [ ] **Step 1: Write patch fixture**

Create `backend/tests/fixtures/official_patch_sample.json`:

```json
{
  "patches": [
    {
      "patch_version": "7.36",
      "title": "Gameplay Update 7.36",
      "summary": "Patch 7.36 introduced broad gameplay changes and hero adjustments.",
      "sections": [
        {
          "heading": "General",
          "entries": ["Added innate abilities for heroes.", "Updated several neutral item timings."]
        },
        {
          "heading": "Heroes",
          "entries": ["Axe received adjustments to lane pressure.", "Juggernaut received ability tuning."]
        }
      ],
      "source_url": "https://www.dota2.com/patches/7.36",
      "updated_at": "2026-06-18"
    }
  ]
}
```

- [ ] **Step 2: Add failing patch and loader tests**

Append to `backend/tests/test_official_dota_source.py`:

```python
from app.data_sources.official_dota import (
    OfficialDotaClient,
    load_official_dota_documents,
    parse_patch_records,
    patch_records_to_documents,
)


def test_parse_patch_records_from_official_fixture() -> None:
    records = parse_patch_records(
        read_fixture("official_patch_sample.json"),
        source_url="https://www.dota2.com/patches",
    )

    assert len(records) == 1
    assert records[0].patch_version == "7.36"
    assert records[0].title == "Gameplay Update 7.36"
    assert records[0].sections[0].heading == "General"
    assert records[0].source_url == "https://www.dota2.com/patches/7.36"


def test_patch_records_convert_to_documents() -> None:
    records = parse_patch_records(
        read_fixture("official_patch_sample.json"),
        source_url="https://www.dota2.com/patches",
    )

    documents = patch_records_to_documents(records)

    assert len(documents) == 1
    assert documents[0].metadata.source_name == "Official Dota 2 Patch 7.36"
    assert documents[0].metadata.entity_type == "patch"
    assert documents[0].metadata.entity_name == "Gameplay Update 7.36"
    assert documents[0].metadata.patch_version == "7.36"
    assert "Added innate abilities for heroes." in documents[0].text


class FixtureOfficialClient(OfficialDotaClient):
    def fetch_heroes(self) -> str:
        return read_fixture("official_heroes_sample.json")

    def fetch_patches(self) -> str:
        return read_fixture("official_patch_sample.json")


def test_load_official_dota_documents_combines_heroes_and_patches() -> None:
    documents = load_official_dota_documents(FixtureOfficialClient())

    assert [document.metadata.entity_type for document in documents] == [
        "hero",
        "hero",
        "patch",
    ]
    assert documents[-1].metadata.source_name == "Official Dota 2 Patch 7.36"
```

- [ ] **Step 3: Run patch tests and verify RED**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_official_dota_source.py -v -p no:cacheprovider --basetemp .tmp\pytest-m5-official-patch
```

Expected: FAIL because patch records, client, and combined loader are not implemented.

- [ ] **Step 4: Implement patch parser, document converter, and client**

Modify `backend/app/data_sources/official_dota.py`:

```python
import httpx
```

Add below `OfficialHeroRecord`:

```python
@dataclass(frozen=True)
class OfficialPatchSection:
    heading: str
    entries: list[str]


@dataclass(frozen=True)
class OfficialPatchRecord:
    patch_version: str
    title: str
    summary: str
    sections: list[OfficialPatchSection]
    source_url: str
    updated_at: str
```

Add below `parse_hero_records`:

```python
class OfficialDotaClient:
    heroes_url = "https://www.dota2.com/heroes"
    patches_url = "https://www.dota2.com/patches"

    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = timeout

    def _get(self, url: str) -> str:
        response = httpx.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.text

    def fetch_heroes(self) -> str:
        return self._get(self.heroes_url)

    def fetch_patches(self) -> str:
        return self._get(self.patches_url)


def parse_patch_records(raw: str, source_url: str) -> list[OfficialPatchRecord]:
    payload = json.loads(raw)
    patches = payload.get("patches")
    if not isinstance(patches, list) or not patches:
        raise OfficialDotaParseError(f"No patch records found in {source_url}")

    records: list[OfficialPatchRecord] = []
    for patch in patches:
        sections = [
            OfficialPatchSection(
                heading=str(section["heading"]),
                entries=[str(entry) for entry in section.get("entries", [])],
            )
            for section in patch.get("sections", [])
        ]
        records.append(
            OfficialPatchRecord(
                patch_version=str(patch["patch_version"]),
                title=str(patch["title"]),
                summary=str(patch["summary"]),
                sections=sections,
                source_url=str(patch.get("source_url") or f"{source_url.rstrip('/')}/{patch['patch_version']}"),
                updated_at=str(patch["updated_at"]),
            )
        )
    return records
```

Add below `hero_records_to_documents`:

```python
def patch_records_to_documents(records: list[OfficialPatchRecord]) -> list[DocumentInput]:
    documents: list[DocumentInput] = []
    for record in records:
        section_text = " ".join(
            f"{section.heading}: {' '.join(section.entries)}" for section in record.sections
        )
        documents.append(
            DocumentInput(
                text=f"{record.title}. {record.summary} {section_text}".strip(),
                metadata=SourceMetadata(
                    source_url=record.source_url,
                    source_name=f"Official Dota 2 Patch {record.patch_version}",
                    patch_version=record.patch_version,
                    entity_type="patch",
                    entity_name=record.title,
                    updated_at=record.updated_at,
                ),
            )
        )
    return documents


def load_official_dota_documents(
    client: OfficialDotaClient | None = None,
) -> list[DocumentInput]:
    active_client = client or OfficialDotaClient()
    hero_documents = hero_records_to_documents(
        parse_hero_records(active_client.fetch_heroes(), active_client.heroes_url)
    )
    patch_documents = patch_records_to_documents(
        parse_patch_records(active_client.fetch_patches(), active_client.patches_url)
    )
    return hero_documents + patch_documents
```

- [ ] **Step 5: Run patch tests and verify GREEN**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_official_dota_source.py -v -p no:cacheprovider --basetemp .tmp\pytest-m5-official-patch
```

Expected: PASS for all official source tests.

- [ ] **Step 6: Commit patch parser and loader**

Run:

```powershell
git add backend/app/data_sources/official_dota.py backend/tests/fixtures/official_patch_sample.json backend/tests/test_official_dota_source.py
git commit -m "feat: parse official dota patch sources"
```

## Task 3: Ingest Official Documents

**Files:**
- Modify: `backend/app/jobs/ingest_documents.py`
- Modify: `backend/app/api/ingest.py`
- Modify: `backend/tests/test_ingest_job.py`
- Modify: `backend/tests/test_ingest_api.py`

- [ ] **Step 1: Add failing ingest job test for official docs**

Append to `backend/tests/test_ingest_job.py`:

```python
from app.rag.schemas import DocumentInput, SourceMetadata


def official_test_documents() -> list[DocumentInput]:
    return [
        DocumentInput(
            text="Axe is an official Dota 2 hero with Initiator and Durable roles.",
            metadata=SourceMetadata(
                source_url="https://www.dota2.com/heroes/axe",
                source_name="Official Dota 2: Axe",
                patch_version=None,
                entity_type="hero",
                entity_name="Axe",
                updated_at="2026-06-19",
            ),
        ),
        DocumentInput(
            text="Gameplay Update 7.36 added innate abilities for heroes.",
            metadata=SourceMetadata(
                source_url="https://www.dota2.com/patches/7.36",
                source_name="Official Dota 2 Patch 7.36",
                patch_version="7.36",
                entity_type="patch",
                entity_name="Gameplay Update 7.36",
                updated_at="2026-06-18",
            ),
        ),
    ]


def test_ingest_seed_documents_can_include_official_documents(tmp_path: Path) -> None:
    store = LocalVectorStore(tmp_path / "vectors.json")
    embedder = DeterministicEmbedder(dimensions=64)

    result = ingest_seed_documents(
        store=store,
        embedder=embedder,
        official_documents_loader=official_test_documents,
    )

    assert result.documents == 5
    assert "Official Dota 2: Axe" in result.sources
    retrieved = Retriever(store=store, embedder=embedder).retrieve("Axe official hero", limit=1)
    assert retrieved[0].chunk.metadata.entity_name == "Axe"
```

- [ ] **Step 2: Run ingest job tests and verify RED**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_ingest_job.py -v -p no:cacheprovider --basetemp .tmp\pytest-m5-ingest-job
```

Expected: FAIL because `ingest_seed_documents` does not accept `official_documents_loader`.

- [ ] **Step 3: Update ingest job to accept official documents**

Modify `backend/app/jobs/ingest_documents.py`:

```python
from collections.abc import Callable
```

Change `ingest_seed_documents` to:

```python
OfficialDocumentsLoader = Callable[[], list[DocumentInput]]


def ingest_seed_documents(
    store: LocalVectorStore,
    embedder: Embedder,
    official_documents_loader: OfficialDocumentsLoader | None = None,
) -> IngestResult:
    documents = load_seed_documents()
    if official_documents_loader is not None:
        documents.extend(official_documents_loader())
    chunks = [chunk for document in documents for chunk in chunk_document(document)]
    entries = [(chunk, embedder.embed(chunk.text)) for chunk in chunks]
    store.upsert(entries)
    return IngestResult(
        documents=len(documents),
        chunks=len(chunks),
        sources=store.list_sources(),
    )
```

- [ ] **Step 4: Run ingest job tests and verify GREEN**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_ingest_job.py -v -p no:cacheprovider --basetemp .tmp\pytest-m5-ingest-job
```

Expected: PASS.

- [ ] **Step 5: Add failing ingest API official override test**

Append to `backend/tests/test_ingest_api.py`:

```python
from app.rag.schemas import DocumentInput, SourceMetadata


def official_api_documents() -> list[DocumentInput]:
    return [
        DocumentInput(
            text="Axe is an official Dota 2 hero.",
            metadata=SourceMetadata(
                source_url="https://www.dota2.com/heroes/axe",
                source_name="Official Dota 2: Axe",
                patch_version=None,
                entity_type="hero",
                entity_name="Axe",
                updated_at="2026-06-19",
            ),
        )
    ]


def test_ingest_documents_endpoint_can_index_official_documents(tmp_path: Path) -> None:
    settings = Settings(
        sqlite_path=tmp_path / "sqlite" / "dota2_rag.db",
        vector_data_path=tmp_path / "vectors",
    )
    app = create_app(settings)
    app.state.official_documents_loader = official_api_documents
    client = TestClient(app)

    response = client.post("/api/ingest/documents")

    assert response.status_code == 200
    payload = response.json()
    assert payload["documents"] == 4
    assert "Official Dota 2: Axe" in payload["sources"]
```

- [ ] **Step 6: Run ingest API tests and verify RED**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_ingest_api.py -v -p no:cacheprovider --basetemp .tmp\pytest-m5-ingest-api
```

Expected: FAIL because `app.state.official_documents_loader` is not passed into the ingest job.

- [ ] **Step 7: Wire official loader into ingest API**

Modify `backend/app/api/ingest.py`:

```python
from app.data_sources.official_dota import load_official_dota_documents
```

Inside the endpoint before calling `ingest_seed_documents`:

```python
official_documents_loader = getattr(
    request.app.state,
    "official_documents_loader",
    load_official_dota_documents,
)
```

Call:

```python
result = ingest_seed_documents(
    store=store,
    embedder=embedder,
    official_documents_loader=official_documents_loader,
)
```

- [ ] **Step 8: Run ingest API tests and verify GREEN**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_ingest_api.py -v -p no:cacheprovider --basetemp .tmp\pytest-m5-ingest-api
```

Expected: PASS.

- [ ] **Step 9: Commit official ingestion integration**

Run:

```powershell
git add backend/app/jobs/ingest_documents.py backend/app/api/ingest.py backend/tests/test_ingest_job.py backend/tests/test_ingest_api.py
git commit -m "feat: ingest official dota documents"
```

## Task 4: Documentation and Final Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add M5 README instructions**

Append to `README.md`:

```markdown
## M5 Official Heroes And Patches

M5 indexes official Dota 2 hero and patch note documents in addition to local seed documents.

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/ingest/documents
```

Tests use local fixtures and do not call `dota2.com`. Official item scraping is intentionally out of scope for M5.
```

- [ ] **Step 2: Run official source tests**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest tests/test_official_dota_source.py -v -p no:cacheprovider --basetemp .tmp\pytest-m5-official-final
```

Expected: PASS.

- [ ] **Step 3: Run full backend tests**

Run:

```powershell
cd backend
$env:TEMP="$PWD\.tmp"; $env:TMP=$env:TEMP
.\.conda\python.exe -m pytest -v -p no:cacheprovider --basetemp .tmp\pytest-m5-final
```

Expected: PASS.

- [ ] **Step 4: Run frontend regression tests and build**

Run:

```powershell
cd frontend
npm test
npm run build
```

Expected: frontend tests and build pass.

- [ ] **Step 5: Manual local smoke**

With backend running, run:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/ingest/documents | ConvertTo-Json -Depth 8
```

Expected: response includes seed sources plus official sources such as `Official Dota 2: Axe` and `Official Dota 2 Patch 7.36`.

Then ask:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/chat -ContentType "application/json" -Body '{"message":"What is Axe?"}' | ConvertTo-Json -Depth 8
```

Expected: response sources include `Official Dota 2: Axe`.

- [ ] **Step 6: Commit docs and any final fixes**

Run:

```powershell
git add README.md
git commit -m "docs: add m5 official source instructions"
```

## Self-Review Notes

- Spec coverage: the plan covers official heroes, official patches, no items, source adapter isolation, fixture tests, ingestion integration, metadata citations, README instructions, backend verification, and frontend regression checks.
- Scope: the plan does not add OpenDota, statistics, frontend UI changes, scheduled refresh, full patch archive ingestion, or unofficial scraping.
- Type consistency: all generated documents use existing `DocumentInput` and `SourceMetadata`; `updated_at` is always a string and `patch_version` is `None` for heroes.
