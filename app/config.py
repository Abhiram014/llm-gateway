import os
from dotenv import load_dotenv

load_dotenv()  # reads .env and puts its values into environment variables

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")