import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_DIR = ROOT_DIR / "knowledge-base"
DATA_DIR = ROOT_DIR / "data"
ORDERS_PATH = DATA_DIR / "orders.json"
EVAL_DIR = ROOT_DIR / "evaluation"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
APP_NAME = os.getenv("APP_NAME", "AsterAndRowSupportAgent")
