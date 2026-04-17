from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import DocumentType


class DocumentResponse(BaseModel):
    id: UUID
    candidate_id: UUID
    bucket: str
    object_key: str
    original_filename: str
    content_type: str
    size_bytes: int
    document_type: DocumentType
    created_at: datetime


class DocumentDownloadLinkResponse(BaseModel):
    document_id: UUID
    download_url: str
    expires_in_seconds: int

