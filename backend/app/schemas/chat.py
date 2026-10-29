from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Intent(StrEnum):
    GENERAL_QUESTION = "GENERAL_QUESTION"
    KNOWLEDGE_QUERY = "KNOWLEDGE_QUERY"
    QUOTE_REQUEST = "QUOTE_REQUEST"
    LEAD = "LEAD"
    DOCUMENT_DEMO = "DOCUMENT_DEMO"
    UNSUPPORTED = "UNSUPPORTED"


class Message(Contract):
    role: Literal["user", "assistant"]
    content: Annotated[str, Field(min_length=1, max_length=2000)]


class ChatRequest(Contract):
    # A turn is a user message and its optional assistant reply. Last user is unanswered.
    messages: Annotated[list[Message], Field(min_length=1, max_length=19)]
    turnstile_token: Annotated[str, Field(min_length=1, max_length=2048)]

    @model_validator(mode="after")
    def validate_conversation(self) -> "ChatRequest":
        for index, message in enumerate(self.messages):
            expected = "user" if index % 2 == 0 else "assistant"
            if message.role != expected or not message.content.strip():
                raise ValueError("Messages must alternate and contain nonblank text")
        if self.messages[-1].role != "user":
            raise ValueError("Conversation must end with a user message")
        return self


class Citation(Contract):
    corpus_id: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    source_id: str
    chunk_id: str
    title: str
    excerpt: str
    first_line: Annotated[int, Field(gt=0)]
    last_line: Annotated[int, Field(gt=0)]


class SourceDocument(Contract):
    corpus_id: str
    source_id: str
    title: str
    content: str


class TraceStep(Contract):
    agent: Literal["safety", "router", "lead", "rag", "document", "response", "validation"]
    status: Literal["success", "failed", "skipped"]
    duration_ms: Annotated[int, Field(ge=0)]


class Lead(Contract):
    customer_type: Literal["B2B", "B2C"] | None = None
    company: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    product: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    quantity: Annotated[int, Field(gt=0, le=1000000)] | None = None
    urgency: Literal["low", "medium", "high"] | None = None


class ChatResponse(Contract):
    request_id: str
    mode: Literal["live", "demo"]
    answer: Annotated[str, Field(min_length=1, max_length=8000)]
    citations: list[Citation] = Field(default_factory=list)
    lead: Lead | None = None
    trace: list[TraceStep]


class ErrorResponse(Contract):
    error: str
    message: str
    request_id: str
