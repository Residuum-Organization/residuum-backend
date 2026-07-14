#!/bin/sh
set -e

echo "==> Iniciando API na porta ${PORT}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
