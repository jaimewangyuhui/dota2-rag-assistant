from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoAcceptanceCase:
    question: str
    expected_type: str
    expected_terms: tuple[str, ...] = ()
    requires_sources: bool = False
    requires_stats: bool = False
    allows_missing_coverage: bool = False


DEMO_ACCEPTANCE_CASES: tuple[DemoAcceptanceCase, ...] = (
    DemoAcceptanceCase(
        question="BKB有什么用？",
        expected_type="knowledge",
        expected_terms=("Black King Bar", "BKB"),
        requires_sources=True,
    ),
    DemoAcceptanceCase(
        question="What does BKB do?",
        expected_type="knowledge",
        expected_terms=("Black King Bar", "BKB"),
        requires_sources=True,
    ),
    DemoAcceptanceCase(
        question="Roshan 会掉什么？",
        expected_type="knowledge",
        expected_terms=("Roshan",),
        requires_sources=True,
    ),
    DemoAcceptanceCase(
        question="肉山掉什么？",
        expected_type="knowledge",
        expected_terms=("Roshan",),
        requires_sources=True,
    ),
    DemoAcceptanceCase(
        question="黑皇杖什么时候出？",
        expected_type="advice",
        expected_terms=("Black King Bar", "BKB"),
        requires_sources=True,
    ),
    DemoAcceptanceCase(
        question="Blink Dagger怎么用？",
        expected_type="advice",
        expected_terms=("Blink Dagger",),
        requires_sources=True,
    ),
    DemoAcceptanceCase(
        question="跳刀怎么用？",
        expected_type="advice",
        expected_terms=("Blink Dagger",),
        requires_sources=True,
    ),
    DemoAcceptanceCase(
        question="Axe win rate meta",
        expected_type="stats",
        expected_terms=("Axe", "52.0%", "25.0%"),
        requires_stats=True,
    ),
    DemoAcceptanceCase(
        question="斧王胜率",
        expected_type="stats",
        expected_terms=("Axe", "52.0%"),
        requires_stats=True,
    ),
    DemoAcceptanceCase(
        question="7.36 BKB 改了什么？",
        expected_type="patch",
        expected_terms=("Black King Bar", "BKB"),
        requires_sources=True,
    ),
    DemoAcceptanceCase(
        question="最近版本 Roshan 有什么变化？",
        expected_type="patch",
        expected_terms=("Roshan",),
        requires_sources=True,
    ),
    DemoAcceptanceCase(
        question="Chen 的神杖效果是什么？",
        expected_type="knowledge_missing",
        allows_missing_coverage=True,
    ),
)
