import os
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL"))
try:
    response = model.generate_content("Hello")
    print(response.text)
except Exception as e:
    print("ERROR:")
    print(repr(e))
