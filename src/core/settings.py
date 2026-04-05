"""Cấu hình tập trung: JSON trong configs/ + biến môi trường (.env)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_app_json() -> dict:
    path = project_root() / "configs" / "app.json"
    if not path.is_file():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _bootstrap_dotenv() -> None:
    root = project_root()
    load_dotenv(root / "configs" / ".env")
    load_dotenv(root / ".env", override=True)


@dataclass(frozen=True)
class AppSettings:
    google_api_key: str | None
    mongo_uri: str
    mongo_db_name: str
    gemini_model: str
    embedding_model: str
    streamlit_page_title: str
    streamlit_page_icon: str
    streamlit_layout: str


@lru_cache
def get_settings() -> AppSettings:
    _bootstrap_dotenv()
    data = _load_app_json()
    st_cfg = data.get("streamlit", {}) or {}
    llm_cfg = data.get("llm", {}) or {}
    emb_cfg = data.get("embeddings", {}) or {}
    mongo_cfg = data.get("mongo", {}) or {}

    return AppSettings(
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        mongo_uri=os.getenv(
            "MONGO_URI", mongo_cfg.get("default_uri", "mongodb://localhost:27017/")
        ),
        mongo_db_name=os.getenv(
            "MONGO_DB_NAME", mongo_cfg.get("default_db_name", "smart_meal_db")
        ),
        gemini_model=llm_cfg.get("gemini_model", "gemini-2.5-flash"),
        embedding_model=emb_cfg.get(
            "sentence_transformer_model", "AITeamVN/Vietnamese_Embedding"
        ),
        streamlit_page_title=st_cfg.get("page_title", "SmartMeal WinMart AI"),
        streamlit_page_icon=st_cfg.get("page_icon", "🥗"),
        streamlit_layout=st_cfg.get("layout", "wide"),
    )
