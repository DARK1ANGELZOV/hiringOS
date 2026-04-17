from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_candidate_use_cases, get_current_user, get_document_service
from app.api.serializers import document_to_schema
from app.core.database import get_db
from app.models.enums import DocumentType, UserRole
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.document import DocumentDownloadLinkResponse, DocumentResponse
from app.services.document_service import DocumentService
from app.use_cases.candidates.use_cases import CandidateUseCases

router = APIRouter(prefix='/documents', tags=['documents'])


async def _assert_candidate_document_access(*, candidate, current_user: User, candidate_use_cases: CandidateUseCases) -> None:
    active_role = getattr(current_user, 'active_role', current_user.role)
    if active_role == UserRole.ADMIN:
        return

    if active_role == UserRole.CANDIDATE:
        if candidate.owner_user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Access denied')
        return

    if active_role == UserRole.HR:
        if candidate.organization_id != getattr(current_user, 'active_org_id', None):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Organization access denied')
        return

    if active_role == UserRole.MANAGER:
        org_id = getattr(current_user, 'active_org_id', None)
        if candidate.organization_id != org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Organization access denied')
        has_access = await candidate_use_cases.candidate_service.repository.manager_has_access(
            manager_user_id=current_user.id,
            organization_id=org_id,
            candidate_id=candidate.id,
        )
        if not has_access:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Manager candidate scope denied')
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Access denied')


@router.post('/{candidate_id}', response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    candidate_id: UUID,
    document_type: DocumentType,
    file: UploadFile = File(...),
    document_service: DocumentService = Depends(get_document_service),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = await candidate_use_cases.get(candidate_id)
    await _assert_candidate_document_access(candidate=candidate, current_user=current_user, candidate_use_cases=candidate_use_cases)

    document, _ = await document_service.upload(
        candidate_id=candidate_id,
        file=file,
        uploaded_by_user_id=UUID(str(current_user.id)),
        document_type=document_type,
    )
    await db.commit()
    return document_to_schema(document)


@router.get('/{candidate_id}', response_model=list[DocumentResponse])
async def list_documents(
    candidate_id: UUID,
    document_service: DocumentService = Depends(get_document_service),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    current_user: User = Depends(get_current_user),
):
    candidate = await candidate_use_cases.get(candidate_id)
    await _assert_candidate_document_access(candidate=candidate, current_user=current_user, candidate_use_cases=candidate_use_cases)
    items = await document_service.list_for_candidate(candidate_id)
    return [document_to_schema(item) for item in items]


@router.get('/item/{document_id}/download-url', response_model=DocumentDownloadLinkResponse)
async def get_document_download_url(
    document_id: UUID,
    document_service: DocumentService = Depends(get_document_service),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    current_user: User = Depends(get_current_user),
):
    document = await document_service.get(document_id)
    candidate = await candidate_use_cases.get(document.candidate_id)
    await _assert_candidate_document_access(candidate=candidate, current_user=current_user, candidate_use_cases=candidate_use_cases)

    url, expires_in = await document_service.create_download_url(document_id=document_id)
    return DocumentDownloadLinkResponse(document_id=document_id, download_url=url, expires_in_seconds=expires_in)


@router.delete('/item/{document_id}', response_model=MessageResponse)
async def delete_document(
    document_id: UUID,
    document_service: DocumentService = Depends(get_document_service),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = await document_service.get(document_id)
    candidate = await candidate_use_cases.get(document.candidate_id)
    await _assert_candidate_document_access(candidate=candidate, current_user=current_user, candidate_use_cases=candidate_use_cases)

    await document_service.delete(document_id=document_id)
    await db.commit()
    return MessageResponse(message='Document deleted')


@router.put('/item/{document_id}/replace', response_model=DocumentResponse)
async def replace_document(
    document_id: UUID,
    file: UploadFile = File(...),
    document_service: DocumentService = Depends(get_document_service),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = await document_service.get(document_id)
    candidate = await candidate_use_cases.get(document.candidate_id)
    await _assert_candidate_document_access(candidate=candidate, current_user=current_user, candidate_use_cases=candidate_use_cases)

    updated = await document_service.replace(
        document_id=document_id,
        file=file,
        uploaded_by_user_id=UUID(str(current_user.id)),
    )
    await db.commit()
    return document_to_schema(updated)
