#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ -f venv/bin/activate ]]; then
  # shellcheck source=/dev/null
  source venv/bin/activate
fi
export LM_STUDIO_MODEL="${LM_STUDIO_MODEL:-meta-llama-3.1-8b-instruct}"
exec uvicorn api_service_lmstudio:app --reload --host 0.0.0.0 --port 8000
