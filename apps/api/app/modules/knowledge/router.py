import json
import uuid
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.config import settings
from app.db.session import SessionDep
from app.modules.accounts import service as accounts_service
from app.modules.knowledge import service
from app.modules.knowledge.enums import (
    Confidentiality,
    KnowledgeScope,
)
from app.modules.knowledge.models import (
    KnowledgeDocument,
    KnowledgeEvidenceCandidate,
    KnowledgeQuery,
)
from app.modules.knowledge.schemas import (
    EvidenceBoundaryResponse,
    EvidenceCandidateResponse,
    EvidenceCandidateReviewRequest,
    KnowledgeAnswerRequest,
    KnowledgeCitation,
    KnowledgeDocumentResponse,
    KnowledgeDocumentStatusRequest,
    KnowledgeQueryResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeWorkspaceResponse,
)

router = APIRouter(tags=["knowledge-rag"])


def _not_found(detail: str = "Knowledge resource not found") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _handle_error(exc: Exception) -> HTTPException:
    if isinstance(exc, accounts_service.AccountNotFoundError):
        return _not_found("Account not found")
    if isinstance(exc, service.KnowledgeNotFoundError):
        return _not_found()
    if isinstance(exc, service.ArchivedAccountError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Archived account is read-only"
        )
    if isinstance(exc, service.KnowledgeValidationError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        )
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


