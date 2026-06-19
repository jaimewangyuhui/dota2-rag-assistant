# Dota 2 RAG Assistant Demo Checklist

Date: 2026-06-19

## Local Services

- Backend: `http://127.0.0.1:8000/api/health`
- Frontend: `http://127.0.0.1:5173/`
- Ollama: local Docker or host service

## Browser Smoke Test

1. Open the frontend.
2. Confirm service health loads.
3. Click `Refresh Knowledge`.
4. Confirm a success message such as `documents`, `chunks`, and `sources`.
5. Ask `What does BKB do?`.
6. Confirm the answer appears with sources.
7. Ask `Axe win rate meta` after local stats are available.
8. Confirm the answer includes `Axe`, a win rate, a pick share, and an OpenDota caveat.
9. Trigger `Refresh Stats` when OpenDota/network is unavailable.
10. Confirm the UI shows `Stats refresh failed. Check OpenDota/network and retry.` without clearing the chat input.
11. Click the example question `What does BKB do?`.
12. Confirm it fills the input without sending automatically.

## Demo Questions

- `BKB有什么用？`
- `What does BKB do?`
- `Roshan 会掉什么？`
- `肉山掉什么？`
- `黑皇杖什么时候出？`
- `Blink Dagger怎么用？`
- `跳刀怎么用？`
- `Axe win rate meta`
- `斧王胜率`
- `7.36 BKB 改了什么？`
- `最近版本 Roshan 有什么变化？`
- `Chen 的神杖效果是什么？`

## Expected Behavior

- Text-backed answers should include sources.
- Stats answers should include sample scope, refresh timestamp, and an OpenDota caveat.
- Unsupported questions should say the local knowledge base does not cover the question.
- The assistant should answer in Chinese while preserving important English Dota 2 terms.
