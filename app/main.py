"""HTTP-слой: тонкая обёртка над ядром."""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app import config, limiter, store
from app.config import load_rules
from app.schemas import TriageRequest, TriageResponse
from app.triage import run_triage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("triage.http")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    store.init_db()
    yield


app = FastAPI(title="AI Triage Service", version="0.2.0", lifespan=lifespan)
RULES = load_rules()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/triage", response_model=TriageResponse)
def triage(request: TriageRequest):
    wait = limiter.retry_after_seconds(request.client_id)
    if wait:
        return JSONResponse(
            status_code=429,
            content={"detail": f"Превышен лимит {config.rate_limit_per_minute()} запросов в минуту"},
            headers={"Retry-After": str(wait)},
        )

    started = time.monotonic()
    response, error = run_triage(request, RULES)
    latency_ms = int((time.monotonic() - started) * 1000)

    ticket = store.save_ticket(
        client_id=request.client_id, channel=request.channel, text=request.text,
        category=response.category, draft_reply=response.draft_reply,
        confidence=response.confidence, escalate=response.escalate,
        error=error, model=_model_label(), latency_ms=latency_ms,
    )
    # текст обращения в логи не пишем: только номер и длину
    log.info("ticket=%s len=%s category=%s escalate=%s", ticket.id, len(request.text), response.category, response.escalate)
    return response


def _model_label() -> str:
    try:
        return config.openai_model() if config.provider() == "openai" else config.model_name()
    except config.ConfigError:
        return ""
