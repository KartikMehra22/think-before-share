import re
import os
import tempfile
import logging
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

logger = logging.getLogger(__name__)


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


def _fetch_via_transcript_api(video_id: str) -> list[dict]:
    """
    Attempt to fetch transcript using youtube-transcript-api.
    Returns a list of segment dicts with 'text' keys.
    Raises on any failure so the caller can fall back.
    """
    try:
        segments = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
        return segments
    except NoTranscriptFound:
        # Try any available auto-generated transcript
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        generated_keys = list(transcript_list._generated_transcripts.keys())
        manual_keys = list(transcript_list._manually_created_transcripts.keys())
        keys = manual_keys or generated_keys
        if not keys:
            raise ValueError("No transcripts available for this video (no_transcript).")
        transcript = transcript_list.find_generated_transcript(keys)
        
        # In 0.6.2, we can just fetch whatever language it is!
        try:
            return transcript.translate('en').fetch()
        except Exception:
            return transcript.fetch()


def _parse_vtt(vtt_text: str) -> str:
    """
    Parse a WebVTT subtitle file into plain text, stripping timestamps,
    tags, and deduplicating consecutive duplicate lines.
    """
    lines = []
    for line in vtt_text.splitlines():
        line = line.strip()
        # Skip WebVTT header, blank lines, and timestamp lines
        if not line or line == "WEBVTT" or "-->" in line:
            continue
        # Strip inline tags like <00:00:00.000> and <c> </c>
        line = re.sub(r"<[^>]+>", "", line).strip()
        if not line:
            continue
        # Deduplicate consecutive identical lines (common in VTT auto-captions)
        if lines and lines[-1] == line:
            continue
        lines.append(line)
    return " ".join(lines)


def _fetch_via_yt_dlp(video_id: str) -> str:
    """
    Attempt to fetch transcript using yt-dlp subtitle extraction.
    
    Strategy (two-step to minimise HTTP requests and avoid 429s):
      1. Extract metadata only (no download) to discover available subtitle language IDs.
      2. Select the best native English subtitle ID (prefers manual 'en', then auto-gen 'en*',
         excluding machine-translated subs like 'en-es-...' or 'en-fr-...').
      3. Download only that one subtitle file.
    
    Returns plain text. Raises on failure.
    """
    try:
        import yt_dlp
    except ImportError:
        raise RuntimeError("yt-dlp is not installed. Run: pip install yt-dlp")

    url = f"https://www.youtube.com/watch?v={video_id}"

    # --- Step 1: Metadata only — discover available subtitle IDs ---
    meta_opts = {
        "skip_download": True,
        "writeautomaticsub": False,
        "writesubtitles": False,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(meta_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    # Gather candidate subtitle language IDs from both manual and auto-generated pools.
    # Exclude machine-translated IDs which follow the pattern "en-<sourcelang>-<id>"
    # (they have a second hyphenated segment after "en").
    all_subs: dict = {}
    all_subs.update(info.get("subtitles", {}))       # manually uploaded
    all_subs.update(info.get("automatic_captions", {}))  # auto-generated

    def _is_native_english(lang_id: str) -> bool:
        """True for 'en', 'en-US', 'en-nP7-2PuUl7o' — False for 'en-fr-rSJ...' style."""
        if not lang_id.startswith("en"):
            return False
        rest = lang_id[2:]           # everything after "en"
        if not rest:
            return True              # bare "en"
        if not rest.startswith("-"):
            return False
        # A machine-translated ID looks like "en-es-<longid>" — it has a recognisable
        # 2-3 char ISO language code immediately after the first dash.
        # A native ID looks like "en-nP7-2PuUl7o" — starts with a random alphanumeric.
        after_dash = rest[1:]
        # Check if the part after the first dash begins with a known ISO 639-1/639-2 code
        # followed by another dash or end-of-string (e.g. "es-", "fr-", "pt-BR-").
        import re as _re
        if _re.match(r"^[a-z]{2,3}(-|$)", after_dash):
            return False             # looks like a translated sub (en-es-..., en-fr-...)
        return True                  # native English subtitle with a random ID suffix

    candidates = [lid for lid in all_subs if _is_native_english(lid)]
    if not candidates:
        raise ValueError(
            f"yt-dlp: no native English subtitles found for video '{video_id}'. "
            f"Available language IDs: {list(all_subs.keys())[:20]}"
        )

    # Prefer bare "en" if present, otherwise pick the first matching candidate.
    target_lang = "en" if "en" in candidates else candidates[0]
    logger.info("yt-dlp: downloading subtitle lang_id=%s for %s", target_lang, video_id)

    # --- Step 2: Download only the selected subtitle file ---
    with tempfile.TemporaryDirectory() as tmpdir:
        dl_opts = {
            "skip_download": True,
            "writeautomaticsub": True,
            "writesubtitles": True,
            "subtitleslangs": [target_lang],
            "subtitlesformat": "vtt",
            "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(dl_opts) as ydl:
            ydl.extract_info(url, download=True)

        vtt_files = [
            os.path.join(tmpdir, f)
            for f in os.listdir(tmpdir)
            if f.endswith(".vtt")
        ]
        if vtt_files:
            with open(vtt_files[0], "r", encoding="utf-8") as fh:
                raw = fh.read()
            text = _parse_vtt(raw)
            if text.strip():
                return text

    raise ValueError(
        f"yt-dlp downloaded subtitle file for lang '{target_lang}' but parsed text was empty."
    )



def get_transcript(video_id: str, max_chars: int = 12000) -> str:
    """
    Fetch the transcript for a YouTube video and return as a single string.
    Truncates to max_chars to avoid exceeding LLM context limits.

    Strategy:
      1. Try youtube-transcript-api (fast, no download).
      2. If that fails, fall back to yt-dlp subtitle extraction.
      3. If both fail, raise ValueError — the caller decides what to do.

    Logs which method succeeded so callers can see which path was taken.
    """
    # --- Primary: youtube-transcript-api ---
    try:
        segments = _fetch_via_transcript_api(video_id)
        full_text = " ".join(seg["text"] for seg in segments)
        logger.info("transcript_api: successfully fetched transcript for %s", video_id)
        method = "transcript_api"
    except Exception as primary_err:
        logger.warning(
            "transcript_api failed for %s (%s). Trying yt-dlp fallback...",
            video_id,
            primary_err,
        )
        # --- Fallback: yt-dlp ---
        try:
            full_text = _fetch_via_yt_dlp(video_id)
            logger.info("yt_dlp_fallback: successfully fetched transcript for %s", video_id)
            method = "yt_dlp_fallback"
        except Exception as fallback_err:
            raise ValueError(
                f"Both transcript methods failed for video '{video_id}'. "
                f"transcript_api error: {primary_err} | "
                f"yt_dlp error: {fallback_err}"
            )

    # Truncate to keep within LLM token limits
    if len(full_text) > max_chars:
        full_text = full_text[:max_chars] + "... [transcript truncated]"

    logger.info("Transcript fetched via '%s' (%d chars).", method, len(full_text))
    return full_text
