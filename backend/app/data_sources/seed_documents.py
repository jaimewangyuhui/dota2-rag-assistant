from app.rag.schemas import DocumentInput, SourceMetadata


def load_seed_documents() -> list[DocumentInput]:
    return [
        DocumentInput(
            text=(
                "Black King Bar, often called BKB, is a core defensive item. "
                "It grants a timed spell immunity effect that helps heroes commit "
                "during fights, dodge disables, and protect key damage windows."
            ),
            metadata=SourceMetadata(
                source_url="seed://items/black-king-bar",
                source_name="Seed: Black King Bar",
                patch_version="7.36",
                entity_type="item",
                entity_name="Black King Bar",
                updated_at="2026-06-18",
            ),
        ),
        DocumentInput(
            text=(
                "Roshan is the major neutral objective near the river. "
                "Roshan can drop Aegis of the Immortal and later additional rewards, "
                "so teams often fight around Roshan timing and vision."
            ),
            metadata=SourceMetadata(
                source_url="seed://objectives/roshan",
                source_name="Seed: Roshan",
                patch_version="7.36",
                entity_type="objective",
                entity_name="Roshan",
                updated_at="2026-06-18",
            ),
        ),
        DocumentInput(
            text=(
                "Blink Dagger gives instant repositioning over a short distance. "
                "It is commonly used to initiate fights, escape before taking damage, "
                "or reach high-value targets."
            ),
            metadata=SourceMetadata(
                source_url="seed://items/blink-dagger",
                source_name="Seed: Blink Dagger",
                patch_version="7.36",
                entity_type="item",
                entity_name="Blink Dagger",
                updated_at="2026-06-18",
            ),
        ),
    ]
