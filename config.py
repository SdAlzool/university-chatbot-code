import os
import json
import logging
import warnings
from dotenv import load_dotenv
from google import genai
import firebase_admin
from firebase_admin import credentials, firestore
from telegram.warnings import PTBUserWarning

warnings.filterwarnings("ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v21.0")
WHATSAPP_PORT = int(os.getenv("WHATSAPP_PORT") or os.getenv("PORT") or "8445")

ADMIN_TELEGRAM_IDS = {
    int(u.strip())
    for u in os.getenv("ADMIN_TELEGRAM_IDS", "").split(",")
    if u.strip().isdigit()
}

ADMIN_WHATSAPP_NUMBERS = {
    n.strip() for n in os.getenv("ADMIN_WHATSAPP_NUMBERS", "").split(",") if n.strip()
}

# Gemini model names — override via .env (FAST_MODEL / GEMINI_MODEL / INTENT_MODEL).
# 3-tier fallback chain (primary -> secondary -> local TF-IDF engine):
#   FAST_MODEL      : primary tier  (gemini-3.6-flash)
#   GEMINI_MODEL    : secondary tier (gemini-3.5-flash-lite)
#   INTENT_MODEL    : used for intent classification
FAST_MODEL = os.getenv("FAST_MODEL", "gemini-3.6-flash")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
INTENT_MODEL_NAME = os.getenv("INTENT_MODEL", "gemini-3.5-flash-lite")

client = genai.Client(api_key=GEMINI_KEY)

if not firebase_admin._apps:
    firebase_key_json = os.getenv("FIREBASE_KEY_JSON")
    if firebase_key_json and firebase_key_json.strip():
        try:
            cred = credentials.Certificate(json.loads(firebase_key_json))
            firebase_admin.initialize_app(cred)
            logging.info("Firebase initialized from FIREBASE_KEY_JSON env var")
        except Exception as e:
            logging.error("Failed to initialize Firebase from env var: %s", e)
    elif os.path.exists("firebase-key.json"):
        try:
            cred = credentials.Certificate("firebase-key.json")
            firebase_admin.initialize_app(cred)
            logging.info("Firebase initialized from firebase-key.json file")
        except Exception as e:
            logging.error("Failed to initialize Firebase from file: %s", e)
    else:
        logging.error("FIREBASE_KEY_JSON env var is empty AND firebase-key.json not found!")

db = firestore.client()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)