from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import DraftTask, ExtractRequest, RankedTask, RankRequest
from .extraction import ExtractionError, extract_tasks
from .ranking import rank_tasks

app = FastAPI(title="ClearStep")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


@app.post("/rank", response_model=list[RankedTask])
def rank(request: RankRequest):
    return rank_tasks(request.tasks, datetime.now(timezone.utc), ZoneInfo(request.timezone))


@app.post("/extract", response_model=list[DraftTask])
def extract(request: ExtractRequest):
    try:
        return extract_tasks(request)
    except ExtractionError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from None
