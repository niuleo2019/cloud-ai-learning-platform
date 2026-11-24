from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    port: int = 3000
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "vocab_app"
    jwt_secret: str = "dev_secret"
    jwt_expires_in: str = "7d"
    # AI learning assistant (Claude API). The key is read from ANTHROPIC_API_KEY.
    anthropic_api_key: str = ""
    agent_model: str = "claude-opus-5-5"
    agent_effort: str = "low"
    # Listening practice: local Whisper speech recognition (faster-whisper, CPU).
    whisper_model: str = "small.en"
    whisper_models_dir: str = "/app/data/whisper-models"
    listening_audio_dir: str = "/app/data/listening-audio"
    listening_max_upload_mb: int = 80
    # Longman pronunciation audio (.mdd resource file from the LDOCE MDict dictionary).
    longman_mdd_path: str = "/app/data/longman.mdd"
    # Imported MDict dictionaries: one sub-folder per dictionary (.mdx + .mdd + css/js/images).
    dictionaries_dir: str = "/app/data/dictionaries"
    dictionary_max_upload_mb: int = 4096
    # Piper neural TTS voice for example sentences without a real recording.
    tts_voice_path: str = "/app/data/tts-voices/en_GB-alba-medium.onnx"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
