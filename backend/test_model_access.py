import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

models_to_test = [
    "gemini-2.0-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash"
]

for m in models_to_test:
    model = genai.GenerativeModel(m)
    try:
        response = model.generate_content("Say 'hello'")
        print(f"[SUCCESS] {m} works! Response: {response.text.strip()}")
    except Exception as e:
        print(f"[FAILED] {m} failed: {e}")
