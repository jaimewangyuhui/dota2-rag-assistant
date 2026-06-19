from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from typing import Any

import httpx

from app.rag.schemas import DocumentInput, SourceMetadata


class OfficialDotaParseError(ValueError):
    pass


def _slug(value: str) -> str:
    return value.lower().replace(" ", "-").replace("'", "")


def _attribute_name(value: Any) -> str:
    attributes = {0: "str", 1: "agi", 2: "int", 3: "all"}
    if isinstance(value, int):
        return attributes.get(value, "")
    return str(value)


def _date_from_timestamp(value: Any) -> str:
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, tz=UTC).date().isoformat()
    return str(value)


def _clean_note(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", "", value)
    return unescape(without_tags).strip()


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
    heroes_url = "https://www.dota2.com/datafeed/herolist?language=english"
    patch_list_url = "https://www.dota2.com/datafeed/patchnoteslist?language=english"
    patch_notes_url = "https://www.dota2.com/datafeed/patchnotes?version={version}&language=english"
    hero_source_url = "https://www.dota2.com/heroes"
    patch_source_url = "https://www.dota2.com/patches"

    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = timeout

    def _get(self, url: str) -> str:
        response = httpx.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.text

    def fetch_heroes(self) -> str:
        return self._get(self.heroes_url)

    def fetch_patches(self) -> str:
        payload = json.loads(self._get(self.patch_list_url))
        patches = payload.get("patches")
        if not isinstance(patches, list) or not patches:
            raise OfficialDotaParseError("No official patch list records found")
        latest_patch = max(patches, key=lambda patch: patch.get("patch_timestamp", 0))
        version = latest_patch["patch_number"]
        return self._get(self.patch_notes_url.format(version=version))


def parse_hero_records(raw: str, source_url: str) -> list[OfficialHeroRecord]:
    payload = json.loads(raw)
    heroes = payload.get("heroes")
    if heroes is None:
        heroes = payload.get("result", {}).get("data", {}).get("heroes")
    if not isinstance(heroes, list) or not heroes:
        raise OfficialDotaParseError(f"No hero records found in {source_url}")

    records: list[OfficialHeroRecord] = []
    for hero in heroes:
        localized_name = str(hero.get("localized_name") or hero["name_loc"])
        records.append(
            OfficialHeroRecord(
                name=str(hero["name"]),
                localized_name=localized_name,
                roles=[str(role) for role in hero.get("roles", [])],
                primary_attribute=_attribute_name(
                    hero.get("primary_attribute", hero.get("primary_attr", ""))
                ),
                summary=str(
                    hero.get("summary")
                    or f"Official Dota 2 hero roster entry for {localized_name}."
                ),
                source_url=f"{source_url.rstrip('/')}/{_slug(localized_name)}",
                updated_at=str(hero.get("updated_at", "")),
            )
        )
    return records


def parse_patch_records(raw: str, source_url: str) -> list[OfficialPatchRecord]:
    payload = json.loads(raw)
    patches = payload.get("patches")
    if patches is None and "patch_number" in payload:
        patches = [payload]
    if not isinstance(patches, list) or not patches:
        raise OfficialDotaParseError(f"No patch records found in {source_url}")

    records: list[OfficialPatchRecord] = []
    for patch in patches:
        sections = _patch_sections(patch)
        patch_version = str(patch.get("patch_version") or patch["patch_number"])
        title = str(patch.get("title") or f"Gameplay Update {patch_version}")
        records.append(
            OfficialPatchRecord(
                patch_version=patch_version,
                title=title,
                summary=str(
                    patch.get("summary") or f"Official Dota 2 patch notes for {patch_version}."
                ),
                sections=sections,
                source_url=str(
                    patch.get("source_url")
                    or f"{source_url.rstrip('/')}/{patch_version}"
                ),
                updated_at=str(
                    patch.get("updated_at") or _date_from_timestamp(patch.get("patch_timestamp", ""))
                ),
            )
        )
    return records


def _patch_sections(patch: dict[str, Any]) -> list[OfficialPatchSection]:
    if "sections" in patch:
        return [
            OfficialPatchSection(
                heading=str(section["heading"]),
                entries=[str(entry) for entry in section.get("entries", [])],
            )
            for section in patch.get("sections", [])
        ]

    entries: list[str] = []
    for group in patch.get("general_notes", []):
        for note in group.get("generic", []):
            text = _clean_note(str(note.get("note", "")))
            if text:
                entries.append(text)
    return [OfficialPatchSection(heading="General", entries=entries)] if entries else []


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
        parse_hero_records(active_client.fetch_heroes(), active_client.hero_source_url)
    )
    patch_documents = patch_records_to_documents(
        parse_patch_records(active_client.fetch_patches(), active_client.patch_source_url)
    )
    return hero_documents + patch_documents
