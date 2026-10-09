"""HTTP-слой: тонкая обёртка над ядром."""
import logging

from fastapi import FastAPI

from app.config import load_rules
from app.schemas import TriageRequest, TriageResponse
from app.triage import run_triage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="AI Triage Service", version="0.1.0")
RULES = load_rules()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/triage", response_model=TriageResponse)
def triage(request: TriageRequest) -> TriageResponse:
    response, _error = run_triage(request, RULES)
    return response
