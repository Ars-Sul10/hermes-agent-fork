from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class AgentCoreConfig:
    # LLM
    openrouter_api_key: str
    openrouter_base_url: str
    llm_model: str

    # Aquera
    aquera_base_url: str
    aquera_api_token: str
    aquera_auth_mode: str
    aquera_timeout_seconds: float
    aquera_max_retries: int

    # AgentCore Runtime
    host: str
    port: int
    log_level: str

    @classmethod
    def from_env(cls) -> AgentCoreConfig:
        return cls(
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            openrouter_base_url=os.getenv(
                "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
            ),
            llm_model=os.getenv("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct"),
            aquera_base_url=os.getenv("AQUERA_BASE_URL", "http://localhost:3000"),
            aquera_api_token=os.getenv("AQUERA_API_TOKEN", ""),
            aquera_auth_mode=os.getenv("AQUERA_AUTH_MODE", "bearer"),
            aquera_timeout_seconds=float(os.getenv("AQUERA_TIMEOUT_SECONDS", "30")),
            aquera_max_retries=int(os.getenv("AQUERA_MAX_RETRIES", "3")),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8080")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
