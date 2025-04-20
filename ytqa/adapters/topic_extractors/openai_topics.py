import openai, textwrap, json
from typing import List
from ...core.models import Segment, TopicBlock

SYSTEM_PROMPT_TOPICS = """
You are a seasoned video indexer.  
Your goal: turn a chronological list of transcript segments (each with `start` seconds + text) into a set of concise, learner‑oriented *chapters* that help viewers jump straight to the parts they care about.

Return **only** valid JSON with a single top‑level key `"topics"` whose value is an array of objects **sorted by `start`**.  
Each object must have:

- `"title"` — ≤ 8‑word noun phrase summarising the block’s main idea (avoid quotes, punctuation, emoji).  
- `"start"` — floating‑point seconds copied from the first segment in the block.  
- `"segments"` — list of *all* segment indices (0‑based, inclusive) that belong to this block, in order.

Guidelines
1. Build coherent blocks roughly **1‑6 minutes** long; combine adjacent segments until the topic clearly shifts.  
2. Chapters must **cover the entire video** in order; no gaps, no overlaps.  
3. Prefer *broad thematic* labels a learner would skim (e.g., “Vector Embeddings Basics”, not “We talk about vectors”).  
4. If the video already contains obvious section markers, respect them, but still enforce the JSON schema.  
5. Output **nothing** except the JSON object.

Example (structure only):

{
  "topics": [
    { "title": "Introduction & Agenda", "start": 0,   "segments": [0,1,2,3] },
    { "title": "Setting up the Dataset", "start": 245, "segments": [4,5,6,7,8] },
    ...
  ]
}
"""


class OpenAITopicExtractor:
    def __init__(self, model):
        print(f"\n=== Initializing OpenAITopicExtractor ===")
        print(f"Requested model: {model}")
        self.model = model
        try:
            # Test if the model is available
            models = openai.models.list()
            available_models = [m.id for m in models]
            print(f"Available models: {available_models}")
            if model not in available_models:
                print(f"Warning: Model {model} not found in available models")
                print("Will attempt to use it anyway, but this might fail")
            else:
                print(f"Model {model} is available")
        except Exception as e:
            print(f"Error checking model availability: {str(e)}")
            print("Will attempt to use the model anyway")

    def extract(self, segments: List[Segment]) -> List[TopicBlock]:
        """Extract topics from transcript segments."""
        try:
            print(f"\n=== Starting topic extraction ===")
            print(f"Input: {len(segments)} segments")
            print(f"Using model: {self.model}")

            # Join segments with timestamps
            print("Preparing segments for OpenAI...")
            joined = "\n".join([f"[{s.start:.1f}s] {s.text}" for s in segments])
            print(f"Total text length: {len(joined)} characters")

            # Create chat completion
            print("\nSending request to OpenAI...")
            try:
                response = openai.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT_TOPICS,
                        },
                        {"role": "user", "content": joined},
                    ],
                    response_format={"type": "json_object"},
                )
                print("Successfully received response from OpenAI")
            except Exception as e:
                print(f"Error in OpenAI API call: {str(e)}")
                print("Stack trace:", e.__class__.__name__)
                import traceback

                print(traceback.format_exc())
                raise

            # Parse response
            print("\nParsing OpenAI response...")
            try:
                topics_data = json.loads(response.choices[0].message.content)
                print(f"Raw topics data: {topics_data}")
            except json.JSONDecodeError as e:
                print("Error: Invalid JSON in OpenAI response")
                print(f"Raw response content: {response.choices[0].message.content}")
                raise

            # Convert to TopicBlock objects
            topics = []
            print("\nProcessing topics...")
            for topic_data in topics_data.get("topics", []):
                try:
                    # Find segments that belong to this topic
                    topic_segments = []
                    start_time = float(topic_data.get("start", 0))
                    title = topic_data.get("title", "").strip()

                    print(f"\nProcessing topic: {title}")
                    print(f"Start time: {start_time}")

                    if not title:
                        print(f"Skipping topic with empty title at {start_time}s")
                        continue

                    # Find segments that belong to this topic by matching start times
                    print("Finding matching segments...")
                    for segment in segments:
                        if abs(segment.start - start_time) < 1.0:  # Within 1 second
                            print(f"Found matching segment at {segment.start}s")
                            topic_segments = self._get_segment_block(
                                segments, segment, 360
                            )  # ~6 minutes max
                            print(f"Got {len(topic_segments)} segments for this topic")
                            break

                    if topic_segments:
                        topic = TopicBlock(
                            title=title,
                            start=start_time,
                            segments=topic_segments,
                        )
                        topics.append(topic)
                        print(f"Added topic: {title} (starts at {start_time:.1f}s)")
                    else:
                        print(
                            f"No segments found for topic '{title}' at {start_time:.1f}s"
                        )

                except Exception as e:
                    print(f"Error processing topic: {str(e)}")
                    print("Stack trace:", e.__class__.__name__)
                    import traceback

                    print(traceback.format_exc())
                    continue

            if not topics:
                print("Error: No valid topics were extracted")
                raise ValueError("No valid topics were extracted from the response")

            print(f"\nSuccessfully extracted {len(topics)} topics")
            return topics

        except Exception as e:
            print(f"\nError in topic extraction: {str(e)}")
            print("Stack trace:", e.__class__.__name__)
            import traceback

            print(traceback.format_exc())
            raise

    def _get_segment_block(
        self, all_segments: List[Segment], start_segment: Segment, max_duration: float
    ) -> List[Segment]:
        """Get a block of segments starting from start_segment up to max_duration seconds."""
        block = []
        current_duration = 0
        started = False

        for segment in all_segments:
            if segment == start_segment:
                started = True

            if started:
                if current_duration + segment.duration > max_duration:
                    break
                block.append(segment)
                current_duration += segment.duration

        return block
