"""Контракт сервиса: что принимаем и что отдаём."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TriageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    channel: Literal["email", "form", "chat"]
    client_id: str = Field(min_length=1, max_length=64)

    @field_validator("text", "client_id")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("не может быть пустым")
        return value


class TriageResponse(BaseModel):
    category: Literal["billing", "support", "complaint", "other"]
    draft_reply: str
    confidence: Literal["high", "medium", "low"]
    escalate: bool
