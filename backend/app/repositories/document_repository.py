from uuid import UUID

from sqlalchemy import delete
from sqlalchemy import select

from app.models.document import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    async def create(self, **kwargs) -> Document:
        document = Document(**kwargs)
        self.db.add(document)
        await self.db.flush()
        return document

    async def get_by_id(self, document_id: UUID) -> Document | None:
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()

    async def list_by_candidate(self, candidate_id: UUID) -> list[Document]:
        result = await self.db.execute(
            select(Document)
            .where(Document.candidate_id == candidate_id)
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, document: Document, **kwargs) -> Document:
        for field, value in kwargs.items():
            setattr(document, field, value)
        await self.db.flush()
        return document

    async def delete(self, document_id: UUID) -> bool:
        result = await self.db.execute(delete(Document).where(Document.id == document_id))
        await self.db.flush()
        return int(result.rowcount or 0) > 0

