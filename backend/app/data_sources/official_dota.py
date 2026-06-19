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
