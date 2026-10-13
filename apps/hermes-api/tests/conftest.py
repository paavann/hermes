import os


os.environ.setdefault("DB_PASSWORD", "mock_test_password")
os.environ.setdefault("API_PORT", "8000")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USER", "mock_user")
os.environ.setdefault("DB_NAME", "mock_db")
os.environ.setdefault("LLM_API", "mock-llm-key")
os.environ.setdefault("LLM_MODEL", "mistral/ministral-8b-latest")
os.environ.setdefault("LLM_API_1", "mock-fallback-key")
os.environ.setdefault("LLM_MODEL_1", "nvidia_nim/meta/llama-3.1-70b-instruct")
