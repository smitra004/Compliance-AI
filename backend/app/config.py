"""Runtime configuration. Demo mode is auto-detected: if no LLM key is
present, the system runs entirely on the deterministic rule engine plus
cached reasoning, so a live demo never depends on network or API keys."""
import os
import logging
from pathlib import Path

os.environ["ANONYMIZED_TELEMETRY"] = "False"
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)



BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file manually if it exists to ensure proper environment connectivity
env_path = BASE_DIR / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        # setdefault allows overriding via system variables if already set
        os.environ[k.strip()] = v.strip().strip('"').strip("'")

POLICIES_DIR = BASE_DIR / "policies"
DEMO_DOCS_DIR = BASE_DIR / "demo_docs"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CHROMA_DIR = str(DATA_DIR / "chroma")
DB_PATH = str(DATA_DIR / "audit.sqlite")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

# Demo mode = no real LLM available. Everything still works deterministically.
DEMO_MODE = not (OPENAI_API_KEY or AZURE_OPENAI_KEY or GROQ_API_KEY)

# ─── Azure OpenAI ───────────────────────────────────────────────────────────
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
AZURE_OPENAI_TRIAGE_DEPLOYMENT = os.getenv("AZURE_OPENAI_TRIAGE_DEPLOYMENT", "gpt-4o-mini")
AZURE_OPENAI_CONFIGURED = bool(AZURE_OPENAI_KEY and AZURE_OPENAI_ENDPOINT)

# ─── Azure AI Search (RAG over the policy corpus, alternative to Chroma) ────
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "").strip()
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY", "").strip()
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX", "compliance-policies")
AZURE_SEARCH_CONFIGURED = bool(AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY)

# ─── Microsoft Purview (data classification / sensitivity labeling) ────────
PURVIEW_ACCOUNT_NAME = os.getenv("PURVIEW_ACCOUNT_NAME", "").strip()
PURVIEW_TENANT_ID = os.getenv("PURVIEW_TENANT_ID", "").strip()
PURVIEW_CLIENT_ID = os.getenv("PURVIEW_CLIENT_ID", "").strip()
PURVIEW_CLIENT_SECRET = os.getenv("PURVIEW_CLIENT_SECRET", "").strip()
PURVIEW_CONFIGURED = bool(PURVIEW_ACCOUNT_NAME and PURVIEW_TENANT_ID and PURVIEW_CLIENT_ID and PURVIEW_CLIENT_SECRET)

# ─── PostgreSQL (durable, multi-instance audit store; SQLite remains the
# zero-config default so the demo never depends on an external DB) ─────────
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
POSTGRES_CONFIGURED = bool(DATABASE_URL)

# ─── Redis (response caching + rate limiting; falls back to an in-process
# dict cache when unavailable) ───────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "").strip()
REDIS_CONFIGURED = bool(REDIS_URL)

# ─── Auth: JWT + Keycloak / Auth0 (OIDC). Falls back to the existing
# X-Role header dev mode when no issuer is configured. ──────────────────────
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-insecure-secret-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
OIDC_ISSUER = os.getenv("OIDC_ISSUER", "").strip()
OIDC_AUDIENCE = os.getenv("OIDC_AUDIENCE", "").strip()
OIDC_JWKS_URL = os.getenv("OIDC_JWKS_URL", "").strip()
OIDC_ROLE_CLAIM = os.getenv("OIDC_ROLE_CLAIM", "realm_access.roles")
OIDC_CONFIGURED = bool(OIDC_ISSUER)

# ─── Email delivery (SMTP) — used for password reset. Same optional-
# integration pattern as everything else above: falls back to a clearly
# labeled demo/log-only mode when unset, rather than pretending to send. ───
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587") or "587")
SMTP_USER = os.getenv("SMTP_USER", "").strip()
# Gmail app passwords are displayed/copied with spaces (e.g. "abcd efgh ijkl mnop")
# for readability, but the real credential has no spaces in it. .strip() alone
# only removes leading/trailing whitespace, so a pasted-with-spaces password was
# silently failing SMTP auth (send_email() catches the exception and returns
# False rather than raising, so this failure was invisible to callers).
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").replace(" ", "").strip()
SMTP_FROM = os.getenv("SMTP_FROM", "").strip()
SMTP_CONFIGURED = bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)
# ─── Google OAuth ───────────────────────────────────────────────
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:8000/auth/google/callback",
).strip()

GOOGLE_CONFIGURED = bool(
    GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
)

# ─── Observability ──────────────────────────────────────────────────────────
PROMETHEUS_ENABLED = os.getenv("PROMETHEUS_ENABLED", "true").lower() != "false"

# ─── Orchestration engine ───────────────────────────────────────────────────
ORCHESTRATOR_ENGINE = os.getenv("ORCHESTRATOR_ENGINE", "native").strip().lower()
CREW_ANALYSIS_ENABLED = os.getenv("CREW_ANALYSIS_ENABLED", "true").lower() != "false"

TRIAGE_MODEL = os.getenv("TRIAGE_MODEL", "gpt-4o-mini")
ANALYSIS_MODEL = os.getenv("ANALYSIS_MODEL", "gpt-4o")

# RAG grounding threshold: the LLM may not make a compliance call unless a
# policy chunk is retrieved above this cosine similarity.
GROUNDING_THRESHOLD = float(os.getenv("GROUNDING_THRESHOLD", "0.35"))

DEFAULT_TENANT = "acmecorp"

REGULATION_PRECEDENCE = {
    "gdpr": 1,              # highest
    "iso27001": 2,
    "sox": 3,
    "internal_security": 4,
    "internal_hr": 5,       # lowest
}
print("OPENAI:", bool(OPENAI_API_KEY))
print("GROQ:", bool(GROQ_API_KEY))
print("TRIAGE_MODEL:", TRIAGE_MODEL)
print("ANALYSIS_MODEL:", ANALYSIS_MODEL)
print("DEMO_MODE:", DEMO_MODE)
print("AZURE_OPENAI_CONFIGURED:", AZURE_OPENAI_CONFIGURED)
print("AZURE_SEARCH_CONFIGURED:", AZURE_SEARCH_CONFIGURED)
print("PURVIEW_CONFIGURED:", PURVIEW_CONFIGURED)
print("POSTGRES_CONFIGURED:", POSTGRES_CONFIGURED)
print("REDIS_CONFIGURED:", REDIS_CONFIGURED)
print("OIDC_CONFIGURED:", OIDC_CONFIGURED)
print("ORCHESTRATOR_ENGINE:", ORCHESTRATOR_ENGINE)
print("GOOGLE_CONFIGURED:", GOOGLE_CONFIGURED)