# Update notes

Base project: your latest `policy-compliance-capgemini-v3` upload, kept
exactly as-is — backend untouched, entire frontend shell (App, views, theme,
nav, API layer) untouched.

Two things were swapped/added, both inside `frontend/src/AppFull.jsx`'s scan
results view, and both wired to real data that's already in scope there
(`scansList`, the current `result`) — nothing else in the app changed:

1. **Digital Twin — replaced.**
   `frontend/src/components/DigitalTwin.jsx` is now the 3D twin from
   `ComplianceAI-final-merged` (`components/Twin3D.tsx`), ported into plain
   JSX: regulations → clauses → findings → documents, built from the full
   `scans` list. Same libraries (`3d-force-graph` + `three-spritetext`),
   same orbit/zoom/click-to-focus behaviour, same node coloring
   (regulation/clause/violation/document) and same detail side-panel.

2. **Agent section — added, directly under the Digital Twin.**
   `frontend/src/components/AgentOrchestra.jsx` is new, ported from
   `ComplianceAI-final-merged`'s `routes/agents.tsx` ("The agents are
   thinking."): the orbiting agent diagram around a planner core, plus the
   live chain-of-thought reasoning trace with confidence pills, play/pause
   and replay controls. It's rendered right below the Digital Twin card in
   `AppFull.jsx`.

Both components are self-contained (own palette/data helpers) so they don't
depend on `theme.css` or any global — consistent with how the original
`DigitalTwin.jsx` was written.

## package.json
Added the two libraries the 3D twin needs:
```
"3d-force-graph": "^1.80.0",
"three-spritetext": "^1.10.0"
```
`package-lock.json` was removed so `npm install` regenerates it cleanly.

## Not included (regenerate locally)
- `frontend/node_modules` — run `npm install`.
- `backend/venv` and `backend/data/chroma` (vector index cache, ~144MB) —
  run `pip install -r requirements.txt`, then re-seed/re-ingest so the
  embeddings rebuild.

## Run
```
cd backend && python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload

cd ../frontend
npm install
npm run dev
```
