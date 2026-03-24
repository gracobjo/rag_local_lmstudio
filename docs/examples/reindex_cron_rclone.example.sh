#!/usr/bin/env bash
# Ejemplo: sincronizar una carpeta remota (rclone) y reindexar el RAG local.
# Copia y adapta rutas, remoto rclone y usuario. No ejecutar como root sin revisar permisos.
#
# Uso manual:
#   chmod +x reindex_cron_rclone.example.sh
#   ./reindex_cron_rclone.example.sh
#
# O bien desde cron (crontab -e), después de ajustar rutas:
#   15 2 * * * /ruta/absoluta/a/rag_project/docs/examples/reindex_cron_rclone.example.sh >> /var/log/rag_sync.log 2>&1

set -euo pipefail

RAG_ROOT="${RAG_ROOT:-/ruta/al/rag_project}"
RCLONE_REMOTE="${RCLONE_REMOTE:-mi_remote:documentacion}"
LOCAL_SYNC="${LOCAL_SYNC:-$RAG_ROOT/docs}"

export PATH="/usr/local/bin:/usr/bin:$PATH"

if command -v rclone >/dev/null 2>&1; then
  rclone sync "$RCLONE_REMOTE" "$LOCAL_SYNC"
else
  echo "rclone no está instalado; omite este paso o instala rclone." >&2
fi

cd "$RAG_ROOT"
if [[ -f venv/bin/activate ]]; then
  # shellcheck source=/dev/null
  source venv/bin/activate
fi
exec python reindex.py --path "$LOCAL_SYNC"
