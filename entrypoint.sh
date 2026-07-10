#!/bin/sh
set -e

# Aplica as migrations pendentes no banco (idempotente: se já estiver
# na versão mais recente, o alembic não faz nada).
echo "==> Verificando/aplicando migrations do banco (alembic upgrade head)..."
alembic upgrade head

echo "==> Iniciando API na porta ${PORT}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
