from __future__ import annotations

import os
from dataclasses import dataclass

from crewai import LLM
from dotenv import load_dotenv


@dataclass(slots=True)
class AppConfig:
    openai_base_url: str
    openai_api_key: str
    openai_model: str
    db_url: str | None
    temperature: float
    max_tokens: int


def load_config(db_url_override: str | None = None) -> AppConfig:
    load_dotenv()
    os.environ["CREWAI_TRACING_ENABLED"] = "false"
    return AppConfig(
        openai_base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:1234/v1"),
        openai_api_key=os.getenv("OPENAI_API_KEY", "local"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        db_url=db_url_override or os.getenv("DATABASE_URL"),
        temperature=float(os.getenv("TEMPERATURE", "0")),
        max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
    )


def build_crewai_llm(cfg: AppConfig) -> LLM:
    return LLM(
        model=f"{cfg.openai_model}",
        api_key=cfg.openai_api_key,
        base_url=cfg.openai_base_url,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
    )
