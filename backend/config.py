import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Paths
    BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
    
    _env_db_path    = os.getenv('DB_PATH', '../data/journal.db')
    DB_PATH         = os.path.normpath(os.path.join(BASE_DIR, _env_db_path)) if not os.path.isabs(_env_db_path) else _env_db_path
    
    _env_storage    = os.getenv('STORAGE_PATH', '../storage/charts')
    STORAGE_PATH    = os.path.normpath(os.path.join(BASE_DIR, _env_storage)) if not os.path.isabs(_env_storage) else _env_storage

    # LLM (Groq / OpenAI-compatible)
    LLM_BASE_URL    = os.getenv('LLM_BASE_URL', 'https://api.groq.com/openai/v1')
    LLM_API_KEY     = os.getenv('LLM_API_KEY', '')
    LLM_MODEL       = os.getenv('LLM_MODEL', 'deepseek-r1-distill-llama-70b')

    # External APIs
    POLYGON_API_KEY = os.getenv('POLYGON_API_KEY', '')
    SEC_USER_AGENT  = os.getenv('SEC_USER_AGENT', 'TradingJournal trader@example.com')
    
    # Vision API (OpenAI-compatible)
    VISION_BASE_URL = os.getenv('VISION_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta/openai/')
    VISION_API_KEY  = os.getenv('VISION_API_KEY', os.getenv('GEMINI_API_KEY', ''))
    VISION_MODEL    = os.getenv('VISION_MODEL', 'gemini-1.5-pro')

    # Upload limits
    MAX_UPLOAD_BYTES    = 10 * 1024 * 1024   # 10 MB
    ALLOWED_MIME_TYPES  = {'image/png', 'image/jpeg', 'image/jpg', 'image/webp'}
    ALLOWED_EXTENSIONS  = {'png', 'jpg', 'jpeg', 'webp'}

    # SMTP / Notifications
    SMTP_SERVER         = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT           = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USER           = os.getenv('SMTP_USER', '')
    SMTP_PASSWORD       = os.getenv('SMTP_PASSWORD', '')
    NOTIFY_EMAIL        = os.getenv('NOTIFY_EMAIL', '')
