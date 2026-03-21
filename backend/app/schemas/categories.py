import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: uuid.UUID | None = None
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str | None = Field(None, max_length=50)


class CategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    parent_id: uuid.UUID | None = None
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str | None = Field(None, max_length=50)

    @field_validator("color", mode="before")
    @classmethod
    def allow_null_color(cls, v: str | None) -> str | None:
        return v


class CategoryResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    parent_id: uuid.UUID | None
    name: str
    color: str | None
    icon: str | None
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
