import os
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL"))
try:
    for i in range(30):
        print(f"Call {i}")
        model.generate_content("Hello")
except Exception as e:
    print(repr(e))
    print(type(e))
    print(type(e).__module__)
