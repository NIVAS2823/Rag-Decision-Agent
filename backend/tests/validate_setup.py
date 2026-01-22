import sys
import os
from pathlib import Path


def print_header(title):
    """Print formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_section(name):
    """Decorator for test sections"""
    def decorator(func):
        def wrapper():
            print(f"\n▶ {name}")
            try:
                result = func()
                if result is None or result:
                    print(f"  ✅ PASS")
                    return True
                else:
                    print(f"  ❌ FAIL")
                    return False
            except Exception as e:
                print(f"  ❌ FAIL: {e}")
                return False
        return wrapper
    return decorator


# ============================================================================
# TEST SUITE
# ============================================================================

print_header("PHASE 1 FOUNDATION VALIDATION")
print("Testing all components installed in Steps 1.1 through 1.7")

results = []

# ----------------------------------------------------------------------------
# 1. PYTHON ENVIRONMENT
# ----------------------------------------------------------------------------
print_header("1. PYTHON ENVIRONMENT")

@test_section("Python version >= 3.11")
def test_python_version():
    version = sys.version_info
    assert version.major == 3 and version.minor >= 11
    print(f"     Python {version.major}.{version.minor}.{version.micro}")
    return True

results.append(test_python_version())

@test_section("Virtual environment activated")
def test_venv():
    venv_path = os.getenv("VIRTUAL_ENV")
    assert venv_path is not None
    print(f"     {venv_path}")
    return True

results.append(test_venv())

# ----------------------------------------------------------------------------
# 2. PROJECT STRUCTURE
# ----------------------------------------------------------------------------
print_header("2. PROJECT STRUCTURE")

@test_section("Backend directory structure")
def test_structure():
    required_dirs = [
        "app",
        "app/api",
        "app/api/routes",
        "app/api/schemas",
        "app/api/dependencies",
        "app/core",
        "app/services",
        "app/services/agents",
        "app/services/rag",
        "app/services/auth",
        "app/services/database",
        "app/models",
        "app/utils",
        "tests",
    ]
    
    for dir_path in required_dirs:
        path = Path(dir_path)
        assert path.exists() and path.is_dir(), f"Missing: {dir_path}"
    
    print(f"     All {len(required_dirs)} required directories exist")
    return True

results.append(test_structure())

@test_section("Essential files present")
def test_files():
    required_files = [
        "requirements.txt",
        ".env.example",
        ".env",
        "app/core/config.py",
        "app/__init__.py",
    ]
    
    for file_path in required_files:
        path = Path(file_path)
        assert path.exists() and path.is_file(), f"Missing: {file_path}"
    
    print(f"     All {len(required_files)} essential files exist")
    return True

results.append(test_files())

# ----------------------------------------------------------------------------
# 3. CORE WEB FRAMEWORK
# ----------------------------------------------------------------------------
print_header("3. CORE WEB FRAMEWORK")

@test_section("FastAPI")
def test_fastapi():
    import fastapi
    print(f"     Version: {fastapi.__version__}")
    return True

results.append(test_fastapi())

@test_section("Uvicorn")
def test_uvicorn():
    import uvicorn
    print(f"     Version: {uvicorn.__version__}")
    return True

results.append(test_uvicorn())

@test_section("Pydantic")
def test_pydantic():
    import pydantic
    print(f"     Version: {pydantic.__version__}")
    return True

results.append(test_pydantic())

# ----------------------------------------------------------------------------
# 4. AGENTIC AI STACK
# ----------------------------------------------------------------------------
print_header("4. AGENTIC AI STACK")

@test_section("LangChain")
def test_langchain():
    import langchain
    print(f"     Version: {langchain.__version__}")
    return True

results.append(test_langchain())

@test_section("LangGraph")
def test_langgraph():
    import langgraph
    from langgraph.graph import StateGraph
    print(f"     ✓ StateGraph available")
    return True

results.append(test_langgraph())

@test_section("LangSmith")
def test_langsmith():
    import langsmith
    print(f"     Version: {langsmith.__version__}")
    return True

results.append(test_langsmith())

# ----------------------------------------------------------------------------
# 5. LLM PROVIDERS
# ----------------------------------------------------------------------------
print_header("5. LLM PROVIDERS")

@test_section("OpenAI")
def test_openai():
    import openai
    print(f"     Version: {openai.__version__}")
    return True

results.append(test_openai())

@test_section("GROQ")
def test_groq():
    import groq
    print(f"     Version: {groq.__version__}")
    return True

results.append(test_groq())

# ----------------------------------------------------------------------------
# 6. RAG COMPONENTS
# ----------------------------------------------------------------------------
print_header("6. RAG COMPONENTS")

@test_section("FAISS (Vector Store)")
def test_faiss():
    import faiss
    # Test basic FAISS functionality
    import numpy as np
    d = 64  # dimension
    nb = 100  # database size
    np.random.seed(1234)
    xb = np.random.random((nb, d)).astype('float32')
    index = faiss.IndexFlatL2(d)
    index.add(xb)
    assert index.ntotal == nb
    print(f"     ✓ FAISS working (test index created)")
    return True

results.append(test_faiss())

@test_section("Sentence Transformers")
def test_sentence_transformers():
    from sentence_transformers import SentenceTransformer
    print(f"     ✓ SentenceTransformer available")
    return True

results.append(test_sentence_transformers())

@test_section("BM25 (Keyword Search)")
def test_bm25():
    from rank_bm25 import BM25Okapi
    # Test basic BM25 functionality
    corpus = [
        "Hello there good man!",
        "It is quite windy in London",
        "How is the weather today?"
    ]
    tokenized_corpus = [doc.split(" ") for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    query = "windy London"
    tokenized_query = query.split(" ")
    scores = bm25.get_scores(tokenized_query)
    assert len(scores) == len(corpus)
    print(f"     ✓ BM25 working (test search completed)")
    return True

results.append(test_bm25())

@test_section("Document Processing")
def test_document_processing():
    import pypdf
    import docx
    import tiktoken
    print(f"     ✓ PyPDF, python-docx, tiktoken available")
    return True

results.append(test_document_processing())

# ----------------------------------------------------------------------------
# 7. DATABASES
# ----------------------------------------------------------------------------
print_header("7. DATABASES")

@test_section("Motor (Async MongoDB)")
def test_motor():
    import motor.motor_asyncio
    print(f"     ✓ Motor available")
    return True

results.append(test_motor())

@test_section("Redis")
def test_redis():
    import redis
    print(f"     Version: {redis.__version__}")
    return True

results.append(test_redis())

# ----------------------------------------------------------------------------
# 8. AUTHENTICATION & SECURITY
# ----------------------------------------------------------------------------
print_header("8. AUTHENTICATION & SECURITY")

@test_section("JWT (python-jose)")
def test_jwt():
    from jose import jwt
    # Test basic JWT functionality
    secret = "test-secret-key"
    payload = {"sub": "test-user", "exp": 9999999999}
    token = jwt.encode(payload, secret, algorithm="HS256")
    decoded = jwt.decode(token, secret, algorithms=["HS256"])
    assert decoded["sub"] == "test-user"
    print(f"     ✓ JWT encoding/decoding working")
    return True

results.append(test_jwt())

@test_section("Password Hashing (passlib)")
def test_passlib():
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    password = "test_password_123"
    hashed = pwd_context.hash(password)
    assert pwd_context.verify(password, hashed)
    print(f"     ✓ Password hashing/verification working")
    return True

results.append(test_passlib())

# ----------------------------------------------------------------------------
# 9. EXTERNAL APIS
# ----------------------------------------------------------------------------
print_header("9. EXTERNAL APIS")

@test_section("Tavily (Web Search)")
def test_tavily():
    from tavily import TavilyClient
    print(f"     ✓ TavilyClient available")
    return True

results.append(test_tavily())

@test_section("Boto3 (Cloud Storage)")
def test_boto3():
    import boto3
    print(f"     Version: {boto3.__version__}")
    return True

results.append(test_boto3())

@test_section("HTTPX (Async HTTP)")
def test_httpx():
    import httpx
    print(f"     Version: {httpx.__version__}")
    return True

results.append(test_httpx())

# ----------------------------------------------------------------------------
# 10. CONFIGURATION SYSTEM
# ----------------------------------------------------------------------------
print_header("10. CONFIGURATION SYSTEM")

@test_section("Environment variables loaded")
def test_env_loading():
    from dotenv import load_dotenv
    result = load_dotenv()
    print(f"     ✓ .env file {'loaded' if result else 'already loaded'}")
    return True

results.append(test_env_loading())

@test_section("Pydantic Settings")
def test_pydantic_settings():
    from app.core.config import settings
    
    # Test required fields
    assert settings.SECRET_KEY
    assert settings.JWT_SECRET_KEY
    assert len(settings.SECRET_KEY) >= 32
    assert len(settings.JWT_SECRET_KEY) >= 32
    
    # Test computed properties
    assert hasattr(settings, 'is_development')
    assert hasattr(settings, 'is_production')
    
    print(f"     ✓ Settings loaded and validated")
    print(f"       App: {settings.APP_NAME}")
    print(f"       Environment: {settings.ENVIRONMENT}")
    print(f"       Debug: {settings.DEBUG}")
    return True

results.append(test_pydantic_settings())

@test_section("Configuration caching")
def test_config_caching():
    from app.core.config import get_settings
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2  # Same instance
    print(f"     ✓ Settings properly cached (singleton pattern)")
    return True

results.append(test_config_caching())

# ----------------------------------------------------------------------------
# 11. UTILITIES
# ----------------------------------------------------------------------------
print_header("11. UTILITIES")

@test_section("Logging (loguru)")
def test_loguru():
    from loguru import logger
    print(f"     ✓ Loguru logger available")
    return True

results.append(test_loguru())

@test_section("Retry logic (tenacity)")
def test_tenacity():
    from tenacity import retry, stop_after_attempt
    
    @retry(stop=stop_after_attempt(3))
    def test_func():
        return True
    
    assert test_func()
    print(f"     ✓ Tenacity retry decorator working")
    return True

results.append(test_tenacity())

# ----------------------------------------------------------------------------
# 12. TESTING FRAMEWORK
# ----------------------------------------------------------------------------
print_header("12. TESTING FRAMEWORK")

@test_section("Pytest")
def test_pytest():
    import pytest
    print(f"     Version: {pytest.__version__}")
    return True

results.append(test_pytest())

@test_section("Pytest Async")
def test_pytest_asyncio():
    import pytest_asyncio
    print(f"     ✓ Async testing support available")
    return True

results.append(test_pytest_asyncio())

# ----------------------------------------------------------------------------
# 13. EVALUATION
# ----------------------------------------------------------------------------
print_header("13. EVALUATION FRAMEWORK")

@test_section("DeepEval")
def test_deepeval():
    import deepeval
    print(f"     Version: {deepeval.__version__}")
    return True

results.append(test_deepeval())

# ----------------------------------------------------------------------------
# FINAL RESULTS
# ----------------------------------------------------------------------------
print_header("VALIDATION RESULTS")

total_tests = len(results)
passed_tests = sum(results)
failed_tests = total_tests - passed_tests

print(f"\n  Total Tests: {total_tests}")
print(f"  Passed: {passed_tests} ✅")
print(f"  Failed: {failed_tests} ❌")
print(f"  Success Rate: {(passed_tests/total_tests)*100:.1f}%")

print("\n" + "=" * 70)

if all(results):
    print("  🎉 ALL TESTS PASSED - PHASE 1 COMPLETE!")
    print("  ✅ Foundation is solid and ready for Phase 2")
    print("=" * 70)
    sys.exit(0)
else:
    print("  ⚠️  SOME TESTS FAILED")
    print("  Please review the errors above before proceeding")
    print("=" * 70)
    sys.exit(1)