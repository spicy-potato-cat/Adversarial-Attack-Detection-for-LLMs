from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DetectionContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["user_prompt"]
    text: str

    @field_validator("text")
    @classmethod
    def reject_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must contain at least one non-whitespace character")
        return value


class DetectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1, max_length=200)
    content: DetectionContent

    @field_validator("request_id")
    @classmethod
    def reject_blank_request_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("request_id must not be blank")
        return value

