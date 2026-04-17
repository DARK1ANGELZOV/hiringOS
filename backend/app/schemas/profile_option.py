from datetime import datetime

from pydantic import BaseModel, Field


class ProfileOptionCreateRequest(BaseModel):
    value: str = Field(min_length=1, max_length=255)


class ProfileOptionResponse(BaseModel):
    id: str
    option_type: str
    value: str
    created_by_user_id: str | None
    created_at: datetime
