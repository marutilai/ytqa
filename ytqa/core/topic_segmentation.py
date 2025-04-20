from typing import List
from ..adapters.topic_extractors import OpenAITopicExtractor
from .models import Segment, TopicBlock


def topics_from_segments(segments: List[Segment], cfg) -> List[TopicBlock]:
    """
    Extract topics from transcript segments using OpenAI's chat completion.

    Args:
        segments: List of transcript segments
        cfg: Configuration object containing topic_model

    Returns:
        List of TopicBlock objects containing title and segments
    """
    try:
        # Initialize the topic extractor
        extractor = OpenAITopicExtractor(cfg.topic_model)

        # Extract topics
        topics = extractor.extract(segments)

        # Validate and clean topics
        validated_topics = []
        for topic in topics:
            if not topic.title or not topic.segments:
                continue
            # Ensure title is clean and concise
            topic.title = topic.title.strip().rstrip(".")
            validated_topics.append(topic)

        return validated_topics

    except Exception as e:
        print(f"Error extracting topics: {str(e)}")
        raise
