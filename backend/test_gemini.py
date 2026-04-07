import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY')
model_name = os.getenv('GEMINI_MODEL', 'gemini-pro')

print(f"API Key: {api_key[:10]}...")
print(f"Model: {model_name}")

genai.configure(api_key=api_key)

try:
    model = genai.GenerativeModel(model_name)
    response = model.generate_content("Hello")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"ERROR: {e}")
