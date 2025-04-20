from typing import List, Optional
from pydantic import BaseModel, Field


class Segment(BaseModel):
    """Represents a single transcript segment with timing information."""

    text: str
    start: float
    duration: float

    @property
    def end(self) -> float:
        return self.start + self.duration


class Chunk(BaseModel):
    """A group of consecutive segments forming a logical unit."""

    segments: List[Segment]
    text: str = Field(..., description="Combined text from all segments")
    start: float = Field(..., description="Start time of first segment")
    end: float = Field(..., description="End time of last segment")


class Answer(BaseModel):
    """Response to a question with relevant context."""

    question: str
    answer: str
    context: List[Chunk]
    confidence: Optional[float] = None


class TopicBlock(BaseModel):
    """A block of transcript segments representing a single topic."""

    title: str
    start: float
    segments: List[Segment]
