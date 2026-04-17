from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_candidate_use_cases, get_current_user, get_resume_use_cases
from app.api.serializers import resume_to_schema
from app.core.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.resume import ResumeManualUpdateRequest, ResumeParseTextRequest, ResumeProfileResponse, ResumeUploadResponse
from app.use_cases.candidates.use_cases import CandidateUseCases
from app.use_cases.resumes.use_cases import ResumeUseCases

router = APIRouter(prefix='/resumes', tags=['resumes'])


@router.post('/upload/{candidate_id}', response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_and_parse_resume(
    candidate_id: UUID,
    file: UploadFile = File(...),
    use_cases: ResumeUseCases = Depends(get_resume_use_cases),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = await candidate_use_cases.get(candidate_id)
    if current_user.role == UserRole.CANDIDATE and candidate.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Access denied')

    document, profile, fallback_used = await use_cases.upload_and_parse(
        candidate_id=candidate_id,
        file=file,
        actor_user_id=UUID(str(current_user.id)),
    )
    await db.commit()
    return ResumeUploadResponse(
        candidate_id=candidate_id,
        document_id=document.id,
        resume_profile_id=profile.id,
        parser_status=profile.parser_status,
        structured_data=profile.structured_data,
        fallback_used=fallback_used,
    )


@router.get('/candidate/{candidate_id}', response_model=ResumeProfileResponse)
async def get_resume_profile(
    candidate_id: UUID,
    use_cases: ResumeUseCases = Depends(get_resume_use_cases),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    current_user: User = Depends(get_current_user),
):
    candidate = await candidate_use_cases.get(candidate_id)
    if current_user.role == UserRole.CANDIDATE and candidate.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Access denied')

    profile = await use_cases.get_profile(candidate_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Resume profile not found')
    return resume_to_schema(profile)


@router.patch('/{resume_id}', response_model=ResumeProfileResponse)
async def manual_update_resume(
    resume_id: UUID,
    payload: ResumeManualUpdateRequest,
    use_cases: ResumeUseCases = Depends(get_resume_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in {UserRole.CANDIDATE, UserRole.HR, UserRole.MANAGER, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Access denied')

    profile = await use_cases.manual_update(
        resume_id=resume_id,
        structured_data=payload.structured_data,
        actor_user_id=UUID(str(current_user.id)),
    )
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Resume profile not found')

    await db.commit()
    return resume_to_schema(profile)


@router.post('/parse-text/{candidate_id}', response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def parse_resume_text(
    candidate_id: UUID,
    payload: ResumeParseTextRequest,
    use_cases: ResumeUseCases = Depends(get_resume_use_cases),
    candidate_use_cases: CandidateUseCases = Depends(get_candidate_use_cases),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    candidate = await candidate_use_cases.get(candidate_id)
    if current_user.role == UserRole.CANDIDATE and candidate.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Access denied')

    profile, fallback_used = await use_cases.parse_text(
        candidate_id=candidate_id,
        text=payload.text,
        actor_user_id=UUID(str(current_user.id)),
    )
    await db.commit()
    return ResumeUploadResponse(
        candidate_id=candidate_id,
        document_id=profile.document_id,
        resume_profile_id=profile.id,
        parser_status=profile.parser_status,
        structured_data=profile.structured_data,
        fallback_used=fallback_used,
    )
