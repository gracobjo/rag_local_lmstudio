"""
Apartado A (práctica RAG): carga PDF/TXT desde ./docs, trocea y persiste el vectorstore en ./chroma_db.

Ejecutar desde la raíz del proyecto: python ingest.py

Para indexación avanzada (MD/DOCX, carpetas recursivas, fusión), usar office_docs.py o reindex.py.
"""
from __future__ import annotations

import os

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader

from chroma_lm import chroma_from_documents, huggingface_embeddings

# Configuración de rutas según el documento de la práctica
DOCS_PATH = "./docs"
DB_PATH = "./chroma_db"


def cargar_documentos(ruta: str):
    """
    Carga archivos PDF y TXT desde la carpeta especificada (solo primer nivel).
    """
    documentos = []
    if not os.path.exists(ruta):
        print(f"Error: La carpeta {ruta} no existe.")
        return documentos

    for fichero in os.listdir(ruta):
        ruta_completa = os.path.join(ruta, fichero)
        loader = None

        if fichero.endswith(".pdf"):
            loader = PyPDFLoader(ruta_completa)
        elif fichero.endswith(".txt"):
            loader = TextLoader(ruta_completa, encoding="utf-8")
        else:
            print(f"Saltando archivo no compatible: {fichero}")
            continue

        if loader:
            print(f"Cargando: {fichero}")
            documentos.extend(loader.load())

    return documentos


def indexar(documentos):
    """
    Divide los documentos en trozos (chunks) y los guarda en ChromaDB (cliente persistente).
    chunk_size=500 y chunk_overlap=50 alineados con el enunciado de la práctica.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )

    chunks = splitter.split_documents(documentos)
    print(f"Documentos divididos en {len(chunks)} fragmentos.")

    embeddings = huggingface_embeddings()
    print("Creando base de datos vectorial en disco...")
    db = chroma_from_documents(chunks, DB_PATH, embeddings)

    print(f"¡Éxito! Indexados {len(chunks)} chunks en {DB_PATH}")
    return db


if __name__ == "__main__":
    print("Iniciando indexación (ingest.py)...")
    docs = cargar_documentos(DOCS_PATH)

    if len(docs) > 0:
        indexar(docs)
    else:
        print("No se encontraron documentos válidos en la carpeta ./docs")
