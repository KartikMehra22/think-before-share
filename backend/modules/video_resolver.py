import re

class InvalidURLError(Exception):
    pass

def extract_video_id(url: str) -> dict:
    """Extract YouTube video ID from various URL formats or raw 11-char ID.
    Returns: { "video_id": str, "url": str }
    """
    clean_url = url.strip()

    # If user passes raw 11-character video ID directly
    if re.fullmatch(r"[0-9A-Za-z_-]{11}", clean_url):
        return {"video_id": clean_url, "url": f"https://www.youtube.com/watch?v={clean_url}"}

    patterns = [
        r"(?:v=|\/v\/|\/embed\/|\/shorts\/|\/live\/)([0-9A-Za-z_-]{11})",
        r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
        r"(?:v=)([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, clean_url)
        if match:
            return {"video_id": match.group(1), "url": clean_url}

    raise InvalidURLError(f"Could not extract YouTube video ID from URL: {url}")

