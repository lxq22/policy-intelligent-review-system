FROM python:3.12-slim

WORKDIR /app

# Keep dependency installation reliable on slower or intermittent networks.
ENV PIP_TIMEOUT=180 \
    PIP_RETRIES=10 \
    PIP_RESUME_RETRIES=10 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY pyproject.toml alembic.ini ./
COPY migrations ./migrations
COPY app ./app
RUN --mount=type=cache,target=/root/.cache/pip pip install .

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
