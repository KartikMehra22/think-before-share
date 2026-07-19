import re

class InvalidURLError(Exception):
    pass

def extract_video_id(url: str) -> dict:
    """Extract YouTube video ID from various URL formats.
    Returns: { "video_id": str, "url": str }
    """
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:embed\/)([0-9A-Za-z_-]{11})",
        r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return {"video_id": match.group(1), "url": url}
    raise InvalidURLError(f"Could not extract video ID from URL: {url}")
