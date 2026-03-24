"""
Ejecución de modos (chat, resumen, cuestionario, guía) sobre el mismo índice Chroma + LM Studio.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, List, Optional

from langchain_core.documents import Document

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

from chroma_lm import huggingface_embeddings, langchain_chroma
from rag_chain_lm import DB_PATH, LM_STUDIO_URL
from prompts_notebooklm import (
    APP_CONTEXT_FOR_MODEL,
    ModoContenido,
    PROMPT_CHAT_MEMORIA,
    configuracion_modo,
    consulta_recuperacion,
)


def _embeddings():
    return huggingface_embeddings()


def _retriever(k: int):
    db = langchain_chroma(DB_PATH, _embeddings())
    return db.as_retriever(search_kwargs={"k": k})


def _norm_ruta_fuente(s: str) -> str:
    return os.path.abspath(os.path.expanduser(s or ""))


def listar_fuentes_indexadas() -> List[str]:
    """
    Lista rutas únicas presentes en metadata `source` del índice Chroma (documentos ya vectorizados).
    """
    if not os.path.exists(DB_PATH):
        return []
    try:
        store = langchain_chroma(DB_PATH, _embeddings())
        coll = store._collection
        raw = coll.get(include=["metadatas"])
        metadatas = raw.get("metadatas") or []
    except Exception:
        return []
    out: set[str] = set()
    for md in metadatas:
        if md and md.get("source"):
            out.add(_norm_ruta_fuente(str(md["source"])))
    return sorted(out)


def _recuperar_documentos(
    query: str,
    k: int,
    fuentes_permitidas: Optional[List[str]] = None,
) -> tuple[List[Document], Optional[str]]:
    """
    Recupera fragmentos. Si `fuentes_permitidas` es una lista no vacía, solo se usan
    chunks cuya metadata `source` coincida (ruta normalizada) con alguno de esos archivos.

    Si la lista es None o vacía, se usa todo el índice.

    Devuelve (documentos, mensaje_error o None).
    """
    store = langchain_chroma(DB_PATH, _embeddings())
    permitidas: Optional[set[str]] = None
    if fuentes_permitidas:
        permitidas = {
            _norm_ruta_fuente(s) for s in fuentes_permitidas if (s or "").strip()
        }
    if not permitidas:
        docs = _retriever(k).get_relevant_documents(query)
        return docs, None

    for pool_size in (80, 150, 250, 400, 600):
        pool = store.similarity_search(query, k=pool_size)
        matched = [
            d
            for d in pool
            if _norm_ruta_fuente(d.metadata.get("source") or "") in permitidas
        ]
        if len(matched) >= k:
            return matched[:k], None
        if pool_size >= 600 and matched:
            return matched[:k], None

    return [], (
        "No se encontraron fragmentos en los documentos seleccionados para esta consulta. "
        "Prueba a quitar el filtro, reindexar o elegir otros archivos."
    )


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
    fuentes_permitidas: Optional[List[str]] = None,
) -> dict[str, Any]:
    """
    Devuelve dict con: texto, fuentes, modo, consulta_recuperacion.

    historial_conversacion: turnos previos en texto plano (solo modo CHAT);
    mejora seguimiento sin inventar hechos fuera del contexto recuperado.

    fuentes_permitidas: lista de rutas de archivo tal como en el índice; si es None o
    lista vacía, se usa todo el corpus indexado.
    """
    cfg = configuracion_modo(modo)
    if modo == ModoContenido.CHAT:
        q = _consulta_retrieval_chat(
            instruccion, tema_recuperacion, historial_conversacion
        )
    else:
        q = consulta_recuperacion(modo, tema_recuperacion)

    fp = fuentes_permitidas if fuentes_permitidas else None
    docs, err_filtro = _recuperar_documentos(q, cfg.k_fragmentos, fp)
    if err_filtro:
        return {
            "texto": err_filtro,
            "fuentes": [],
            "modo": modo.value,
            "consulta_recuperacion": q,
            "cuestionario_json": None,
            "error_filtro": True,
        }
    if not docs:
        return {
            "texto": "No se recuperó ningún fragmento. Indexa documentos primero.",
            "fuentes": [],
            "modo": modo.value,
            "consulta_recuperacion": q,
            "cuestionario_json": None,
        }

    def _archivo_fragmento(d: Document) -> str:
        raw = d.metadata.get("source") or d.metadata.get("file_path") or ""
        if not raw:
            return "desconocido"
        return _norm_ruta_fuente(str(raw))

    if modo == ModoContenido.CUESTIONARIO:
        context = "\n\n---\n\n".join(
            f"[Fragmento {i+1}] (archivo: {_archivo_fragmento(d)})\n{d.page_content}"
            for i, d in enumerate(docs)
        )
    else:
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


def _primer_objeto_json_balanceado(texto: str) -> Optional[str]:
    """Extrae el primer objeto JSON `{...}` respetando strings y llaves anidadas."""
    i = texto.find("{")
    if i < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for j in range(i, len(texto)):
        c = texto[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return texto[i : j + 1]
    return None


def _quitar_cercas_markdown(texto: str) -> str:
    """Elimina bloques ```json ... ``` y restos de fences."""
    t = texto.strip()
    for _ in range(5):
        nuevo = re.sub(
            r"```(?:json|JSON)?\s*",
            "",
            t,
            flags=re.IGNORECASE,
        )
        nuevo = re.sub(r"\s*```\s*", "", nuevo)
        if nuevo == t:
            break
        t = nuevo.strip()
    return t


def _extraer_json_cuestionario(texto: str) -> Optional[dict]:
    """Intenta parsear JSON del bloque devuelto por el modelo."""
    t = _quitar_cercas_markdown(texto)

    def _intentar(s: str) -> Optional[dict]:
        s = s.strip()
        if not s:
            return None
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
        bloque = _primer_objeto_json_balanceado(s)
        if not bloque:
            return None
        try:
            return json.loads(bloque)
        except json.JSONDecodeError:
            arreglado = re.sub(r",\s*([\]}])", r"\1", bloque)
            try:
                return json.loads(arreglado)
            except json.JSONDecodeError:
                return None

    parsed = _intentar(t)
    if parsed is not None:
        return parsed

    # Texto introductorio antes del primer {
    idx = t.find("{")
    if idx > 0:
        parsed = _intentar(t[idx:])
        if parsed is not None:
            return parsed

    # Bloque entre fences aunque el balanceo global falle
    m = re.search(
        r"```(?:json)?\s*(\{[\s\S]*?\})\s*```",
        texto,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if m:
        parsed = _intentar(m.group(1))
        if parsed is not None:
            return parsed

    return None
