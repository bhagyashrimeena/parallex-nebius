"""PARALLAX Studio HTTP API and web application.

Run with `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from app.engine import (
    DEFAULT_MODEL, InspectionError, MAX_IMAGE_BYTES, MAX_IMAGES,
    inspect_with_nebius, load_and_normalize,
)

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=False)
DATA = Path(os.getenv("PARALLAX_DATA_DIR") or str(ROOT / "data")).resolve()
SESSIONS = DATA / "sessions"
SESSIONS.mkdir(parents=True, exist_ok=True)
STATIC = ROOT / "app" / "static"
app = FastAPI(title="PARALLAX Studio API", version="1.0.0", docs_url="/api/docs", redoc_url=None)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
ID_PATTERN = re.compile(r"^[a-f0-9]{24}$")
PHOTO_PATTERN = re.compile(r"^P-\d{2}$")
SESSION_TTL_SECONDS = 24 * 60 * 60
MAX_STORED_SESSIONS = 100
_guard = threading.Lock()
_events: dict[tuple[str, str], deque[float]] = {}
_analysis_slots = threading.BoundedSemaphore(2)
_last_cleanup = 0.0


def _limit(request: Request, action: str) -> None:
    """Bound anonymous demo traffic; counters reset when the process restarts."""
    ip = request.client.host if request.client else "unknown"
    checks = ([("upload:ip", ip, 20, 3600), ("upload:global", "all", 200, 86400)] if action == "upload" else
              [("analyze:ip", ip, 12, 3600), ("analyze:global", "all", 60, 86400)])
    now = time.monotonic()
    with _guard:
        queues = []
        for category, identity, maximum, window in checks:
            queue = _events.setdefault((category, identity), deque())
            while queue and now - queue[0] >= window:
                queue.popleft()
            if len(queue) >= maximum:
                retry = max(1, int(window - (now - queue[0])))
                raise HTTPException(429, "Demo request limit reached. Try again later.",
                                    headers={"Retry-After": str(retry)})
            queues.append(queue)
        for queue in queues:
            queue.append(now)


def _prune_sessions() -> None:
    """Remove expired anonymous cases, including their normalized photos."""
    now = time.time()
    root = SESSIONS.resolve()
    for folder in SESSIONS.iterdir():
        if not folder.is_dir() or not ID_PATTERN.fullmatch(folder.name):
            continue
        if folder.resolve().parent != root:
            continue
        try:
            if now - folder.stat().st_mtime > SESSION_TTL_SECONDS:
                shutil.rmtree(folder)
        except FileNotFoundError:
            pass


@app.middleware("http")
async def cleanup_middleware(request: Request, call_next):
    global _last_cleanup
    now = time.monotonic()
    with _guard:
        due = _last_cleanup == 0 or now - _last_cleanup > 3600
        if due:
            _last_cleanup = now
    if due:
        _prune_sessions()
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


class ReviewInput(BaseModel):
    finding_id: str = Field(max_length=20)
    status: str
    note: str = Field(default="", max_length=500)


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _folder(sid: str) -> Path:
    if not ID_PATTERN.fullmatch(sid):
        raise HTTPException(404, "Unknown inspection")
    folder = SESSIONS / sid
    if not folder.exists():
        raise HTTPException(404, "Unknown inspection")
    return folder


def _read(sid: str) -> dict:
    try:
        return json.loads((_folder(sid) / "session.json").read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise HTTPException(500, "Inspection record cannot be loaded") from exc


def _write(sid: str, record: dict) -> None:
    target = _folder(sid) / "session.json"
    temp = _folder(sid) / "session.tmp"
    temp.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(target)


def _public(record: dict) -> dict:
    # No filesystem paths or API secrets are exposed to the browser.
    return record


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", media_type="text/html")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "parallax", "nebius_configured": bool(os.getenv("NEBIUS_API_KEY")),
            "model": os.getenv("NEBIUS_MODEL", DEFAULT_MODEL)}


@app.post("/api/sessions", status_code=201)
async def new_session(
    request: Request,
    category: Annotated[str, Form()] = "Equipment & assets",
    objective: Annotated[str, Form()] = "Document visible condition and outstanding uncertainty",
    files: list[UploadFile] = File(...),
):
    _limit(request, "upload")
    _prune_sessions()
    if sum(1 for p in SESSIONS.iterdir() if p.is_dir() and ID_PATTERN.fullmatch(p.name)) >= MAX_STORED_SESSIONS:
        raise HTTPException(503, "Demo storage is temporarily full. Try again later.")
    if not (1 <= len(files) <= MAX_IMAGES):
        raise HTTPException(400, f"Upload 1 to {MAX_IMAGES} images per inspection.")
    if not category.strip() or not objective.strip() or len(category) > 80 or len(objective) > 500:
        raise HTTPException(400, "Enter a valid inspection category and objective.")
    processed: list[tuple[bytes, dict]] = []
    for file in files:
        if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(400, "Only JPEG, PNG and WebP images are accepted.")
        raw = await file.read(MAX_IMAGE_BYTES + 1)
        try:
            encoded, quality = load_and_normalize(raw)
        except InspectionError as exc:
            raise HTTPException(400, str(exc)) from exc
        processed.append((encoded, quality))
    sid = secrets.token_hex(12)
    folder = SESSIONS / sid
    folder.mkdir(parents=True, exist_ok=False)
    photos = []
    for i, (encoded, quality) in enumerate(processed, 1):
        pid = f"P-{i:02d}"
        name = f"{pid}.jpg"
        (folder / name).write_bytes(encoded)
        photos.append({"id": pid, "stored_name": name, "url": f"/api/sessions/{sid}/photos/{pid}",
                       "quality": quality})
    record = {"id": sid, "category": category.strip(), "objective": objective.strip(),
              "created_at": _stamp(), "status": "uploaded", "photos": photos,
              "result": None, "analysis_history": [], "activity": [{"at": _stamp(), "message": f"{len(photos)} image(s) registered as evidence."}]}
    _write(sid, record)
    return _public(record)


@app.post("/api/sessions/{sid}/photos")
async def add_followup_photo(sid: str, request: Request, files: list[UploadFile] = File(...)):
    """Append an evidence angle and retain the previous analysis in audit history."""
    _limit(request, "upload")
    record = _read(sid)
    existing = len(record["photos"])
    if not files or existing + len(files) > MAX_IMAGES:
        raise HTTPException(400, f"A case supports up to {MAX_IMAGES} photos in total.")
    staged = []
    for file in files:
        if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(400, "Only JPEG, PNG and WebP images are accepted.")
        raw = await file.read(MAX_IMAGE_BYTES + 1)
        try:
            staged.append(load_and_normalize(raw))
        except InspectionError as exc:
            raise HTTPException(400, str(exc)) from exc
    if record.get("result"):
        record.setdefault("analysis_history", []).append({"archived_at": _stamp(),
            "photo_count": existing, "result": record["result"]})
        record["result"] = None
    for offset, (encoded, quality) in enumerate(staged, 1):
        pid = f"P-{existing + offset:02d}"
        name = f"{pid}.jpg"
        (_folder(sid) / name).write_bytes(encoded)
        record["photos"].append({"id": pid, "stored_name": name,
            "url": f"/api/sessions/{sid}/photos/{pid}", "quality": quality})
    record["status"] = "awaiting_reanalysis"
    record["activity"].append({"at": _stamp(), "message": f"{len(staged)} follow-up photo(s) added; model results must be refreshed."})
    _write(sid, record)
    return _public(record)


@app.get("/api/sessions/{sid}")
def get_session(sid: str):
    return _public(_read(sid))


@app.get("/api/sessions/{sid}/photos/{pid}")
def get_photo(sid: str, pid: str):
    record = _read(sid)
    if not PHOTO_PATTERN.fullmatch(pid) or pid not in {p["id"] for p in record["photos"]}:
        raise HTTPException(404, "Photo not found")
    return FileResponse(_folder(sid) / f"{pid}.jpg", media_type="image/jpeg",
                        headers={"Cache-Control": "private, max-age=600"})


@app.post("/api/sessions/{sid}/analyze")
async def analyze(sid: str, request: Request):
    record = _read(sid)
    if not os.getenv("NEBIUS_API_KEY"):
        raise HTTPException(503, "NEBIUS_API_KEY is missing; live AI analysis is disabled. Use the clearly marked sample case to explore offline.")
    _limit(request, "analyze")
    if not _analysis_slots.acquire(blocking=False):
        raise HTTPException(429, "Live analysis is busy. Try again shortly.", headers={"Retry-After": "30"})
    try:
        result = await inspect_with_nebius(record, _folder(sid))
    except InspectionError as exc:
        raise HTTPException(502, str(exc)) from exc
    finally:
        _analysis_slots.release()
    if record.get("result"):
        record.setdefault("analysis_history", []).append({"archived_at": _stamp(), "photo_count": len(record["photos"]), "result": record["result"]})
    record["result"] = result
    record["status"] = "human_review_required"
    record["activity"].append({"at": _stamp(), "message": f"Live Nebius analysis completed using {result['model']} (2 inference requests)."})
    _write(sid, record)
    return _public(record)


@app.post("/api/sessions/{sid}/review")
def review(sid: str, review_data: ReviewInput):
    record = _read(sid)
    if not record["result"]:
        raise HTTPException(409, "Run the inspection first.")
    if review_data.status not in {"confirmed", "rejected", "needs_more_evidence"}:
        raise HTTPException(400, "Invalid review status")
    match = next((item for item in record["result"]["findings"] if item["id"] == review_data.finding_id), None)
    if match is None:
        raise HTTPException(404, "Finding does not exist")
    match["review_status"] = review_data.status
    match["review_note"] = review_data.note.strip()
    record["activity"].append({"at": _stamp(), "message": f"Human review: {match['id']} marked {review_data.status}."})
    _write(sid, record)
    return _public(record)


@app.get("/api/sessions/{sid}/export")
def export_session(sid: str):
    record = _read(sid)
    return JSONResponse(record, headers={"Content-Disposition": f'attachment; filename="parallax-{sid}.json"'})


@app.get("/api/demo")
def get_demo():
    """A local synthetic fixture, never masquerading as an AI inference."""
    sid = "demo"
    return {
        "id": sid, "category": "Equipment & assets", "objective": "Evaluate visible casing damage before handover",
        "created_at": "2026-10-28T00:00:00+00:00", "status": "sample_fixture",
        "photos": [{"id": "P-01", "url": "/static/demo-equipment.jpg", "quality": {
            "width": 1200, "height": 850, "brightness": 128.1, "contrast": 40.2,
            "edge_signal": 27.4, "flags": [], "review": "Basic checks passed"}}],
        "result": {
            "summary": "Synthetic demonstration: the pictured housing has a visible diagonal line near one corner. An additional close-up is needed to distinguish a superficial mark from a crack.",
            "findings": [{"id": "F-01", "title": "Unresolved casing line", "observation": "A dark diagonal mark appears on the housing near the upper-right fastener.",
                          "interpretation": "Could be a surface mark or a crack; this image alone cannot establish the cause.",
                          "priority": "unknown", "evidence_ids": ["P-01"], "review_status": "unreviewed", "review_note": ""}],
            "uncertainties": ["Cannot determine depth or material integrity from this single view.",
                              "No second angle available to validate the feature."],
            "rejected_claims": 0,
            "next_shot": {"title": "Capture an oblique close-up", "instruction": "Move 20–30 cm from the upper-right corner; shoot at 30–45° with diffuse side lighting, including the fastener for context.",
                          "reason": "Shows whether the diagonal feature has depth or changes with the light angle.",
                          "question": "Is the mark raised, recessed, or only discoloration?"},
            "mode": "sample_fixture", "model": "No inference performed", "provider": "Offline sample",
            "trace": [], "status": "human_review_required"},
        "activity": [{"at": "2026-10-28T00:00:00+00:00", "message": "Loaded a clearly labeled synthetic fixture; no live model called."}]
    }


@app.exception_handler(404)
async def not_found_handler(request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Not found"}, status_code=404)
    return FileResponse(STATIC / "index.html", media_type="text/html")
