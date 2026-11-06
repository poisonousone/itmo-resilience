FROM python:3.13.18-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1

COPY requirements-runtime.txt .

RUN pip install --no-cache-dir -r requirements-runtime.txt && useradd -u 10001 -m app

COPY --chown=10001:10001 src/ src/
COPY --chown=10001:10001 models/baseline.joblib models/baseline.sha256 models/

USER 10001:10001

CMD ["python", "-c", "from src.predict import predict; print(predict('What is machine learning?'))"]
