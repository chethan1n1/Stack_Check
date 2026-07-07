import os

class Settings:
    PROJECT_NAME: str = "StackCheck Data Validation Platform"
    API_V1_STR: str = "/api/v1"
    
    # Base directory of the project
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Uploads, reports, and profiles directories
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.join(BASE_DIR, "uploads"))
    REPORT_DIR: str = os.getenv("REPORT_DIR", os.path.join(BASE_DIR, "reports"))
    PROFILE_DIR: str = os.getenv("PROFILE_DIR", os.path.join(BASE_DIR, "profiles"))
    LOG_DIR: str = os.getenv("LOG_DIR", os.path.join(BASE_DIR, "logs"))
    
    # Database Configuration (Defaults to SQLite in project root)
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'stackcheck.db')}")
    
    # CORS Origins
    CORS_ORIGINS: list[str] = ["*"]

settings = Settings()

# Ensure directories exist
for folder in [settings.UPLOAD_DIR, settings.REPORT_DIR, settings.PROFILE_DIR, settings.LOG_DIR]:
    os.makedirs(folder, exist_ok=True)
