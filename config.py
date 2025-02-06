# config.py

import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load environment variables from .env file
load_dotenv()

class Config:
    DEBUG = True
    SECRET_KEY = 'your-secret-key'
    DATA_FOLDER = 'data'
    CANDIDATES_FILE = 'data/candidates.json'
    UPLOAD_FOLDER = 'candidates'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB file size limit
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg'}
    # PDFKit configuration (if using wkhtmltopdf)
    PDF_CONFIG = {
        'wkhtmltopdf': '/usr/local/bin/wkhtmltopdf'  # Update this path as needed
    }
    # App Secrets and API Keys
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
    STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY', '')
    PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY', '')
    PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY', '')
    PAYSTACK_BASE_URL = os.getenv('PAYSTACK_BASE_URL', '')
    SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', '')
    DEEPSEEK_API = os.getenv('DEEPSEEK_API', '')
