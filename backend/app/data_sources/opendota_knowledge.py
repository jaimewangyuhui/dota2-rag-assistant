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
