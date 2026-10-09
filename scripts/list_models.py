"""Показывает, какие модели OpenAI доступны по вашему ключу ProxyAPI.
Запуск: ./venv/bin/python scripts/list_models.py   (ключ берётся из .env, на экран не выводится)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import openai

from app import config

client = openai.OpenAI(api_key=config.api_key(), base_url=config.openai_base_url())
ids = sorted(m.id for m in client.models.list())
print(f"Всего моделей: {len(ids)}")
for model_id in ids:
    if "gpt" in model_id:
        print(model_id)
