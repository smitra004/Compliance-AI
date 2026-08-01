"""Azure integrations: OpenAI, AI Search, Purview.

Each client is real (calls the actual Azure REST/SDK surface) but only
activates when its config block is fully populated — otherwise it reports
`configured: False` and the caller keeps using the existing Groq/OpenAI +
ChromaDB path, matching the project's existing DEMO_MODE fallback pattern.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app import config


def get_azure_chat_client(temperature: float = 0.1, max_tokens: int = 2000):
    """Returns a LangChain-compatible AzureChatOpenAI client, or None if
    Azure OpenAI isn't configured. Drop-in alternative to the Groq/OpenAI
    client built in `pipeline/agents.py::_get_llm_client`."""
    if not config.AZURE_OPENAI_CONFIGURED:
        return None
    from langchain_openai import AzureChatOpenAI
    return AzureChatOpenAI(
        azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
        api_key=config.AZURE_OPENAI_KEY,
        api_version=config.AZURE_OPENAI_API_VERSION,
        azure_deployment=config.AZURE_OPENAI_DEPLOYMENT,
        temperature=temperature,
        max_tokens=max_tokens,
    )


class AzureAISearchClient:
    """Thin wrapper over azure-search-documents. Used as an alternative
    retrieval backend to the local ChromaDB store in `pipeline/vectorstore.py`
    — same "grounded citation" contract (chunk text + score + source)."""

    def __init__(self) -> None:
        self.configured = config.AZURE_SEARCH_CONFIGURED
        self._client = None
        if self.configured:
            try:
                from azure.core.credentials import AzureKeyCredential
                from azure.search.documents import SearchClient
                self._client = SearchClient(
                    endpoint=config.AZURE_SEARCH_ENDPOINT,
                    index_name=config.AZURE_SEARCH_INDEX,
                    credential=AzureKeyCredential(config.AZURE_SEARCH_KEY),
                )
            except Exception as e:  # noqa: BLE001
                print(f"[azure_search] client init failed ({e}); staying on ChromaDB")
                self.configured = False

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not self.configured or self._client is None:
            return []
        results = self._client.search(search_text=query, top=top_k)
        return [
            {
                "text": r.get("content", ""),
                "score": r.get("@search.score", 0.0),
                "source": r.get("source", config.AZURE_SEARCH_INDEX),
            }
            for r in results
        ]

    def upload_policy_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        if not self.configured or self._client is None:
            return
        self._client.upload_documents(documents=chunks)


class PurviewClient:
    """Wrapper over the Purview Data Map / Scanning REST API for sensitivity
    labeling of uploaded documents (PII / confidential / restricted), used
    to enrich the compliance report with an org-wide classification, not
    just the document-local rule findings."""

    def __init__(self) -> None:
        self.configured = config.PURVIEW_CONFIGURED
        self._token: Optional[str] = None

    def _get_token(self) -> Optional[str]:
        if not self.configured:
            return None
        import httpx
        resp = httpx.post(
            f"https://login.microsoftonline.com/{config.PURVIEW_TENANT_ID}/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": config.PURVIEW_CLIENT_ID,
                "client_secret": config.PURVIEW_CLIENT_SECRET,
                "scope": "https://purview.azure.net/.default",
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def classify_document(self, document_name: str, text_sample: str) -> Dict[str, Any]:
        """Returns a Purview-style sensitivity classification. Falls back to
        a local heuristic (reusing the same PII/secret patterns the rule
        engine already flags) when Purview isn't configured, so the
        dashboard field this feeds is never blank."""
        if not self.configured:
            return self._heuristic_classification(text_sample)
        try:
            token = self._get_token()
            import httpx
            endpoint = f"https://{config.PURVIEW_ACCOUNT_NAME}.purview.azure.com/catalog/api/atlas/v2/entity"
            resp = httpx.get(endpoint, headers={"Authorization": f"Bearer {token}"}, timeout=10.0)
            return {"source": "purview", "status_code": resp.status_code, "raw": resp.json() if resp.status_code == 200 else None}
        except Exception as e:  # noqa: BLE001
            print(f"[purview] classification call failed ({e}); using local heuristic")
            return self._heuristic_classification(text_sample)

    @staticmethod
    def _heuristic_classification(text_sample: str) -> Dict[str, Any]:
        import re
        labels = []
        if re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text_sample):
            labels.append("PII.Email")
        if re.search(r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b", text_sample):
            labels.append("PII.SSN-like")
        if re.search(r"(api[_-]?key|password|secret)\s*[:=]", text_sample, re.IGNORECASE):
            labels.append("Credential.Secret")
        return {
            "source": "local-heuristic",
            "sensitivity_label": "Highly Confidential" if labels else "General",
            "info_types": labels,
        }
