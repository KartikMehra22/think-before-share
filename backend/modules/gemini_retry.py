"""
Shared Gemini retry logic.

Google's ResourceExhausted error includes the exact wait time in its message:
  "Please retry in 8.84753s."

We parse that value and sleep exactly that long (+ a 2s buffer), which is
far more reliable than exponential backoff guessing.
"""
import re
import time
import logging

logger = logging.getLogger(__name__)

_RETRY_AFTER_RE = re.compile(r"retry in (\d+(?:\.\d+)?)\s*s", re.IGNORECASE)


def parse_retry_after(exc: Exception) -> float | None:
    """Extract the suggested retry-after seconds from a ResourceExhausted error."""
    msg = str(exc)
    m = _RETRY_AFTER_RE.search(msg)
    if m:
        return float(m.group(1))
    return None


def gemini_retry(func, *args, max_attempts: int = 5, label: str = "gemini_call", **kwargs):
    """
    Call `func(*args, **kwargs)`, retrying on ResourceExhausted.

    Strategy:
      - On rate-limit, parse the exact retry-after seconds from the error.
      - Sleep for (retry_after + 2s buffer) so the window definitely resets.
      - Fall back to 15s if the retry-after can't be parsed.
      - Give up and re-raise after `max_attempts`.
    """
    from google.api_core.exceptions import ResourceExhausted

    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except ResourceExhausted as exc:
            if attempt == max_attempts:
                logger.error(
                    "%s: rate-limited on final attempt %d/%d — giving up. err=%s",
                    label, attempt, max_attempts, exc,
                )
                raise

            wait = parse_retry_after(exc)
            if wait is None:
                wait = 15.0   # conservative fallback
            wait += 2.0       # add a 2-second buffer

            logger.warning(
                "%s: rate-limited (attempt %d/%d). "
                "Sleeping %.1fs (parsed from API error + 2s buffer)…",
                label, attempt, max_attempts, wait,
            )
            time.sleep(wait)
            logger.info("%s: resuming after rate-limit wait.", label)
