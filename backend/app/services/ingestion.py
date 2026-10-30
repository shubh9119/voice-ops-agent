"""Document ingestion pipeline: fetch → chunk → embed → store."""

import hashlib
import asyncio
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings
from app.models.schemas import DocumentInput
from app.services.embeddings import EmbeddingService
from app.services.vectorstore import VectorStoreService

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    HAS_SPLITTER = True
except ImportError:
    HAS_SPLITTER = False


def _fallback_recursive_split(
    text: str,
    chunk_size: int = 400,
    chunk_overlap: int = 50,
) -> list[str]:
    """Fallback recursive text splitter matching LangChain behavior."""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        if end < text_len:
            # Try to break at paragraph, line, period, or space
            split_at = -1
            for sep in ["\n\n", "\n", ". ", " "]:
                idx = text.rfind(sep, start, end)
                if idx > start:
                    split_at = idx + len(sep)
                    break
            if split_at > start:
                end = split_at

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_len:
            break
        start = max(end - chunk_overlap, start + 1)

    return chunks


class IngestionService:
    """Handles the full ingestion pipeline for documents.

    Pipeline:
    1. Fetch (URL) or accept raw text
    2. Compute stable doc_id (SHA-256)
    3. Split into chunks (RecursiveCharacterTextSplitter 400/50)
    4. Attach metadata (tenant_id, doc_id, chunk_index, source, brand)
    5. Embed and upsert into vector store
    """

    def __init__(self):
        settings = get_settings()
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP

        if HAS_SPLITTER:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""],
            )
        else:
            self.text_splitter = None

        self.embedding_service = EmbeddingService.get_instance()
        self.vectorstore = VectorStoreService.get_instance()

    @staticmethod
    def compute_doc_id(url: Optional[str] = None, text: Optional[str] = None) -> str:
        """Compute a stable document ID using SHA-256."""
        content = url if url else text
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    async def fetch_url_content(self, url: str) -> str:
        """Fetch a web page and extract readable text."""
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "OmniboundBot/1.0"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()

        text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    def chunk_text(self, text: str) -> list[str]:
        """Split text into chunks of 400 chars with 50 overlap.

        Rationale:
        - 400 chars (~80-100 words) provides optimal semantic cohesion for LLM grading.
        - 50 char overlap ensures boundary sentences/facts are not severed.
        - Idempotent indexing via {doc_id}-{chunk_index}.
        """
        if self.text_splitter:
            chunks = self.text_splitter.split_text(text)
        else:
            chunks = _fallback_recursive_split(
                text, self.chunk_size, self.chunk_overlap
            )
        return [c for c in chunks if len(c.strip()) > 20]

    async def ingest_document(
        self,
        tenant_id: str,
        document: DocumentInput,
    ) -> int:
        if document.url:
            text = await self.fetch_url_content(document.url)
            source = document.url
        else:
            text = document.text
            source = document.source

        doc_id = self.compute_doc_id(url=document.url, text=document.text)
        chunks = self.chunk_text(text)
        if not chunks:
            return 0

        chunk_ids = [f"{doc_id}-{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "tenant_id": tenant_id,
                "doc_id": doc_id,
                "chunk_index": i,
                "source": source,
                "brand": document.brand,
            }
            for i in range(len(chunks))
        ]

        embeddings = await self.embedding_service.embed_texts(chunks)

        self.vectorstore.upsert_chunks(
            tenant_id=tenant_id,
            ids=chunk_ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )

        return len(chunks)

    async def ingest_documents(
        self,
        tenant_id: str,
        documents: list[DocumentInput],
    ) -> tuple[int, int]:
        tasks = [
            self.ingest_document(tenant_id, doc)
            for doc in documents
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        docs_stored = 0
        total_chunks = 0
        errors = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(f"Document {i}: {str(result)}")
            else:
                docs_stored += 1
                total_chunks += result

        if errors and docs_stored == 0:
            raise RuntimeError(f"All documents failed: {'; '.join(errors)}")

        return docs_stored, total_chunks
