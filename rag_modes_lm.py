"""
Ejecución de modos (chat, resumen, cuestionario, guía) sobre el mismo índice Chroma + LM Studio.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

from rag_chain_lm import DB_PATH, LM_STUDIO_URL
from prompts_notebooklm import (
    APP_CONTEXT_FOR_MODEL,
    ModoContenido,
    PROMPT_CHAT_MEMORIA,
    configuracion_modo,
    consulta_recuperacion,
)


def _embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def _retriever(k: int):
    db = Chroma(persist_directory=DB_PATH, embedding_function=_embeddings())
    return db.as_retriever(search_kwargs={"k": k})


def _llm(model_id: str, temperature: float) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=LM_STUDIO_URL,
        api_key="lm-studio",
        model=model_id.strip(),
        temperature=temperature,
    )


def _consulta_retrieval_chat(
    instruccion: str, tema_recuperacion: str, historial: str
) -> str:
    """Mezcla pregunta actual (y opcionalmente historial) para recuperar chunks relevantes."""
    base = (tema_recuperacion or instruccion).strip()
    if historial.strip():
        h = historial.strip()
        if len(h) > 4000:
            h = h[-4000:]
        return f"{h}\n\n---\nPregunta actual:\n{instruccion.strip()}"
    return consulta_recuperacion(ModoContenido.CHAT, base)


def ejecutar_modo(
    modo: ModoContenido,
    instruccion: str,
    model_id: str,
    tema_recuperacion: str = "",
    historial_conversacion: str = "",
) -> dict[str, Any]:
    """
    Devuelve dict con: texto, fuentes, modo, consulta_recuperacion.

    historial_conversacion: turnos previos en texto plano (solo modo CHAT);
    mejora seguimiento sin inventar hechos fuera del contexto recuperado.
    """
    cfg = configuracion_modo(modo)
    if modo == ModoContenido.CHAT:
        q = _consulta_retrieval_chat(
            instruccion, tema_recuperacion, historial_conversacion
        )
    else:
        q = consulta_recuperacion(modo, tema_recuperacion)
    retriever = _retriever(cfg.k_fragmentos)
    docs = retriever.get_relevant_documents(q)
    context = "\n\n---\n\n".join(
        f"[Fragmento {i+1}]\n{d.page_content}" for i, d in enumerate(docs)
    )
    fuentes = []
    for d in docs:
        src = d.metadata.get("source") or d.metadata.get("file_path") or "desconocido"
        if src not in fuentes:
            fuentes.append(src)

    llm = _llm(model_id, cfg.temperatura)
    usar_memoria = modo == ModoContenido.CHAT and bool(
        historial_conversacion.strip()
    )
    if usar_memoria:
        prompt = PromptTemplate(
            input_variables=["app_context", "history", "context", "instruccion"],
            template=PROMPT_CHAT_MEMORIA,
        )
        vars_llm = {
            "app_context": APP_CONTEXT_FOR_MODEL,
            "history": historial_conversacion.strip(),
            "context": context,
            "instruccion": instruccion,
        }
    else:
        prompt = PromptTemplate(
            input_variables=["app_context", "context", "instruccion"],
            template=cfg.plantilla,
        )
        vars_llm = {
            "app_context": APP_CONTEXT_FOR_MODEL,
            "context": context,
            "instruccion": instruccion,
        }
    chain = prompt | llm
    texto = chain.invoke(vars_llm)
    content = texto.content if hasattr(texto, "content") else str(texto)

    out: dict[str, Any] = {
        "texto": content,
        "fuentes": fuentes,
        "modo": modo.value,
        "consulta_recuperacion": q,
    }
    if modo == ModoContenido.CUESTIONARIO:
        out["cuestionario_json"] = _extraer_json_cuestionario(content)
    return out


def _extraer_json_cuestionario(texto: str) -> Optional[dict]:
    """Intenta parsear JSON del bloque devuelto por el modelo."""
    texto = texto.strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", texto)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None
