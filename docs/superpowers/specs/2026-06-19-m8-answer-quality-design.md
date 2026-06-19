# M8 Answer Quality And Alias Design

Date: 2026-06-19

## Goal

Improve the first demo's answer quality without adding new data sources or a larger UI surface. M8 should make common Dota 2 questions work better when the user mixes Chinese, English, abbreviations, and player slang.

The assistant should answer in Chinese by default, preserve important English Dota terms, and make its limits clear when local knowledge or local stats do not cover the question.

## Current Context

The project already has:

- A FastAPI chat endpoint with question classification.
- Local vector retrieval over indexed Dota 2 documents.
- A prompt builder with answer structure rules.
- A structured OpenDota hero stats path.
- A React demo UI with example questions and refresh controls.

Current weak spots:

- Alias matching is mostly implicit. Questions like `斧王胜率`, `黑皇杖有什么用`, or `肉山掉什么` may not reliably map to `Axe`, `Black King Bar / BKB`, or `Roshan`.
- Question classification is based on small keyword lists and can miss mixed-language questions.
- Stats answers and RAG answers have different shapes.
- The project has tests for mechanics, but not a visible golden-question quality suite.

## Scope

M8 will add a small answer-quality layer around the existing RAG pipeline:

- Static alias definitions for common demo terms.
- Query normalization that preserves the original user question while adding canonical terms for classification, retrieval, and stats lookup.
- More robust classification for Chinese, English, abbreviations, and slang.
- A consistent answer contract for knowledge, patch, advice, and stats answers.
- Golden-question tests that protect the demo path.

Initial alias coverage should focus on the demo and core Dota concepts:

- Heroes: `Axe`, `斧王`.
- Items and mechanics: `BKB`, `Black King Bar`, `黑皇杖`; `Blink Dagger`, `跳刀`.
- Objectives: `Roshan`, `肉山`.
- Stats terms: `胜率`, `win rate`, `pick rate`, `ban rate`, `meta`, `热门`.
- Advice terms: `怎么用`, `怎么出`, `counter`, `克制`, `对线`, `团战`.

This is intentionally small. The design should make later alias expansion easy, but M8 should not attempt a complete Dota encyclopedia.

## Non-Goals

M8 will not:

- Add item trend ingestion.
- Add new external data providers.
- Scrape more official pages.
- Add frontend charts or a new dashboard.
- Add cloud models.
- Guarantee perfect Chinese localization for every hero, item, or ability.
- Replace the local model with hand-written answers for all questions.

## User Experience

Example questions should become more reliable:

- `BKB有什么用？`
- `What does BKB do?`
- `黑皇杖什么时候出？`
- `Roshan 会掉什么？`
- `肉山掉什么？`
- `Axe win rate meta`
- `斧王胜率`
- `Blink Dagger怎么用？`
- `跳刀怎么用？`

For text-backed answers, the assistant should keep the existing source behavior and make the answer shape predictable:

- `直接结论`
- `关键原因`
- `建议/注意`
- `相关术语`
- `来源/数据新鲜度`

For stats-backed answers, the assistant should answer from SQLite without calling the generator when a matching hero is found. The answer should include the canonical hero name, win rate, pick share, sample count, refresh timestamp, and a caution that OpenDota public-match data is sample-based and not real-time global Meta.

If coverage is missing, the assistant should say that the local knowledge base or local stats do not cover the question, rather than guessing.

## Backend Design

### Alias Registry

Add a small alias module under `backend/app/rag/`, for example `aliases.py`.

Responsibilities:

- Store canonical terms and aliases in one place.
- Normalize a question into:
  - original text,
  - expanded text for retrieval and classification,
  - canonical hero name when detected,
  - canonical terms detected for prompt hints.
- Keep matching deterministic and testable.

The initial implementation can use simple case-insensitive substring matching. Word-boundary behavior should be used for short English aliases where appropriate, so a short alias does not accidentally match unrelated words.

### Classification

Update `classify_question` to classify against expanded text, not only the raw question.

Rules:

- Patch signals still win first for patch questions.
- Stats signals should catch `胜率`, `win rate`, `pick rate`, `ban rate`, `meta`, and `热门`.
- Advice signals should catch Chinese and English usage/counter wording.
- If no stronger signal exists, fall back to `knowledge`.

This keeps the current categories: `knowledge`, `patch`, `stats`, `advice`.

### Retrieval

Use expanded query text for embeddings. The original question should still be passed to the final prompt so the model responds to what the user asked.

Example:

```text
original: 黑皇杖有什么用？
expanded: 黑皇杖有什么用？ Black King Bar BKB spell immunity
```

The exact expansion can stay conservative. Its purpose is to improve retrieval hit rate, not to inject unsupported facts.

### Stats Lookup

Use canonical hero detection before repository lookup.

Example:

```text
question: 斧王胜率
canonical hero: Axe
repository lookup: Axe
```

If no canonical hero is detected, keep the existing fallback that returns the top local heroes when stats exist.

### Prompt Builder

Keep `build_prompt` focused, but make the answer contract clearer:

- Chinese answer by default.
- Preserve English terms such as `Black King Bar / BKB`, `Roshan`, `Blink Dagger`, and hero names.
- Use the five expected sections.
- Cite source metadata from the supplied context.
- Avoid absolute advice such as "must buy" or "always pick".
- Say local coverage is missing when context is insufficient.

The prompt may receive canonical term hints from the alias layer, but it should not turn those hints into unsupported claims.

## Testing Design

Add or expand backend tests for:

- Alias normalization:
  - `黑皇杖` detects `Black King Bar / BKB`.
  - `肉山` detects `Roshan`.
  - `斧王` detects `Axe`.
  - `跳刀` detects `Blink Dagger`.
- Classification:
  - `斧王胜率` is `stats`.
  - `Axe win rate meta` is `stats`.
  - `跳刀怎么用` is `advice`.
  - `肉山掉什么` is `knowledge`.
- Prompt construction:
  - The prompt includes the five answer sections.
  - The prompt preserves canonical English terms.
  - Advice prompts include the no-absolute-claims rule.
- Chat service stats path:
  - A Chinese hero alias can produce an `Axe` stats answer when local stats exist.
  - Missing stats still returns the existing local-data-missing message.
- Golden questions:
  - A small parameterized test suite covers the demo questions and expected route or answer properties.

Frontend changes are not required for M8. Existing frontend tests and build should still pass.

## Acceptance Criteria

M8 is complete when:

- Common Chinese/English aliases improve classification, retrieval input, and stats lookup.
- The existing demo questions still work.
- `斧王胜率` can resolve to the local `Axe` stats row when stats data exists.
- RAG prompts enforce the expected Chinese answer shape and source/freshness behavior.
- Golden-question tests cover at least the listed demo questions.
- Backend tests pass.
- Frontend tests and build pass if any frontend code is touched.

## Risks And Mitigations

- Alias matching can create false positives. Mitigation: keep the initial alias list small and add tests for each alias.
- Query expansion can bias retrieval. Mitigation: expand only with canonical names and known synonyms, not long explanations.
- Answer formatting can become rigid. Mitigation: require section names but allow concise content inside each section.
- Stats data may be missing locally. Mitigation: keep the explicit missing-data answer and debug flag behavior.

## Implementation Notes

The implementation should be test-driven. Start with alias and classification tests, then wire query normalization into chat service and prompt building.

Keep the work scoped to the backend unless tests reveal that the demo UI needs a small display adjustment.
