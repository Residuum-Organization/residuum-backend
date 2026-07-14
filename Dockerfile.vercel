FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN chmod +x /app/entrypoint.sh

ENV PORT=8080
EXPOSE 8080

# O entrypoint roda "alembic upgrade head" (aplica migrations pendentes)
# antes de iniciar a API a cada nova versão que sobe.
CMD ["/app/entrypoint.sh"]
