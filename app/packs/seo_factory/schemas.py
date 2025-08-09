from pydantic import BaseModel, Field

class KeywordTask(BaseModel):
    topic: str = Field(..., min_length=2)
    market: str = "en"
    depth: int = 20
