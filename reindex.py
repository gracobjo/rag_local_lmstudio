#!/usr/bin/env python3
"""
Reindexación por línea de comandos (cron, systemd, tras rclone/sync a disco).

No requiere Streamlit ni LM Studio: solo embeddings locales + Chroma.

Ejemplos::

    ./reindex.py --path ./docs
    ./reindex.py --path /datos/manual_sync --replace
    ./reindex.py --path ./docs --merge --db ./chroma_db
"""
from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    parser = argparse.ArgumentParser(
        description="Indexa una carpeta en el vector store Chroma (misma lógica que la app Streamlit)."
    )
    parser.add_argument(
        "--path",
        required=True,
        help="Carpeta con PDF/TXT/MD/DOCX (ruta absoluta o relativa al cwd).",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Solo archivos en el primer nivel (por defecto se incluyen subcarpetas).",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Añadir fragmentos al índice existente. Por defecto se **reemplaza** el índice (fuente única de verdad).",
    )
    parser.add_argument(
        "--db",
        dest="persist_directory",
        default=os.environ.get("RAG_CHROMA_PATH"),
        help="Directorio del índice Chroma (por defecto: variable RAG_CHROMA_PATH o ./chroma_db como en rag_chain_lm).",
    )

    args = parser.parse_args()
    reemplazar = not bool(args.merge)

    from office_docs import indexar_carpeta_en_sistema
    from rag_chain_lm import DB_PATH

    persist = args.persist_directory or DB_PATH

    try:
        n_chunks, n_files = indexar_carpeta_en_sistema(
            args.path,
            recursivo=not args.no_recursive,
            reemplazar=reemplazar,
            persist_directory=persist,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Error al indexar: {e}", file=sys.stderr)
        return 1

    print(
        f"Listo: {n_chunks} fragmentos desde {n_files} archivos → índice en {os.path.abspath(persist)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
