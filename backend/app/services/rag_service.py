"""
RAG Service — In-memory keyword-based retrieval for regulatory templates.

Stores and retrieves:
- Regulatory guidance documents (FinCEN, FIU-IND, FATF)
- SAR narrative templates
- Typology reference documents

Usage rules:
- Retrieved content is for structural guidance ONLY
- Never copy prior SAR text verbatim
- Document identifiers must be logged in audit JSON
- Retrieved content cannot override case-specific data
"""

import math
import re
from typing import List, Dict, Optional
from collections import Counter


class RAGService:
    """
    Lightweight Retrieval-Augmented Generation service using TF-IDF similarity.
    No external vector-store dependency (replaces ChromaDB).
    """

    def __init__(self):
        self._documents: Dict[str, Dict] = {}  # id -> {text, metadata}
        self._idf: Dict[str, float] = {}
        self._tfidf_vectors: Dict[str, Dict[str, float]] = {}
        self._dirty = True  # rebuild index flag

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Split text into lowercase tokens."""
        return re.findall(r"[a-z0-9]+", text.lower())

    def _rebuild_index(self):
        """Recompute IDF and per-document TF-IDF vectors."""
        n_docs = len(self._documents)
        if n_docs == 0:
            self._idf = {}
            self._tfidf_vectors = {}
            self._dirty = False
            return

        # Document frequency
        df: Dict[str, int] = Counter()
        doc_tfs: Dict[str, Counter] = {}
        for doc_id, doc in self._documents.items():
            tokens = self._tokenize(doc["text"])
            tf = Counter(tokens)
            doc_tfs[doc_id] = tf
            for term in set(tokens):
                df[term] += 1

        # IDF = log(N / df)
        self._idf = {term: math.log((n_docs + 1) / (freq + 1)) + 1 for term, freq in df.items()}

        # TF-IDF vectors
        self._tfidf_vectors = {}
        for doc_id, tf in doc_tfs.items():
            total = sum(tf.values()) or 1
            vec = {}
            for term, count in tf.items():
                vec[term] = (count / total) * self._idf.get(term, 0)
            self._tfidf_vectors[doc_id] = vec

        self._dirty = False

    @staticmethod
    def _cosine_sim(a: Dict[str, float], b: Dict[str, float]) -> float:
        """Compute cosine similarity between two sparse vectors."""
        common = set(a.keys()) & set(b.keys())
        if not common:
            return 0.0
        dot = sum(a[k] * b[k] for k in common)
        mag_a = math.sqrt(sum(v * v for v in a.values()))
        mag_b = math.sqrt(sum(v * v for v in b.values()))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    def add_document(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Add a regulatory document to the in-memory store."""
        self._documents[doc_id] = {"text": text, "metadata": metadata or {}}
        self._dirty = True
        return True

    def retrieve_guidance(
        self,
        query: str,
        n_results: int = 3,
    ) -> List[Dict]:
        """
        Retrieve the most relevant regulatory documents for *query*.
        Returns list of {document_id, text, metadata} sorted by relevance.
        """
        if not self._documents:
            return []

        if self._dirty:
            self._rebuild_index()

        # Build query TF-IDF vector using the corpus IDF
        tokens = self._tokenize(query)
        if not tokens:
            return []
        tf = Counter(tokens)
        total = sum(tf.values()) or 1
        q_vec = {term: (count / total) * self._idf.get(term, 1.0) for term, count in tf.items()}

        # Score every document
        scores = []
        for doc_id, d_vec in self._tfidf_vectors.items():
            sim = self._cosine_sim(q_vec, d_vec)
            scores.append((sim, doc_id))

        scores.sort(reverse=True)

        results = []
        for sim, doc_id in scores[:n_results]:
            if sim <= 0:
                break
            doc = self._documents[doc_id]
            results.append({
                "document_id": doc_id,
                "text": doc["text"],
                "metadata": doc["metadata"],
            })

        return results

    def seed_default_templates(self) -> int:
        """
        Seed the store with default regulatory templates.
        Returns the number of documents seeded.
        """
        templates = [
            {
                "id": "FINCEN-SAR-STRUCTURE-001",
                "text": (
                    "SAR Narrative Structure per FinCEN guidance: "
                    "1. Subject Information - Include full name, DOB, SSN/TIN, address, account numbers. "
                    "2. Summary of Suspicious Activity - Concise overview of the suspicious activity. "
                    "3. Detailed Description - Chronological description of transactions and behavior. "
                    "4. Relationship to Other Subjects - Any connections to other suspicious parties. "
                    "5. Additional Information - Any other relevant details."
                ),
                "metadata": {"source": "FinCEN", "type": "template", "version": "2024"},
            },
            {
                "id": "FATF-TYPOLOGY-ML-001",
                "text": (
                    "FATF Money Laundering Typologies: "
                    "Structuring/Smurfing - Breaking large transactions into smaller ones below reporting thresholds. "
                    "Layering - Complex web of transfers to obscure the origin of funds. "
                    "Integration - Introducing laundered funds back into the legitimate economy. "
                    "Trade-Based ML - Manipulating trade transactions to transfer value. "
                    "Shell Companies - Using front companies with no legitimate business purpose."
                ),
                "metadata": {"source": "FATF", "type": "typology", "version": "2024"},
            },
            {
                "id": "FIUIND-STR-GUIDANCE-001",
                "text": (
                    "FIU-IND Suspicious Transaction Report Guidelines: "
                    "Report transactions that give rise to reasonable ground of suspicion. "
                    "Include nature of transaction, amount, parties involved, reasons for suspicion. "
                    "Cross-border wire transfers above threshold must be reported. "
                    "Cash transactions above INR 10 lakh require CTR filing."
                ),
                "metadata": {"source": "FIU-IND", "type": "guidance", "version": "2024"},
            },
            {
                "id": "AML-RED-FLAGS-001",
                "text": (
                    "Common AML Red Flags: "
                    "Rapid movement of funds - Funds deposited and quickly transferred out. "
                    "Round dollar amounts - Transactions in even amounts suggesting structuring. "
                    "High-risk jurisdictions - Transactions involving sanctioned or high-risk countries. "
                    "Unusual business pattern - Activity inconsistent with stated business purpose. "
                    "Velocity spikes - Sudden increase in transaction frequency or volume."
                ),
                "metadata": {"source": "Industry", "type": "red_flags", "version": "2024"},
            },
        ]

        count = 0
        for template in templates:
            if self.add_document(template["id"], template["text"], template["metadata"]):
                count += 1
        return count


# Singleton instance
rag_service = RAGService()

# Auto-seed on import so templates are always available
rag_service.seed_default_templates()
