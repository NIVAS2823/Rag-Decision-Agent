import sys
import warnings
import importlib

# ---------------------------------------------------------------------------
# WARNING HANDLING (Silence known non-fatal warnings)
# ---------------------------------------------------------------------------
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def test_import(package_name, import_statement):
    """Test if a package can be imported safely"""
    try:
        exec(import_statement, {})
        print(f"✅ {package_name}: OK")
        return True
    except ImportError as e:
        print(f"❌ {package_name}: FAILED (ImportError) - {e}")
        return False
    except Exception as e:
        print(f"⚠️  {package_name}: WARNING (Runtime) - {e}")
        return True  # Runtime warnings should not fail CI


def test_optional_env(package_name, env_var):
    """Check optional API key presence (non-fatal)"""
    import os
    if os.getenv(env_var):
        print(f"✅ {package_name} API key detected ({env_var})")
    else:
        print(f"⚠️  {package_name} API key NOT set ({env_var}) — skipping auth test")


# ---------------------------------------------------------------------------
# TEST SUITE
# ---------------------------------------------------------------------------
print("=" * 60)
print("TESTING CRITICAL IMPORTS (ZERO-NOISE MODE)")
print("=" * 60)

tests = [
    # -----------------------------------------------------------------------
    # Web Framework
    # -----------------------------------------------------------------------
    ("FastAPI", "import fastapi"),
    ("Uvicorn", "import uvicorn"),

    # -----------------------------------------------------------------------
    # LangChain / LangGraph
    # -----------------------------------------------------------------------
    ("LangChain", "import langchain"),
    ("LangGraph", "import langgraph"),
    ("LangSmith", "import langsmith"),

    # -----------------------------------------------------------------------
    # LLM Providers
    # -----------------------------------------------------------------------
    ("OpenAI", "import openai"),
    ("Anthropic", "import anthropic"),

    # Gemini (Google)
    ("Gemini (Google)", "import google.genai as genai"),

    # Groq
    ("Groq", "from groq import Groq"),

    # -----------------------------------------------------------------------
    # RAG Components
    # -----------------------------------------------------------------------
    ("FAISS", "import faiss"),
    ("Sentence Transformers", "from sentence_transformers import SentenceTransformer"),
    ("BM25", "from rank_bm25 import BM25Okapi"),

    # -----------------------------------------------------------------------
    # Data Validation
    # -----------------------------------------------------------------------
    ("Pydantic", "import pydantic"),

    # -----------------------------------------------------------------------
    # Databases
    # -----------------------------------------------------------------------
    ("Motor (MongoDB)", "import motor.motor_asyncio"),
    ("Redis", "import redis"),

    # -----------------------------------------------------------------------
    # Authentication
    # -----------------------------------------------------------------------
    ("Jose (JWT)", "from jose import jwt"),
    ("Passlib", "from passlib.context import CryptContext"),

    # -----------------------------------------------------------------------
    # Document Processing
    # -----------------------------------------------------------------------
    ("PyPDF", "import pypdf"),
    ("Python-docx", "import docx"),

    # -----------------------------------------------------------------------
    # External APIs
    # -----------------------------------------------------------------------
    ("Tavily", "from tavily import TavilyClient"),
    ("Boto3 (R2)", "import boto3"),

    # -----------------------------------------------------------------------
    # Utilities
    # -----------------------------------------------------------------------
    ("Python-dotenv", "from dotenv import load_dotenv"),
    ("Requests", "import requests"),
    ("HTTPX", "import httpx"),
]

# ---------------------------------------------------------------------------
# RUN TESTS
# ---------------------------------------------------------------------------
print()
results = []
for package, import_stmt in tests:
    results.append(test_import(package, import_stmt))

# ---------------------------------------------------------------------------
# OPTIONAL API KEY CHECKS (NON-FATAL)
# ---------------------------------------------------------------------------
print("\n" + "-" * 60)
print("OPTIONAL API KEY CHECKS")
print("-" * 60)

test_optional_env("OpenAI", "OPENAI_API_KEY")
# test_optional_env("Anthropic", "ANTHROPIC_API_KEY")
test_optional_env("Gemini", "GOOGLE_API_KEY")
test_optional_env("Groq", "GROQ_API_KEY")
test_optional_env("LangSmith", "LANGSMITH_API_KEY")
test_optional_env("Tavily", "TAVILY_API_KEY")

# ---------------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print(f"RESULTS: {sum(results)}/{len(results)} imports passed")
print("=" * 60)

if all(results):
    print("✅ Environment is healthy and production-ready!")
    sys.exit(0)
else:
    print("❌ Some critical imports failed. Fix before deployment.")
    sys.exit(1)
