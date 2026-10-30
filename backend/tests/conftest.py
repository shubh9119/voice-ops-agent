"""Shared test fixtures for the Omnibound Brand Q&A Agent tests."""

import os
import sys
import shutil
import hashlib
import pytest
from unittest.mock import AsyncMock, patch

# Ensure backend app is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set required env vars BEFORE importing app modules
os.environ["GOOGLE_API_KEY"] = "test-key-not-real"
os.environ["CHROMA_PERSIST_DIR"] = "./test_chroma_data"

from fastapi.testclient import TestClient
from app.services.vectorstore import VectorStoreService
from app.services.embeddings import EmbeddingService
from app.services.llm import LLMService
from app.agents.qa_agent import reset_qa_graph


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    os.environ["GOOGLE_API_KEY"] = "test-key-not-real"
    os.environ["CHROMA_PERSIST_DIR"] = "./test_chroma_data"
    yield
    if os.path.exists("./test_chroma_data"):
        shutil.rmtree("./test_chroma_data", ignore_errors=True)


@pytest.fixture()
def clean_chroma():
    """Provide a clean vector store for each test."""
    test_dir = "./test_chroma_data"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)

    VectorStoreService.reset()
    EmbeddingService.reset()
    LLMService.reset()
    reset_qa_graph()

    yield

    VectorStoreService.reset()
    EmbeddingService.reset()
    LLMService.reset()
    reset_qa_graph()

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture()
def mock_embedding():
    """Mock the embedding service methods to return deterministic 768-dim vectors."""
    def fake_embed_texts(texts):
        vectors = []
        for text in texts:
            h = hashlib.md5(text.encode()).hexdigest()
            base = [int(h[j % len(h)], 16) / 15.0 for j in range(768)]
            vectors.append(base)
        return vectors

    def fake_embed_query(text):
        h = hashlib.md5(text.encode()).hexdigest()
        return [int(h[j % len(h)], 16) / 15.0 for j in range(768)]

    with patch.object(EmbeddingService, "embed_texts", new_callable=AsyncMock) as m_texts, \
         patch.object(EmbeddingService, "embed_query", new_callable=AsyncMock) as m_query:
        m_texts.side_effect = lambda texts: fake_embed_texts(texts)
        m_query.side_effect = lambda text: fake_embed_query(text)
        yield m_query


@pytest.fixture()
def mock_llm():
    """Mock the LLM service ainvoke method."""
    with patch.object(LLMService, "ainvoke", new_callable=AsyncMock) as m_ainvoke:
        m_ainvoke.return_value = "yes"
        yield m_ainvoke


@pytest.fixture()
def client(clean_chroma, mock_embedding, mock_llm):
    """FastAPI test client with all external services mocked."""
    from app.config import get_settings
    get_settings.cache_clear()

    from app.main import app
    return TestClient(app)
