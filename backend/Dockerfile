FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

ARG SOURCE_VERSION=local
LABEL org.opencontainers.image.revision=$SOURCE_VERSION

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

COPY . .

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -m app.cli.bootstrap_admin && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
