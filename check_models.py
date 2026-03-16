from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize client
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

print("✅ Client initialized")
print("\n📋 Available models:")

try:
    # List all models
    for model in client.models.list():
        print(f"  - {model.name}")
        print(f"    Display name: {model.display_name}")
        print(f"    Description: {model.description[:100]}...")
        print()
except Exception as e:
    print(f"❌ Error listing models: {e}")