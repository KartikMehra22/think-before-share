import asyncio
from modules.claims import extract_claims
from modules.transcript import get_transcript

t = get_transcript("jzfy0hXAa-c")
if t["status"] == "success":
    try:
        claims = extract_claims(t["transcript"])
        print(claims)
    except Exception as e:
        print("EXCEPTION TYPE:", type(e))
        print("EXCEPTION:", e)
