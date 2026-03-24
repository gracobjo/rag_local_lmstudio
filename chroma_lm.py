"""
Cliente Chroma persistente para LangChain.

Usa chromadb.PersistentClient en lugar de chromadb.Client(Settings): evita el error
«Could not connect to tenant default_tenant» con ciertos índices o versiones de la
librería al abrir ./chroma_db.
"""
from __future__ import annotations

import os
import shutil
import time
from typing import List

import chromadb
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document


def persist_path_abs(path: str) -> str:
    return os.path.abspath(os.path.expanduser(path))


def chroma_persistent_client(persist_directory: str) -> chromadb.ClientAPI:
    """Cliente local con tenant/base de datos por defecto correctamente inicializados."""
    return chromadb.PersistentClient(path=persist_path_abs(persist_directory))


def huggingface_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def langchain_chroma(
    persist_directory: str,
    embedding_function: HuggingFaceEmbeddings,
) -> Chroma:
    """Vector store LangChain sobre Chroma persistente."""
    p = persist_path_abs(persist_directory)
    return Chroma(
        client=chroma_persistent_client(p),
        embedding_function=embedding_function,
        persist_directory=p,
    )


def chroma_from_documents(
    documents: List[Document],
    persist_directory: str,
    embedding_function: HuggingFaceEmbeddings,
) -> Chroma:
    """Equivalente a Chroma.from_documents usando PersistentClient."""
    p = persist_path_abs(persist_directory)
    return Chroma.from_documents(
        documents=documents,
        embedding=embedding_function,
        client=chroma_persistent_client(p),
        persist_directory=p,
    )


def borrar_directorio_indice(persist_directory: str, max_intentos: int = 3) -> None:
    """Elimina el directorio del índice (p. ej. antes de reemplazar). Reintenta brevemente."""
    p = persist_path_abs(persist_directory)
    if not os.path.exists(p):
        return
    for intento in range(max_intentos):
        try:
            shutil.rmtree(p)
            return
        except OSError:
            if intento == max_intentos - 1:
                raise
            time.sleep(0.15)
