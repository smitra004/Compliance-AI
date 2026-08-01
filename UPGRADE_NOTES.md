# UPGRADE_NOTES.md — technologies & features added

This pass adds the requested tech stack and demo features on top of the
existing ComplianceAI prototype, without touching its core scan pipeline
logic. Same philosophy as the original project: everything has a working
zero-config fallback, so `docker compose up --build` still runs with no
credentials.

## Already present before this update (verified, not re-built)
- Drag-and-drop upload (`AppFull.jsx` Scan view)
- Live AI reasoning stream (SSE "Multi-Agent Council" logs, `MultiAgentConsole`)
- Animated processing feedback (scanline + live log stream while a scan runs)
- One-click PDF audit report (`GET /api/scan/{id}/pdf`, download buttons in Reports/Audit)
- Before/after compliance comparison (Playground view: `originalScore` vs `simulatedScore`)
- RBAC (`X-Role` header, four roles)
- Docker (`docker-compose.yml`, per-service Dockerfiles)

## Added this pass

### Backend — technologies
| Tech | File(s) | Status |
|---|---|---|
| **LangGraph** | `app/pipeline/langgraph_orchestrator.py` | Real `StateGraph` (parse → council → seal). Switch on with `ORCHESTRATOR_ENGINE=langgraph`; default stays `native` (original hand-rolled pipeline). Same `ScanRecord` output either way. |
| **CrewAI** | `app/pipeline/crew.py` | Real `Agent`/`Task`/`Crew` (Risk Assessor + Remediation Advisor) that synthesizes an executive summary from a completed scan's violations. Falls back to a deterministic templated summary when no LLM key is set. Exposed at `GET /api/scan/{id}/crew-analysis`. |
| **Azure OpenAI** | `app/azure_clients.py` (`get_azure_chat_client`), `app/config.py` | Drop-in `AzureChatOpenAI` client, active when `AZURE_OPENAI_KEY` + `AZURE_OPENAI_ENDPOINT` are set. |
| **Azure AI Search** | `app/azure_clients.py` (`AzureAISearchClient`) | Alternative retrieval backend to ChromaDB — same grounded-citation contract. Active when `AZURE_SEARCH_ENDPOINT`/`KEY` are set. |
| **Microsoft Purview** | `app/azure_clients.py` (`PurviewClient`) | Document sensitivity classification via the Purview REST API when configured; otherwise a local heuristic (reuses the existing PII/secret regex patterns) so the field is never blank. Exposed at `GET /api/scan/{id}/classification`. |
| **PostgreSQL** | `app/db_pg.py` | Optional durable mirror of the audit log + scan records via SQLAlchemy, for multi-replica deployments. SQLite (`db.py`) remains the source of truth and zero-config default. Active when `DATABASE_URL` is set. |
| **Redis** | `app/cache.py` | Caches `/api/scan/{id}/crew-analysis` responses (and anything else that opts in). Falls back to an in-process dict when `REDIS_URL` is unset or unreachable. |
| **Docker** | `docker-compose.yml` | Expanded: backend, frontend, **postgres, redis, keycloak** (profile `auth`), **prometheus, grafana** (profile `observability`). |
| **Kubernetes** | `k8s/*.yaml` | Namespace, ConfigMap, Secret template, Postgres StatefulSet, Redis/Keycloak Deployments, backend Deployment+HPA (3–10 replicas), frontend Deployment, Ingress (with SSE/WebSocket timeouts), Prometheus+Grafana. |
| **CI/CD (GitHub Actions)** | `.github/workflows/ci-cd.yml` | Lint + import check + tests → frontend build → Docker build/push to GHCR → `kubectl` rollout, gated on `main`. |
| **JWT + RBAC** | `app/auth.py`, `app/rbac.py` | JWT verification layered onto the existing header-based RBAC (backward compatible). Two modes: OIDC (Keycloak/Auth0 JWKS validation) when `OIDC_ISSUER` is set, otherwise locally-signed dev tokens via `POST /api/auth/token`. `GET /api/auth/me` decodes the current token. |
| **Prometheus + Grafana** | `app/metrics.py`, `monitoring/` | `/metrics` endpoint (scan count, violation count by severity/regulation, scan duration histogram, remediation count, auth failures). Grafana auto-provisioned with a starter dashboard. |
| **Keycloak / Auth0** | `docker-compose.yml`, `k8s/12-keycloak.yaml`, `app/auth.py` | Keycloak ships as an optional compose/k8s service; `app/auth.py`'s OIDC path works against either Keycloak or Auth0 (JWKS URL is auto-derived from the issuer, or set `OIDC_JWKS_URL` explicitly). |

### Frontend — features
| Feature | File(s) | Status |
|---|---|---|
| **Voice interaction** | `src/components/VoiceControl.jsx` | Web Speech API. Say "Analyze this document" / "Scan document" to trigger a scan, "clear"/"reset" to reset the view. Wired into the Scan view below the sample-template buttons. No external API — works offline in demo mode. Hides itself in browsers without `SpeechRecognition` support. |
| **Dark/light mode** | `AppFull.jsx` (`ThemeToggle`, `DARK_PALETTE`), `theme.css` | Toggle button in the top header. The app's `CAP` palette object is mutated in place and the tree re-rendered, so it applies across the whole 4000+ line app without threading a theme prop everywhere. Persists via `localStorage`. |
| **Real-time notifications** | `app/notifications.py` (backend), `src/components/NotificationCenter.jsx` (frontend) | WebSocket at `/ws/notifications`. Backend broadcasts on scan completion and remediation. Frontend bell icon in the header shows unread count, auto-reconnects, and lists recent activity. |

## Endpoints added
```
POST /api/auth/token              issue a dev JWT (user, role)
GET  /api/auth/me                 decode current bearer token
GET  /api/integrations/status     which of Azure/Postgres/Redis/OIDC/Prometheus are live
GET  /api/scan/{id}/crew-analysis CrewAI executive summary (cached in Redis)
GET  /api/scan/{id}/classification Purview sensitivity classification
WS   /ws/notifications            real-time event stream
GET  /metrics                     Prometheus scrape target
```

## What still needs your credentials to go from "wired" to "live"
Everything above degrades gracefully without config, per the project's
existing DEMO_MODE pattern — but to actually exercise the Azure/Purview/
Keycloak paths in a demo, you'll need to fill in `backend/.env` (see
`backend/.env.example`) or the equivalent `k8s/02-secrets.yaml` values:
Azure OpenAI/Search keys, a Purview service principal, and either a
Keycloak realm or Auth0 tenant if you want real OIDC login instead of the
dev-token endpoint.

## Running it
```bash
# Full stack incl. Postgres/Redis (Keycloak/Prometheus/Grafana are optional profiles):
docker compose --profile auth --profile observability up --build

# Or locally, same as before:
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```

Kubernetes: `kubectl apply -f k8s/` (build/push your own image tags first,
or let the GitHub Actions workflow do it on push to `main`).
