FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FICTIONRAG_HOST=0.0.0.0 \
    FICTIONRAG_PORT=5000 \
    FICTIONRAG_VISITOR_DB_PATH=/app/data/runtime/visitor_usage.sqlite3

WORKDIR /app

RUN addgroup --system --gid 10001 app \
    && adduser --system --uid 10001 --ingroup app app

COPY requirements.txt requirements-prod.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt -r requirements-prod.txt

COPY src ./src
COPY frontend ./frontend

RUN mkdir -p data/novels data/index data/entities data/runtime \
    && chown -R app:app /app

VOLUME ["/app/data/runtime"]

USER app

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/' % os.getenv('FICTIONRAG_PORT', '5000'), timeout=3)" || exit 1

CMD ["sh", "-c", "gunicorn --bind ${FICTIONRAG_HOST:-0.0.0.0}:${FICTIONRAG_PORT:-5000} --workers ${GUNICORN_WORKERS:-2} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-180} --access-logfile - --error-logfile - src.app:app"]
