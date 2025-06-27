import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Configurações centralizadas da aplicação."""
    
    # Telegram
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    
    # Groq API
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///sara_bot.db")
    
    # Bot Configuration
    BOT_NAME: str = "Sara"
    BOT_USERNAME: str = "@sara_assistant_bot"
    
    # Job Queue
    JOB_QUEUE_ENABLED: bool = True
    
    # Timezone
    DEFAULT_TIMEZONE: str = "America/Sao_Paulo"
    
    # Whisper Model
    WHISPER_MODEL: str = "whisper-large-v3-turbo"
    
    # LLM Model
    LLM_MODEL: str = "llama3-70b-8192"
    
    # Shortcuts
    SHORTCUT_BASE_NAME: str = "CriarLembrete"
    
    @classmethod
    def validate(cls) -> None:
        """Valida se todas as configurações necessárias estão presentes."""
        if not cls.TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN é obrigatório")
        if not cls.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY é obrigatório")

# Instância global das configurações
settings = Settings()
settings.validate()