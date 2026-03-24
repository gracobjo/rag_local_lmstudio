"""
Cadena RAG para LM Studio. Usa los mismos ids que devuelve GET /v1/models.
Si los .py originales son de solo lectura, importa este módulo desde app_lmstudio.py.
"""
from __future__ import annotations

from typing import Optional

from langchain_openai import ChatOpenAI
from chroma_lm import huggingface_embeddings, langchain_chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
import os

DB_PATH = "./chroma_db"
LM_STUDIO_URL = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL", "meta-llama-3.1-8b-instruct")

# Ids de chat (excluye modelos solo de embeddings). Ajusta si añades/quitas modelos en LM Studio.
MODELOS_CHAT_LM_STUDIO: dict[str, str] = {
    "meta-llama-3.1-8b-instruct": "Llama 3.1 8B Instruct",
    "qwen/qwen3.5-9b": "Qwen 3.5 9B",
    "phi-3-mini-4k-instruct": "Phi-3 mini 4k instruct",
}

PROMPT_TEMPLATE = """Eres un asistente experto. Usa ÚNICAMENTE el siguiente contexto para responder.
Si la respuesta no está en el contexto, di: 'No tengo información sobre eso.'

Contexto:
{context}

Pregunta: {question}

Respuesta:"""


def crear_cadena_rag(model_id: Optional[str] = None):
    """
    model_id: id exacto según GET /v1/models. Si es None, usa LM_STUDIO_MODEL (env o default).
    """
    mid = (model_id or LM_STUDIO_MODEL).strip()
    embeddings = huggingface_embeddings()
    db = langchain_chroma(DB_PATH, embeddings)
    retriever = db.as_retriever(search_kwargs={"k": 4})
    llm = ChatOpenAI(
        base_url=LM_STUDIO_URL,
        api_key="lm-studio",
        model=mid,
        temperature=0.1,
    )
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=PROMPT_TEMPLATE,
    )
    return RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )
