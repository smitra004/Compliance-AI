# Changes for the Leadership Round — voice removed, ABAC added, login page added

Three targeted changes on top of the existing app, per the judging feedback.

## 1. Voice control removed
- Deleted `frontend/src/components/VoiceControl.jsx`.
- Removed its import and usage from `AppFull.jsx` (Scan view).

## 2. ABAC (Attribute-Based Access Control) added on top of RBAC
New module: `backend/app/abac.py`.

- Attributes carried per-user: `department`, `region`, `clearance_level`
  (public < internal < confidential < restricted), `business_unit`.
- Policies are keyed by regulation (the natural sensitivity boundary
  already in the data model):
  - GDPR → region ∈ {EU, Global}, clearance ≥ Confidential
  - Internal HR → department ∈ {HR, Legal, Executive}, clearance ≥ Confidential
  - SOX → department ∈ {Finance, Legal, Executive}, clearance ≥ Restricted
  - Internal Security → department ∈ {Security, IT, Executive}, clearance ≥ Confidential
  - ISO 27001 / Custom → clearance ≥ Internal
- Attributes are embedded in the JWT (`app/auth.py::issue_dev_token`),
  alongside the existing RBAC `role` claim — RBAC still gates *what* an
  action is allowed (upload/view/audit/manage); ABAC additionally gates
  *which* findings are visible once RBAC has already allowed `view`.
- Enforcement points:
  - `GET /api/scan/{id}` — violations the caller isn't cleared for are
    redacted (title/excerpt/explanation replaced, count + reasons
    returned in an `abac` field) instead of removed, so the audit trail
    stays complete.
  - `GET /api/scan/{id}/pdf` — returns `403` if the caller lacks
    clearance for the most sensitive regulation touched by the scan.
  - `GET /api/auth/attribute-options` — vocabulary for the frontend
    picker, so it can never drift from the policies above.
- Verified end-to-end with `TestClient`: a Public/Engineering/US viewer
  gets all findings redacted and a 403 on PDF export; an
  Executive/Global/Restricted admin sees everything.

## 3. Enterprise login page added
New component: `frontend/src/components/Login.jsx`.

- Company logo/brand header, email + password fields, an "SSO" row
  (Microsoft Entra ID / Google — demo buttons that issue a working dev
  token so the flow is end-to-end even without a configured IdP; wire
  `OIDC_ISSUER` in `backend/.env` for real SSO via Keycloak/Auth0).
- Role selector (RBAC) plus a collapsible ABAC section (department,
  region, clearance level).
- On submit, calls `POST /api/auth/token` and stores the returned JWT +
  role + attributes; `AppFull.jsx`'s `AppRoot` gates the whole app behind
  this until a token is present.
- The former demo-only role dropdown in the sidebar now re-issues the
  JWT on change (rather than just swapping a header) so role switches
  actually take effect against `require()` in `rbac.py`. ABAC attributes
  got the same live-reissue treatment, plus a "Sign out" button.
- The scan detail view now shows a banner listing how many findings were
  redacted and why, whenever the signed-in user's attributes don't meet
  a finding's policy.

## Try it
```bash
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```
Log in with any email/password (dev mode; not verified). Pick a low
clearance (e.g. Public / Engineering / US) vs a high one (Restricted /
Executive / Global) to see ABAC redact findings and block PDF export.
