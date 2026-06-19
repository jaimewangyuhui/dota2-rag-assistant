from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def read_repo_file(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_readme_links_current_demo_and_runbook_docs() -> None:
    readme = read_repo_file("README.md")

    assert "Current capabilities" in readme
    assert "docs/local-runbook.md" in readme
    assert "docs/demo-checklist.md" in readme
    assert "M9" in readme


def test_local_runbook_covers_required_local_setup_topics() -> None:
    runbook = read_repo_file("docs/local-runbook.md")

    for expected in [
        "Docker Ollama",
        "Backend startup",
        "Frontend startup",
        "Refresh Knowledge",
        "Refresh Stats",
        "Verification",
        "Troubleshooting",
        "Conda Python blocked by Windows policy",
    ]:
        assert expected in runbook


def test_gitignore_ignores_local_vscode_directory() -> None:
    gitignore = read_repo_file(".gitignore")

    assert ".vscode/" in gitignore
