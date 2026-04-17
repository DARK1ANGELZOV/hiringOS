from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'HiringOS AI Service'
    app_debug: bool = False

    resume_llm_model_id: str = 'Qwen/Qwen2.5-0.5B-Instruct'
    interview_llm_model_id: str = 'Qwen/Qwen2.5-0.5B-Instruct'
    embedding_model_id: str = 'sentence-transformers/all-MiniLM-L6-v2'
    stt_model_id: str = 'openai/whisper-small'
    tts_model_id: str = 'microsoft/speecht5_tts'
    tts_vocoder_model_id: str = 'microsoft/speecht5_hifigan'
    tts_speaker_dataset_id: str = 'Matthijs/cmu-arctic-xvectors'
    tts_female_speaker_hint: str = 'slt'
    video_analysis_model_id: str = 'openai/clip-vit-base-patch32'
    hf_local_files_only: bool = True

    max_resume_chars: int = 16000


@lru_cache
def get_settings() -> Settings:
    return Settings()
