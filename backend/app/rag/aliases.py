from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class AliasEntry:
    canonical: str
    aliases: tuple[str, ...]
    expansion: tuple[str, ...]
    entity_type: str


@dataclass(frozen=True)
class NormalizedQuestion:
    original: str
    expanded: str
    canonical_terms: list[str]
    canonical_hero: str | None = None


ALIAS_ENTRIES: tuple[AliasEntry, ...] = (
    AliasEntry(
        canonical="Axe",
        aliases=("axe", "斧王"),
        expansion=("Axe",),
        entity_type="hero",
    ),
    AliasEntry(
        canonical="Black King Bar / BKB",
        aliases=("bkb", "black king bar", "黑皇杖"),
        expansion=("Black King Bar", "BKB"),
        entity_type="item",
    ),
    AliasEntry(
        canonical="Blink Dagger",
        aliases=("blink dagger", "跳刀"),
        expansion=("Blink Dagger",),
        entity_type="item",
    ),
    AliasEntry(
        canonical="Roshan",
        aliases=("roshan", "肉山"),
        expansion=("Roshan",),
        entity_type="objective",
    ),
)


def _matches_alias(question: str, alias: str) -> bool:
    if alias.isascii() and alias.replace(" ", "").isalnum():
        return re.search(rf"\b{re.escape(alias)}\b", question, flags=re.IGNORECASE) is not None
    return alias.lower() in question.lower()


def _append_missing(parts: list[str], value: str) -> None:
    if not any(existing.lower() == value.lower() for existing in parts):
        parts.append(value)


def normalize_question(question: str) -> NormalizedQuestion:
    parts = [question]
    canonical_terms: list[str] = []
    canonical_hero: str | None = None

    for entry in ALIAS_ENTRIES:
        if not any(_matches_alias(question, alias) for alias in entry.aliases):
            continue

        _append_missing(canonical_terms, entry.canonical)
        for term in entry.expansion:
            if not _matches_alias(" ".join(parts), term):
                parts.append(term)
        if entry.entity_type == "hero":
            canonical_hero = entry.canonical

    return NormalizedQuestion(
        original=question,
        expanded=" ".join(parts),
        canonical_terms=canonical_terms,
        canonical_hero=canonical_hero,
    )
