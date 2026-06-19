from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

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
                source_url=str(
                    patch.get("source_url")
                    or f"{source_url.rstrip('/')}/{patch['patch_version']}"
                ),
                updated_at=str(patch["updated_at"]),
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
