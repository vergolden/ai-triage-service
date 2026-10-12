FROM python:3.12-slim

# Не писать .pyc и сразу выводить логи в консоль контейнера
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Зависимости - отдельным слоем: пока requirements.txt не меняется, пересборка быстрая
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY config ./config

# Обычный пользователь вместо root; /data - место для базы
RUN useradd --create-home appuser \
    && mkdir /data \
    && chown appuser /data
USER appuser

# База лежит в томе: контейнер можно удалить, обращения останутся.
# Ключ ProxyAPI в образ НЕ вшит: он передаётся при запуске (docker run --env-file .env).
ENV DATABASE_URL=sqlite:////data/triage.db
VOLUME /data

EXPOSE 8000

# 1 worker: SQLite-файл и лимит по таблице tickets; для учебного сервиса достаточно
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
