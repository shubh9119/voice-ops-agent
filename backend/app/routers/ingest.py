"""Document ingestion endpoint."""

import logging
import httpx
from fastapi import APIRouter, HTTPException, Path, Query

from app.models.schemas import IngestRequest, IngestResponse, ErrorResponse
from app.services.ingestion import IngestionService
from app.services.vectorstore import VectorStoreService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ingest"])


@router.post(
    "/tenants/{tenant_id}/ingest",
    response_model=IngestResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        502: {"model": ErrorResponse, "description": "URL fetch failed"},
    },
)
async def ingest_documents(
    tenant_id: str = Path(..., min_length=1, max_length=100, description="Tenant identifier"),
    body: IngestRequest = ...,
):
    """Ingest documents into a tenant's corpus.

    Accepts documents with either a URL (fetched automatically) or
    raw text. Each document is chunked, embedded, and stored in the
    tenant's vector namespace.

    Idempotent: re-ingesting the same document overwrites its chunks
    rather than creating duplicates.
    """
    try:
        service = IngestionService()
        docs_stored, chunks_stored = await service.ingest_documents(
            tenant_id=tenant_id,
            documents=body.documents,
        )

        logger.info(
            f"Tenant '{tenant_id}': ingested {docs_stored} docs, {chunks_stored} chunks"
        )

        return IngestResponse(
            documents_stored=docs_stored,
            chunks_stored=chunks_stored,
        )

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch URL: {str(e)}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception(f"Ingestion failed for tenant '{tenant_id}'")
        raise HTTPException(status_code=500, detail=f"Ingestion error: {str(e)}")


@router.get("/tenants/{tenant_id}/stats")
async def get_tenant_stats(
    tenant_id: str = Path(..., min_length=1, max_length=100),
):
    """Get stored vector count for a tenant."""
    vs = VectorStoreService.get_instance()
    count = vs.collection_count(tenant_id)
    return {
        "tenant_id": tenant_id,
        "total_chunks": count,
    }


@router.get("/tenants/{tenant_id}/chunks")
async def get_tenant_chunks(
    tenant_id: str = Path(..., min_length=1, max_length=100),
    limit: int = Query(50, ge=1, le=100),
):
    """Retrieve indexed chunks for inspection and knowledge base view."""
    vs = VectorStoreService.get_instance()
    chunks = vs.get_chunks(tenant_id, limit=limit)
    return {
        "tenant_id": tenant_id,
        "total_chunks": vs.collection_count(tenant_id),
        "chunks": chunks,
    }


@router.delete("/tenants/{tenant_id}")
async def reset_tenant_data(
    tenant_id: str = Path(..., min_length=1, max_length=100),
):
    """Reset / clear all indexed vectors for a tenant."""
    vs = VectorStoreService.get_instance()
    vs.delete_collection(tenant_id)
    return {
        "tenant_id": tenant_id,
        "message": f"All data for tenant '{tenant_id}' cleared.",
    }
