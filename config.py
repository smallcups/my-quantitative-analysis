import os
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables
load_dotenv()


class Config:
    """Base configuration."""

    # Database settings
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
    DB_NAME = os.getenv('DB_NAME', 'stock_cursor')
    DB_CHARSET = os.getenv('DB_CHARSET', 'utf8mb4')

    # SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}?charset={DB_CHARSET}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }

    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

    # Redis settings
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))

    # Logging settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/stock_analysis.log')

    # Data update schedule
    DATA_UPDATE_HOUR = int(os.getenv('DATA_UPDATE_HOUR', 18))  # Update data daily at 18:00
    DATA_UPDATE_MINUTE = int(os.getenv('DATA_UPDATE_MINUTE', 0))

    # Alert settings
    EMAIL_SMTP_SERVER = os.getenv('EMAIL_SMTP_SERVER', 'smtp.qq.com')
    EMAIL_SMTP_PORT = int(os.getenv('EMAIL_SMTP_PORT', 587))
    EMAIL_USERNAME = os.getenv('EMAIL_USERNAME', '')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')

    # Pagination settings
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100

    # LLM settings
    LLM_CONFIG = {
        'provider': 'openai',  # Supported: 'ollama', 'openai', 'azure'
        'ollama': {
            'base_url': 'http://localhost:11434',
            'model': 'qwen2.5-coder:latest',
            'timeout': 60,
            'temperature': 0.1,
            'max_tokens': 2048
        },
        'openai': {
            'api_key': os.environ.get('OPENAI_API_KEY'),
            'model': 'qwen-coder-turbo-0919',
            'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
            'timeout': 60,
            'temperature': 0.1,
            'max_tokens': 2048
        }
    }


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


# Config mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