def _clean_optional(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value[:limit] or None


def _parse_metadata(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise service.KnowledgeValidationError("metadata_json must contain valid JSON") from exc
    if not isinstance(parsed, dict):
        raise service.KnowledgeValidationError("metadata_json must contain a JSON object")
    if len(json.dumps(parsed)) > 10_000:
        raise service.KnowledgeValidationError("metadata_json exceeds the 10 KB limit")
    return parsed


def document_response(document: KnowledgeDocument) -> KnowledgeDocumentResponse:
    return KnowledgeDocumentResponse(
        id=document.id,
        account_id=document.account_id,
        knowledge_scope=document.knowledge_scope,
        document_type=document.document_type,
        title=document.title,
        source_file=document.source_file,
        media_type=document.media_type,
        size_bytes=document.size_bytes,
        checksum_sha256=document.checksum_sha256,
        status=document.status,
        confidentiality=document.confidentiality,
        version=document.version,
        effective_date=document.effective_date,
        industry=document.industry,
        region=document.region,
        product=document.product,
        deployment_mode=document.deployment_mode,
        page_count=document.page_count,
        chunk_count=document.chunk_count,
        embedding_provider=document.embedding_provider,
        embedding_model=document.embedding_model,
        metadata=document.details,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def candidate_response(candidate: KnowledgeEvidenceCandidate) -> EvidenceCandidateResponse:
    return EvidenceCandidateResponse(
        id=candidate.id,
        citation_id=candidate.citation_id,
        knowledge_scope=candidate.knowledge_scope,
        source_file=candidate.source_file,
        document_title=candidate.document_title,
        document_version=candidate.document_version,
        page_number=candidate.page_number,
        section=candidate.section,
        excerpt=candidate.excerpt,
        retrieval_score=candidate.retrieval_score,
        rerank_score=candidate.rerank_score,
        metadata=candidate.metadata_snapshot,
        status=candidate.status,
        created_at=candidate.created_at,
    )


def query_response(query: KnowledgeQuery) -> KnowledgeQueryResponse:
    return KnowledgeQueryResponse(
        id=query.id,
        account_id=query.account_id,
        question=query.question,
        answer=query.answer,
        provider=query.provider,
        model=query.model,
        scopes=query.scopes,
        filters=query.filters,
        retrieval_metadata=query.retrieval_metadata,
        citations=[
            candidate_response(item)
            for item in sorted(
                query.candidates,
                key=lambda candidate: candidate.rerank_score,
                reverse=True,
            )
        ],
        created_at=query.created_at,
    )


@router.get(
    "/accounts/{account_id}/knowledge",
    response_model=KnowledgeWorkspaceResponse,
)
def get_workspace(account_id: uuid.UUID, session: SessionDep) -> KnowledgeWorkspaceResponse:
    try:
        documents = service.list_documents(session, account_id)
        queries = service.list_queries(session, account_id)
    except Exception as exc:
        raise _handle_error(exc) from exc
    return KnowledgeWorkspaceResponse(
        account_id=account_id,
        answer_provider=service.configured_answer_provider(),
        live_answer_available=bool(settings.openai_api_key),
        embedding_provider=service.configured_embedding_provider(),
        accepted_extensions=service.ACCEPTED_EXTENSIONS,
        max_upload_mb=settings.knowledge_max_upload_mb,
        accessible_scopes=[KnowledgeScope.ACCOUNT, KnowledgeScope.ENTERPRISE],
        documents=[document_response(item) for item in documents],
        recent_queries=[query_response(item) for item in queries],
    )


@router.post(
    "/accounts/{account_id}/knowledge/documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    account_id: uuid.UUID,
    session: SessionDep,
    file: Annotated[UploadFile, File()],
    knowledge_scope: Annotated[KnowledgeScope, Form()] = KnowledgeScope.ACCOUNT,
    document_type: Annotated[str, Form(max_length=80)] = "general",
    title: Annotated[str | None, Form(max_length=240)] = None,
    confidentiality: Annotated[Confidentiality, Form()] = Confidentiality.INTERNAL,
    effective_date: Annotated[date | None, Form()] = None,
    industry: Annotated[str | None, Form(max_length=120)] = None,
    region: Annotated[str | None, Form(max_length=120)] = None,
    product: Annotated[str | None, Form(max_length=160)] = None,
    deployment_mode: Annotated[str | None, Form(max_length=120)] = None,
    metadata_json: Annotated[str | None, Form(max_length=10_000)] = None,
) -> KnowledgeDocumentResponse:
    try:
        content = await file.read(settings.knowledge_max_upload_mb * 1024 * 1024 + 1)
        document = service.ingest_document(
            session,
            acting_account_id=account_id,
            content=content,
            filename=file.filename,
            media_type=file.content_type,
            scope=knowledge_scope,
            document_type=document_type,
            title=_clean_optional(title, 240),
            confidentiality=confidentiality,
            effective_date=effective_date,
            industry=_clean_optional(industry, 120),
            region=_clean_optional(region, 120),
            product=_clean_optional(product, 160),
            deployment_mode=_clean_optional(deployment_mode, 120),
            metadata=_parse_metadata(metadata_json),
        )
        return document_response(document)
    except Exception as exc:
        raise _handle_error(exc) from exc
    finally:
        await file.close()


@router.post(
    "/accounts/{account_id}/knowledge/search",
    response_model=KnowledgeSearchResponse,
)
def search_knowledge(
    account_id: uuid.UUID,
    payload: KnowledgeSearchRequest,
    session: SessionDep,
) -> KnowledgeSearchResponse:
    try:
        citations = service.retrieve(session, account_id, payload)
    except Exception as exc:
        raise _handle_error(exc) from exc
    return KnowledgeSearchResponse(
        account_id=account_id,
        query=payload.query,
        scopes=payload.scopes,
        citations=[KnowledgeCitation(**item) for item in citations],
        candidate_count=len(citations),
        retrieval_strategy="scope filter → pgvector + keyword → metadata filter → rerank",
    )


@router.post(
    "/accounts/{account_id}/knowledge/answers",
    response_model=KnowledgeQueryResponse,
    status_code=status.HTTP_201_CREATED,
)
def answer_from_knowledge(
    account_id: uuid.UUID,
    payload: KnowledgeAnswerRequest,
    session: SessionDep,
) -> KnowledgeQueryResponse:
    try:
        return query_response(service.search_and_record(session, account_id, payload))
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.patch(
    "/accounts/{account_id}/knowledge/documents/{document_id}/status",
    response_model=KnowledgeDocumentResponse,
)
def change_document_status(
    account_id: uuid.UUID,
    document_id: uuid.UUID,
    payload: KnowledgeDocumentStatusRequest,
    session: SessionDep,
) -> KnowledgeDocumentResponse:
    try:
        return document_response(
            service.update_document_status(session, account_id, document_id, payload.status)
        )
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.patch(
    "/accounts/{account_id}/knowledge/evidence-candidates/{candidate_id}",
    response_model=EvidenceBoundaryResponse,
)
def review_candidate(
    account_id: uuid.UUID,
    candidate_id: uuid.UUID,
    payload: EvidenceCandidateReviewRequest,
    session: SessionDep,
) -> EvidenceBoundaryResponse:
    try:
        candidate = service.review_evidence_candidate(
            session, account_id, candidate_id, payload.status
        )
        return EvidenceBoundaryResponse(
            id=candidate.id,
            status=candidate.status,
            boundary=(
                "Evidence review is auditable but does not create a Claim, Hypothesis, "
                "or Confirmed Need."
            ),
        )
    except Exception as exc:
        raise _handle_error(exc) from exc
