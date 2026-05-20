import os
from dotenv import load_dotenv

load_dotenv()

AI_PROVIDER: str = os.getenv("AI_PROVIDER", "anthropic").lower()  # anthropic | gemini | groq
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
DB_PATH: str = os.getenv("DB_PATH", "career_compass.db")

_REQUIRED_KEY = {
    "anthropic": ("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY),
    "gemini":    ("GEMINI_API_KEY",    GEMINI_API_KEY),
    "groq":      ("GROQ_API_KEY",      GROQ_API_KEY),
}

if AI_PROVIDER not in _REQUIRED_KEY:
    raise RuntimeError(f"Unknown AI_PROVIDER '{AI_PROVIDER}'. Choose: anthropic | gemini | groq")

_key_name, _key_val = _REQUIRED_KEY[AI_PROVIDER]
if not _key_val:
    raise RuntimeError(f"AI_PROVIDER='{AI_PROVIDER}' but {_key_name} is not set in .env")
