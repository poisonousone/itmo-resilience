
FROM python:3.13.18-slim-trixie

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1

COPY requirements-runtime.txt .

RUN pip install --no-cache-dir -r requirements-runtime.txt && useradd -u 10001 -m app

COPY --chown=10001:10001 src/ src/
COPY --chown=10001:10001 static/ static/
COPY --chown=10001:10001 models/baseline.joblib models/baseline.sha256 models/

USER 10001:10001

EXPOSE 8000

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]

