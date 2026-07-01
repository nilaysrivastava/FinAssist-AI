import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR.parent
DATA_DIR = BASE_DIR / "data"
KB_SOURCE_DIR = BASE_DIR / "kb_sources"
KB_INDEX_FILE = DATA_DIR / "kb_index.json"

load_dotenv(BACKEND_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_GUARD_MODEL = os.getenv("GROQ_GUARD_MODEL", GROQ_MODEL)
APP_SECRET = os.getenv("APP_SECRET", "dev-secret")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

CHUNK_TARGET_WORDS = int(os.getenv("CHUNK_TARGET_WORDS", "360"))
CHUNK_OVERLAP_WORDS = int(os.getenv("CHUNK_OVERLAP_WORDS", "70"))
EMBEDDING_DIMS = int(os.getenv("EMBEDDING_DIMS", "768"))
MAX_CONTEXT_CHUNKS = int(os.getenv("MAX_CONTEXT_CHUNKS", "6"))
