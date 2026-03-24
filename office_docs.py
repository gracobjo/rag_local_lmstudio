"""
Carga e indexación de documentación de oficina (carpeta única fuente de verdad).

Formatos: PDF, TXT, Markdown, DOCX (opcional). Recorre subcarpetas si se indica.
"""
from __future__ import annotations

import os
import shutil
from typing import Callable, List, Optional

from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Extensiones tratadas como documentación (no binarios genéricos)
EXTENSIONES_SOPORTADAS = {".pdf", ".txt", ".md", ".markdown", ".docx"}


def _cargar_docx(path: str) -> List[Document]:
    try:
        from langchain_community.document_loaders import Docx2txtLoader
    except ImportError:
        raise RuntimeError(
            "Para .docx instala: pip install docx2txt"
        ) from None
    return Docx2txtLoader(path).load()


def cargar_un_archivo(ruta: str) -> List[Document]:
    ext = os.path.splitext(ruta)[1].lower()
    if ext == ".pdf":
        return PyPDFLoader(ruta).load()
    if ext in (".txt", ".md", ".markdown"):
        return TextLoader(ruta, encoding="utf-8").load()
    if ext == ".docx":
        return _cargar_docx(ruta)
    raise ValueError(f"Extensión no soportada: {ext}")


def listar_archivos_documento(
    carpeta: str, recursivo: bool = True
) -> List[str]:
    """Rutas absolutas normalizadas de todos los archivos indexables."""
    base = os.path.realpath(carpeta)
    if not os.path.isdir(base):
        return []
    salida: List[str] = []
    if recursivo:
        for root, _dirs, files in os.walk(base):
            for name in files:
                ext = os.path.splitext(name)[1].lower()
                if ext in EXTENSIONES_SOPORTADAS:
                    salida.append(os.path.join(root, name))
    else:
        for name in os.listdir(base):
            p = os.path.join(base, name)
            if os.path.isfile(p):
                ext = os.path.splitext(name)[1].lower()
                if ext in EXTENSIONES_SOPORTADAS:
                    salida.append(p)
    salida.sort()
    return salida


def cargar_carpeta(
    carpeta: str,
    recursivo: bool = True,
    progreso: Optional[Callable[[int, int, str], None]] = None,
) -> List[Document]:
    """
    Carga todos los documentos admitidos desde una carpeta (oficina / manuales).
    """
    rutas = listar_archivos_documento(carpeta, recursivo=recursivo)
    todos: List[Document] = []
    for i, ruta in enumerate(rutas):
        if progreso:
            progreso(i + 1, len(rutas), ruta)
        try:
            todos.extend(cargar_un_archivo(ruta))
        except Exception as e:
            todos.append(
                Document(
                    page_content=f"[Error al cargar {ruta}: {e}]",
                    metadata={"source": ruta, "error": True},
                )
            )
    return todos


def vectorizar_y_persistir(
    documentos: List[Document],
    persist_directory: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    reemplazar_indice: bool = True,
) -> int:
    """
    Trocea, embeddea y guarda en Chroma.

    - reemplazar_indice=True: borra el índice anterior (una sola fuente de verdad, p. ej. carpeta de oficina).
    - reemplazar_indice=False: añade trozos al índice existente (p. ej. subidas desde Streamlit).
    """
    if not documentos:
        return 0
    if reemplazar_indice and os.path.exists(persist_directory):
        shutil.rmtree(persist_directory)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    chunks = splitter.split_documents(documentos)
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    if not os.path.exists(persist_directory):
        Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=persist_directory,
        )
    else:
        store = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings,
        )
        store.add_documents(chunks)
    return len(chunks)
