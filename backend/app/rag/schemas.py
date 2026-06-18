from pydantic import BaseModel, Field


class SourceMetadata(BaseModel):
    source_url: str
    source_name: str
    patch_version: str | None = None
    entity_type: str
    entity_name: str
    updated_at: str


class DocumentInput(BaseModel):
    text: str = Field(min_length=1)
    metadata: SourceMetadata


class TextChunk(BaseModel):
    chunk_id: str
    text: str = Field(min_length=1)
    metadata: SourceMetadata


class RetrievedChunk(BaseModel):
    chunk: TextChunk
    score: float
