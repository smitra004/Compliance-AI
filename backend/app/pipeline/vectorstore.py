"""RAG vector store backed by ChromaDB.

Policies are ingested into per-tenant, per-regulation collections with
metadata. Retrieval is scoped to the tenant and returns the policy chunk
plus a similarity score used as the RAG grounding signal.

Falls back to a lightweight in-memory TF-IDF store if ChromaDB or its
embedding model cannot be loaded, so the pipeline always runs.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

from app import config
from app.models import PolicyCitation, Regulation


def _load_policy_blocks(path: Path):
    blocks = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("||")]
        if len(parts) != 4:
            continue
        clause, regulation, sev_weight, text = parts
        blocks.append(
            {
                "clause": clause,
                "regulation": regulation,
                "severity_weight": sev_weight,
                "text": text,
            }
        )
    return blocks


def _all_policy_blocks():
    blocks = []
    for f in sorted(config.POLICIES_DIR.glob("*.txt")):
        blocks.extend(_load_policy_blocks(f))
    return blocks


# --------------------------------------------------------------------------- #
# Lightweight fallback store (pure python, no downloads)                        #
# --------------------------------------------------------------------------- #
class _FallbackStore:
    def __init__(self, blocks):
        self.blocks = blocks
        self.vocab = {}
        self.doc_vecs = [self._vec(b["text"] + " " + b["clause"]) for b in blocks]

    def _tokens(self, text):
        return re.findall(r"[a-z0-9]+", text.lower())

    def _vec(self, text):
        counts = {}
        for t in self._tokens(text):
            self.vocab.setdefault(t, len(self.vocab))
            counts[t] = counts.get(t, 0) + 1
        return counts

    @staticmethod
    def _cos(a, b):
        common = set(a) & set(b)
        num = sum(a[t] * b[t] for t in common)
        da = sum(v * v for v in a.values()) ** 0.5
        db = sum(v * v for v in b.values()) ** 0.5
        return num / (da * db) if da and db else 0.0

    def query(self, text, n=3):
        q = self._vec(text)
        scored = sorted(
            ((self._cos(q, dv), b) for dv, b in zip(self.doc_vecs, self.blocks)),
            key=lambda x: x[0],
            reverse=True,
        )
        return scored[:n]


class VectorStore:
    def __init__(self):
        self.base_blocks = _all_policy_blocks()
        self.backend = "chromadb"
        self.client = None
        self.collections = {}  # tenant_id -> collection
        self._fallbacks = {}   # tenant_id -> _FallbackStore
        try:
            import chromadb
            self.client = chromadb.PersistentClient(path=config.CHROMA_DIR)
        except Exception as exc:
            print(f"[vectorstore] ChromaDB unavailable, using fallback: {exc}")
            self.backend = "tfidf-fallback"

    def _get_tenant_blocks(self, tenant_id: str):
        blocks = list(self.base_blocks)
        try:
            from app import db
            custom_policies = db.list_custom_policies(tenant_id=tenant_id)
            for cp in custom_policies:
                cp_id = cp["id"]
                rules = cp["rules"]
                for idx, rule in enumerate(rules):
                    clause = f"CUSTOM-{cp_id}-{idx+1}"
                    blocks.append({
                        "clause": clause,
                        "regulation": "custom",
                        "severity_weight": "P2",
                        "text": rule
                    })
        except Exception as e:
            print(f"[vectorstore] Error loading custom policies for {tenant_id}: {e}")
        return blocks

    def get_collection_or_fallback(self, tenant_id: str):
        if self.backend == "tfidf-fallback":
            if tenant_id not in self._fallbacks:
                self._fallbacks[tenant_id] = _FallbackStore(self._get_tenant_blocks(tenant_id))
            return None
            
        if tenant_id not in self.collections:
            name = f"policies_{tenant_id}"
            try:
                try:
                    self.client.delete_collection(name)
                except Exception:
                    pass
                blocks = self._get_tenant_blocks(tenant_id)
                col = self.client.create_collection(name=name)
                if blocks:
                    col.add(
                        ids=[f"pol_{i}" for i in range(len(blocks))],
                        documents=[b["text"] for b in blocks],
                        metadatas=[
                            {
                                "clause": b["clause"],
                                "regulation": b["regulation"],
                                "severity_weight": b["severity_weight"],
                            }
                            for b in blocks
                        ],
                    )
                self.collections[tenant_id] = col
            except Exception as e:
                print(f"[vectorstore] Error initializing collection for {tenant_id}: {e}")
                if tenant_id not in self._fallbacks:
                    self._fallbacks[tenant_id] = _FallbackStore(self._get_tenant_blocks(tenant_id))
                return None
                
        return self.collections[tenant_id]

    def add_custom_policy(self, tenant_id: str, cp_id: int, policy_name: str, rules: list[str]):
        if tenant_id in self.collections:
            del self.collections[tenant_id]
        if tenant_id in self._fallbacks:
            del self._fallbacks[tenant_id]
        self.get_collection_or_fallback(tenant_id)

    @property
    def min_similarity(self) -> float:
        # Calibrated to the embedding space actually in use. Real
        # transformer embeddings (chromadb) sit higher than TF-IDF.
        return config.GROUNDING_THRESHOLD if self.backend == "chromadb" else 0.06

    def retrieve(self, text: str, tenant_id: str = "acmecorp", n: int = 3) -> List[PolicyCitation]:
        citations: List[PolicyCitation] = []
        col = self.get_collection_or_fallback(tenant_id)
        if col is not None:
            res = col.query(query_texts=[text], n_results=n)
            metas = res["metadatas"][0]
            docs = res["documents"][0]
            dists = res.get("distances", [[0] * len(docs)])[0]
            for meta, doc, dist in zip(metas, docs, dists):
                sim = max(0.0, 1.0 - float(dist) / 2.0)  # cosine distance -> sim
                citations.append(
                    PolicyCitation(
                        regulation=Regulation(meta["regulation"]),
                        clause=meta["clause"],
                        text=doc,
                        similarity=round(sim, 3),
                    )
                )
        else:
            fb = self._fallbacks.get(tenant_id)
            if not fb:
                fb = _FallbackStore(self._get_tenant_blocks(tenant_id))
                self._fallbacks[tenant_id] = fb
            for sim, b in fb.query(text, n):
                citations.append(
                    PolicyCitation(
                        regulation=Regulation(b["regulation"]),
                        clause=b["clause"],
                        text=b["text"],
                        similarity=round(float(sim), 3),
                    )
                )
        return citations


_store: VectorStore | None = None


def get_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
