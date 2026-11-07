
import asyncio
import hashlib
import json
import logging
import os
import secrets
import time
import uuid
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from threading import BoundedSemaphore, Lock

import joblib
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from src.predict import validate_text

root = Path(__file__).resolve().parent.parent
model_file = root / "models" / "baseline.joblib"
hash_file = root / "models" / "baseline.sha256"

RATE_LIMIT = 10
WINDOW = 60
MAX_BODY = 32768
TIMEOUT = 3

rate_history = defaultdict(deque)
auth_failures = defaultdict(deque)
lock = Lock()
slots = BoundedSemaphore(2)
pool = ThreadPoolExecutor(max_workers=2)

requests_total = Counter("ml_api_requests_total", "API requests", ["route", "status"])
rejects_total = Counter("ml_api_rejections_total", "Rejected requests", ["reason"])
request_seconds = Histogram("ml_api_duration_seconds", "Response time", ["route"])
logger = logging.getLogger("uvicorn.error")


def load_checked_model():
    expected = hash_file.read_text().split()[0]
    actual = hashlib.sha256(model_file.read_bytes()).hexdigest()

    if not secrets.compare_digest(expected, actual):
        raise ValueError("Model SHA256 mismatch")

    return joblib.load(model_file), actual[:12]


@asynccontextmanager
async def lifespan(app):
    app.state.model = None
    app.state.version = "unavailable"

    try:
        app.state.model, app.state.version = load_checked_model()
    except Exception as exc: #noqa: BLE001
        logger.error("model_unavailable: %s", type(exc).__name__)

    yield


app = FastAPI(lifespan=lifespan)


def fail(request, status, reason, message):
    request.state.reason = reason
    raise HTTPException(status_code=status, detail=message)


def authenticate(request):
    expected = os.getenv("API_TOKEN", "")

    if not expected:
        fail(request, 503, "not_configured", "Service unavailable")

    supplied = request.headers.get("X-API-Key", "")

    if not secrets.compare_digest(supplied, expected):
        fail(request, 401, "auth", "Unauthorized")


def enforce_rate(request):
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()

    with lock:
        history = rate_history[ip]

        while history and now - history[0] > WINDOW:
            history.popleft()

        if len(history) >= RATE_LIMIT:
            fail(request, 429, "rate_limit", "Too many requests")

        history.append(now)


@app.middleware("http")
async def observe(request, call_next):
    request.state.request_id = uuid.uuid4().hex
    start = time.perf_counter()
    response = await call_next(request)

    route = request.url.path
    if route not in ("/", "/predict", "/health", "/metrics"):
        route = "other"

    status = str(response.status_code)
    requests_total.labels(route, status).inc()
    request_seconds.labels(route).observe(time.perf_counter() - start)

    reason = getattr(request.state, "reason", "none")

    if response.status_code >= 400:
        rejects_total.labels(reason).inc()

    if route == "/predict" and response.status_code == 401:
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()

        with lock:
            history = auth_failures[ip]

            while history and now - history[0] > 60:
                history.popleft()

            history.append(now)

            if len(history) == 3:
                logger.warning(json.dumps({
                    "event": "alert",
                    "rule": "3x401_in_60s",
                    "count": 3
                }))

    logger.info(json.dumps({
        "time": datetime.now(UTC).isoformat(),
        "request_id": request.state.request_id,
        "route": route,
        "status": response.status_code,
        "duration_ms": round((time.perf_counter() - start) * 1000, 2),
        "model_version": getattr(app.state, "version", "unavailable"),
        "reason": reason
    }))

    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.get("/")
def index():
    return FileResponse(root / "static" / "index.html")


@app.get("/health")
def health():
    if getattr(app.state, "model", None) is None or not os.getenv("API_TOKEN"):
        raise HTTPException(status_code=503, detail="Service unavailable")

    return {"status": "healthy", "model_version": app.state.version}


@app.get("/metrics")
def metrics(request: Request):
    authenticate(request)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/predict")
async def predict(request: Request):
    enforce_rate(request)
    authenticate(request)

    if getattr(app.state, "model", None) is None:
        fail(request, 503, "model_unavailable", "Service unavailable")

    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()

    if content_type != "application/json":
        fail(request, 415, "format", "Expected JSON")

    body = bytearray()

    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BODY:
            fail(request, 413, "body_size", "Request too large")
        body.extend(chunk)

    try:
        data = json.loads(body)
    except (ValueError, UnicodeError):
        fail(request, 400, "json", "Invalid JSON")

    if not isinstance(data, dict) or set(data) != {"text"}:
        fail(request, 422, "schema", "Expected field: text")

    try:
        text = validate_text(data["text"])
    except (TypeError, ValueError):
        status = 413 if isinstance(data["text"], str) and len(data["text"]) > 10000 else 422
        fail(request, status, "text", "Invalid text")

    if not slots.acquire(blocking=False):
        fail(request, 429, "concurrency", "Service busy")

    future = asyncio.get_running_loop().run_in_executor(
        pool, app.state.model.predict, [text]
    )
    future.add_done_callback(lambda _: slots.release())

    try:
        result = await asyncio.wait_for(asyncio.shield(future), timeout=TIMEOUT)
        label = int(result[0])
    except TimeoutError:
        fail(request, 503, "timeout", "Prediction timeout")

    return {
        "prediction": "INJECTION" if label == 1 else "BENIGN",
        "model_version": app.state.version,
        "request_id": request.state.request_id
    }

