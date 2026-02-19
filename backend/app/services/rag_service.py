"""
RAG Service — ChromaDB integration for regulatory template retrieval.

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

import os
from typing import List, Dict, Optional

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

from app.config import settings


class RAGService:
    """
    Retrieval-Augmented Generation service using ChromaDB.
    Provides regulatory context to the SAR generation engine.
    """

    def __init__(self):
        self._client = None
        self._collection = None

    def _get_client(self):
        """Lazy initialization of ChromaDB client."""
        if not CHROMA_AVAILABLE:
            return None
        if self._client is None:
            self._client = chromadb.Client(ChromaSettings(
                anonymized_telemetry=False,
            ))
        return self._client

    def _get_collection(self):
        """Get or create the regulatory documents collection."""
        client = self._get_client()
        if client is None:
            return None
        if self._collection is None:
            self._collection = client.get_or_create_collection(
                name="regulatory_documents",
                metadata={"description": "SAR templates and regulatory guidance"}
            )
        return self._collection

    def add_document(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Add a regulatory document to the vector store.
        
        Args:
            doc_id: Unique document identifier (e.g., "FINCEN-SAR-TEMPLATE-001")
            text: Document text content
            metadata: Additional metadata (source, date, type)
        """
        collection = self._get_collection()
        if collection is None:
            return False

        collection.add(
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata or {}],
        )
        return True

    def retrieve_guidance(
        self,
        query: str,
        n_results: int = 3,
    ) -> List[Dict]:
        """
        Retrieve relevant regulatory guidance for a given query.
        
        Returns list of documents with their IDs and metadata.
        All retrieved document IDs must be logged in the audit trail.
        """
        collection = self._get_collection()
        if collection is None:
            return []

        try:
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
            )
        except Exception:
            return []

        documents = []
        if results and results.get("ids"):
            for i, doc_id in enumerate(results["ids"][0]):
                documents.append({
                    "document_id": doc_id,
                    "text": results["documents"][0][i] if results.get("documents") else "",
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                })
        return documents

    def seed_default_templates(self) -> int:
        """
        Seed the vector store with default regulatory templates.
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
