import re
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:embed\/)([0-9A-Za-z_-]{11})",
        r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from URL: {url}")


def get_transcript(video_id: str, max_chars: int = 12000) -> str:
    """
    Fetch the transcript for a YouTube video and return as a single string.
    Truncates to max_chars to avoid exceeding LLM context limits.
    """
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
    except NoTranscriptFound:
        # Try any available language
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = transcript_list.find_generated_transcript(
                transcript_list._manually_created_transcripts.keys()
                or transcript_list._generated_transcripts.keys()
            )
            transcript_list = transcript.fetch()
        except Exception as e:
            raise ValueError(f"No transcript available for this video: {e}")
    except TranscriptsDisabled:
        raise ValueError("Transcripts are disabled for this video.")
    except Exception as e:
        raise ValueError(f"Failed to fetch transcript: {e}")

    # Join all transcript segments into a single text
    full_text = " ".join(seg["text"] for seg in transcript_list)

    # Truncate to keep within LLM token limits
    if len(full_text) > max_chars:
        full_text = full_text[:max_chars] + "... [transcript truncated]"

    return full_text
