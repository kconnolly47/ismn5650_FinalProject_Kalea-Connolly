import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Key for authentication - strip any whitespace
API_KEY = os.getenv("API_KEY", "").strip()

if not API_KEY:
    raise ValueError("API_KEY not found in environment variables. Please set it in .env file")

# Debug: print the API key when server starts (remove after testing)
print(f"Loaded API_KEY: '{API_KEY}'")