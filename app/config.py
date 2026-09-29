import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(dotenv_path=BASE_DIR / ".env")

class Settings:
    BASE_DIR: Path = BASE_DIR
    PROJECT_NAME: str = "ComicCraft"
    PROJECT_DESCRIPTION: str = "AI Comic Story Creator using Gemini Models & Generative AI"
    VERSION: str = "1.0.0"

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    HF_API_KEY: str = os.getenv("HF_API_KEY", "")

    GEMINI_FLASH_MODEL: str = os.getenv("GEMINI_FLASH_MODEL", "gemini-1.5-flash")
    GEMINI_PRO_MODEL: str = os.getenv("GEMINI_PRO_MODEL", "gemini-1.5-pro")

    APP_HOST: str = os.getenv("APP_HOST", "127.0.0.1")
    APP_PORT: int = int(os.getenv("APP_PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")

    STATIC_DIR: Path = BASE_DIR / "static"
    PANELS_DIR: Path = STATIC_DIR / "panels"
    EXPORTS_DIR: Path = STATIC_DIR / "exports"
    IMAGES_DIR: Path = STATIC_DIR / "images"
    TEMPLATES_DIR: Path = BASE_DIR / "templates"

    def __init__(self):
        self.PANELS_DIR.mkdir(parents=True, exist_ok=True)
        self.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        self.IMAGES_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
