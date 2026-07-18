import os
import sys
import json
import argparse
from datetime import datetime, timezone

# Add backend directory to sys.path to enable imports
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

try:
    from transcript import extract_video_id, get_transcript
except ModuleNotFoundError as e:
    print(f"Error importing modules: {e}")
    print("\nIt looks like python is not running inside the project virtual environment.")
    print("Please resolve this by either:")
    print("  1. Activating the virtual environment:")
    print("     source backend/.venv/bin/activate")
    print("     python backend/fixtures/save_demo_fixture.py <url>")
    print("  2. Running the script directly with the virtual environment interpreter:")
    print("     backend/.venv/bin/python backend/fixtures/save_demo_fixture.py <url>\n")
    sys.exit(1)

MOCK_TRANSCRIPT = (
    "The Apollo 11 mission successfully landed the first humans on the Moon in July 1969. "
    "Neil Armstrong and Buzz Aldrin spent over two hours exploring the lunar surface, "
    "collecting rock samples, and taking photographs. "
    "The Earth is approximately 150 million kilometers (93 million miles) away from the Sun, "
    "and light from the Sun takes about 8 minutes and 20 seconds to reach our planet. "
    "Mount Everest is the highest mountain above sea level on Earth, located in the Himalayas range "
    "on the border between Nepal and China. "
    "Atmospheric carbon dioxide levels have risen significantly since the industrial revolution, "
    "and recent climate observations show that CO2 levels now exceed 415 parts per million."
)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch a YouTube transcript and save it as a local JSON fixture for testing."
    )
    parser.add_argument("url", type=str, help="YouTube video URL")
    parser.add_argument(
        "--allow-mock-fallback",
        action="store_true",
        default=False,
        help=(
            "If real transcript fetching fails, write MOCK data instead of exiting. "
            "A loud warning will still be printed and 'is_mock: true' will be set in the fixture. "
            "Never use this for demo runs — only for unblocking local pipeline testing."
        ),
    )
    args = parser.parse_args()

    url = args.url.strip()
    print(f"Extracting video ID from: {url}")

    try:
        video_id = extract_video_id(url)
        print(f"Extracted video ID: {video_id}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print("Fetching transcript (trying transcript-api, then yt-dlp fallback)...")
    transcript_text = None
    is_mock = False

    try:
        transcript_text = get_transcript(video_id)
        print(f"✅ Successfully fetched real transcript ({len(transcript_text)} characters).")
    except Exception as fetch_err:
        if args.allow_mock_fallback:
            print()
            print("=" * 70)
            print("⚠️  WARNING: Could not fetch real transcript.")
            print(f"   Error: {fetch_err}")
            print()
            print("   Writing MOCK data instead (--allow-mock-fallback was passed).")
            print("   The fixture will contain 'is_mock: true'.")
            print("   DO NOT use this fixture for the live demo.")
            print("=" * 70)
            print()
            transcript_text = MOCK_TRANSCRIPT
            is_mock = True
        else:
            print()
            print("=" * 70)
            print("❌ ERROR: Could not fetch real transcript — no fixture was saved.")
            print(f"   Error: {fetch_err}")
            print()
            print("   If you want to write mock data anyway (for local pipeline testing),")
            print("   re-run with the --allow-mock-fallback flag:")
            print(f"   python {sys.argv[0]} \"{url}\" --allow-mock-fallback")
            print("=" * 70)
            print()
            sys.exit(1)

    fixture_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_transcript.json")

    payload = {
        "video_id": video_id,
        "url": url,
        "transcript": transcript_text,
        "is_mock": is_mock,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        os.makedirs(os.path.dirname(fixture_path), exist_ok=True)
        with open(fixture_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        status = "MOCK" if is_mock else "REAL"
        print(f"Saved [{status}] fixture to: {fixture_path}")
    except Exception as e:
        print(f"Error saving fixture: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
