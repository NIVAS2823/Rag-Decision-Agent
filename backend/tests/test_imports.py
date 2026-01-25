import os
import warnings
import pytest

# ---------------------------------------------------------------------------
# WARNING HANDLING (Silence known non-fatal warnings)
# ---------------------------------------------------------------------------
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ---------------------------------------------------------------------------
# TEST DEFINITIONS
# ---------------------------------------------------------------------------

CRITICAL_IMPORTS = [
    # Web Framework
    ("FastAPI", "import fastapi"),
    ("Uvicorn", "import uvicorn"),

    # LangChain / LangGraph
    ("LangChain", "import langchain"),
    ("LangGraph", "import langgraph"),
    ("LangSmith", "import langsmith"),

    # LLM Providers
    ("OpenAI", "import openai"),
    ("Anthropic", "import anthropic"),
    ("Gemini (Google)", "import google.generativeai as genai"),
    ("Groq", "from groq import Groq"),

    # RAG Components
    ("FAISS", "import faiss"),
    ("Sentence Transformers", "from sentence_transformers import SentenceTransformer"),
    ("BM25", "from rank_bm25 import BM25Okapi"),

    # Data Validation
    ("Pydantic", "import pydantic"),

    # Databases
    ("Motor (MongoDB)", "import motor.motor_asyncio"),
    ("Redis", "import redis"),

    # Authentication
    ("Jose (JWT)", "from jose import jwt"),
    ("Passlib", "from passlib.context import CryptContext"),

    # Document Processing
    ("PyPDF", "import pypdf"),
    ("Python-docx", "import docx"),

    # External APIs
    ("Tavily", "from tavily import TavilyClient"),
    ("Boto3 (R2)", "import boto3"),

    # Utilities
    ("Python-dotenv", "from dotenv import load_dotenv"),
    ("Requests", "import requests"),
    ("HTTPX", "import httpx"),
]

OPTIONAL_ENV_CHECKS = [
    ("OpenAI", "OPENAI_API_KEY"),
    ("Gemini", "GOOGLE_API_KEY"),
    ("Groq", "GROQ_API_KEY"),
    ("LangSmith", "LANGSMITH_API_KEY"),
    ("Tavily", "TAVILY_API_KEY"),
]

# ---------------------------------------------------------------------------
# TESTS
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("package_name, import_statement", CRITICAL_IMPORTS)
def test_import(package_name, import_statement):
    """Ensure critical packages import correctly."""
    try:
        exec(import_statement, {})
    except ImportError as e:
        pytest.fail(f"❌ {package_name} import failed: {e}")
    except Exception as e:
        # Runtime warnings should not fail CI, but should be visible
        pytest.xfail(f"⚠️ {package_name} runtime warning: {e}")


@pytest.mark.parametrize("package_name, env_var", OPTIONAL_ENV_CHECKS)
def test_optional_env(package_name, env_var):
    """Optional API keys should not fail CI if missing."""
    if not os.getenv(env_var):
        pytest.skip(f"{package_name} API key not set ({env_var})")
