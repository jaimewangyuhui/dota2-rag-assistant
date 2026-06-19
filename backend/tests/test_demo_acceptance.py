from tests.fixtures.demo_acceptance import DEMO_ACCEPTANCE_CASES, DemoAcceptanceCase


def test_demo_acceptance_cases_cover_required_question_types() -> None:
    question_types = {case.expected_type for case in DEMO_ACCEPTANCE_CASES}

    assert question_types == {"knowledge", "advice", "stats", "patch", "knowledge_missing"}


def test_demo_acceptance_cases_are_readable_contracts() -> None:
    for case in DEMO_ACCEPTANCE_CASES:
        assert isinstance(case, DemoAcceptanceCase)
        assert case.question
        assert case.expected_type
        assert not (case.requires_sources and case.allows_missing_coverage)
