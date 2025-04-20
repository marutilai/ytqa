from abc import ABC, abstractmethod
from typing import List

from ...core.models import Segment


class TranscriptProvider(ABC):
    """Base class for transcript providers."""

    @abstractmethod
    def get_transcript(self, video_id: str) -> List[Segment]:
        """Retrieve transcript segments for a video."""
        pass
