#!/usr/bin/env bash
# Desenvolvimento: sobe os 2 backends (APIs) e serve o frontend separadamente.
#   Backend Admin :8000 · Backend Verificação :8001 · Frontend :3000
set -e
cd "$(dirname "$0")"
for d in admin-backend verificacao-backend; do
  [ -f "$d/.env" ] || { cp "$d/.env.example" "$d/.env"; echo "Criado $d/.env — EDITE as chaves antes de usar em produção."; }
  [ -d "$d/venv" ] || { python3 -m venv "$d/venv"; "$d/venv/bin/pip" install -q -r "$d/requirements.txt"; }
done
(cd verificacao-backend && set -a && . ./.env && set +a && exec venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001) &
(cd admin-backend && set -a && . ./.env && set +a && exec venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000) &
(cd frontend && exec python3 -m http.server 3000) &
echo "Frontend:    http://localhost:3000"
echo "API Admin:   http://localhost:8000/docs   |   API Verificação: http://localhost:8001/docs"
wait
