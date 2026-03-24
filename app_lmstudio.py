"""
Interfaz Streamlit RAG + modos tipo NotebookLM (resumen, cuestionario, guía).
Ejecutar: ./run_streamlit_lmstudio.sh
"""
import streamlit as st
import os
import warnings
from langchain_community.document_loaders import PyPDFLoader, TextLoader

from office_docs import (
    EXTENSIONES_SOPORTADAS,
    cargar_carpeta,
    cargar_un_archivo,
    vectorizar_y_persistir,
)
from rag_chain_lm import LM_STUDIO_MODEL, MODELOS_CHAT_LM_STUDIO
from prompts_notebooklm import ModoContenido
from rag_modes_lm import ejecutar_modo

warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

DB_PATH = "./chroma_db"
DOCS_PATH = "./docs"


def _nombre_archivo_seguro(nombre: str) -> str:
    base = os.path.basename(nombre)
    if not base or base.strip() != base:
        return "documento_subido"
    return base

st.set_page_config(
    page_title="RAG local (LM Studio)",
    page_icon="📚",
    layout="wide",
)

st.markdown(
    """
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #4CAF50; color: white; }
    .stChatInputContainer { padding-bottom: 20px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def procesar_y_indexar(uploaded_files):
    """Guarda copia en ./docs y añade trozos al índice Chroma (sin borrar índice previo)."""
    os.makedirs(DOCS_PATH, exist_ok=True)
    documentos_totales = []
    guardados: list[str] = []
    for uploaded_file in uploaded_files:
        nombre = _nombre_archivo_seguro(uploaded_file.name)
        destino = os.path.join(DOCS_PATH, nombre)
        with open(destino, "wb") as f:
            f.write(uploaded_file.getbuffer())
        guardados.append(destino)
        documentos_totales.extend(cargar_un_archivo(destino))

    n = vectorizar_y_persistir(
        documentos_totales,
        persist_directory=DB_PATH,
        reemplazar_indice=False,
    )
    return n, guardados


def indexar_carpeta_en_sistema(
    ruta_carpeta: str, recursivo: bool, reemplazar: bool
) -> tuple[int, int]:
    """
    Carga todos los documentos admitidos desde una carpeta y vectoriza.
    Devuelve (número de fragmentos, número de archivos leídos).
    """
    ruta = os.path.realpath(os.path.expanduser(ruta_carpeta.strip()))
    if not os.path.isdir(ruta):
        raise FileNotFoundError(f"No es una carpeta válida: {ruta}")
    docs = cargar_carpeta(ruta, recursivo=recursivo)
    fuentes: set[str] = set()
    for d in docs:
        s = d.metadata.get("source")
        if s and not d.metadata.get("error"):
            fuentes.add(s)
    n_archivos = len(fuentes)
    chunks = vectorizar_y_persistir(
        docs,
        persist_directory=DB_PATH,
        reemplazar_indice=reemplazar,
    )
    return chunks, n_archivos


def _historial_para_prompt(messages: list) -> str:
    """Turnos previos al mensaje actual (texto plano, truncado)."""
    lineas = []
    for m in messages:
        if m.get("role") == "user":
            lineas.append(f"Usuario: {m.get('content', '')}")
        else:
            lineas.append(f"Asistente: {m.get('content', '')}")
    texto = "\n".join(lineas)
    if len(texto) > 8000:
        return texto[-8000:]
    return texto


def _render_cuestionario_json(data: dict) -> None:
    if not data or "preguntas" not in data:
        return
    st.subheader(data.get("titulo", "Cuestionario"))
    for p in data.get("preguntas", []):
        pid = p.get("id", "")
        with st.expander(f"Pregunta {pid}", expanded=False):
            st.markdown(f"**{p.get('pregunta', '')}**")
            opciones = p.get("opciones") or []
            correcta = int(p.get("indice_correcta", 0))
            for i, opt in enumerate(opciones):
                pref = "✅ " if i == correcta else "○ "
                st.markdown(f"{pref}{opt}")
            st.caption(f"Explicación: {p.get('explicacion', '')}")


with st.sidebar:
    st.title("⚙️ Modelo LLM")
    _ids = list(MODELOS_CHAT_LM_STUDIO.keys())
    _default_i = next(
        (i for i, k in enumerate(_ids) if k == LM_STUDIO_MODEL),
        0,
    )
    modelo_elegido = st.selectbox(
        "Modelo",
        options=_ids,
        index=_default_i,
        format_func=lambda mid: f"{MODELOS_CHAT_LM_STUDIO[mid]} — {mid}",
        help="Ids según GET /v1/models en LM Studio.",
    )
    otro_id = st.text_input(
        "Otro id (opcional)",
        placeholder="Sobrescribe el modelo de la lista",
    )
    model_id_chat = otro_id.strip() if otro_id.strip() else modelo_elegido

    st.divider()
    st.title("📂 Documentación (fuente de verdad)")
    st.caption(
        f"Formatos: **{', '.join(sorted(EXTENSIONES_SOPORTADAS))}** · "
        "Carpeta del proyecto: `docs/`"
    )
    st.info(
        "**Oficina / manuales:** indexa una carpeta entera (reemplaza el índice) o sube "
        "ficheros sueltos (se copian a `docs/` y se **añaden** al índice). "
        "LM Studio en **1234**."
    )

    recursivo = st.checkbox(
        "Incluir subcarpetas al indexar desde disco", value=True, key="rec_folder"
    )

    if st.button("📁 Indexar carpeta `docs/` del proyecto", key="idx_docs"):
        base_docs = os.path.realpath(DOCS_PATH)
        if not os.path.isdir(base_docs) or not os.listdir(base_docs):
            st.warning(
                "La carpeta `docs/` está vacía o no existe. Copia ahí tus manuales o sube archivos abajo."
            )
        else:
            with st.spinner("Leyendo docs/ y vectorizando (índice anterior se sustituye)..."):
                try:
                    n, nfiles = indexar_carpeta_en_sistema(
                        base_docs, recursivo=recursivo, reemplazar=True
                    )
                    st.success(
                        f"Índice actualizado: **{n}** fragmentos desde **{nfiles}** archivos."
                    )
                except Exception as e:
                    st.error(str(e))

    ruta_externa = st.text_input(
        "Ruta absoluta de otra carpeta (opcional)",
        placeholder="/home/usuario/documentacion_empresa",
        help="Indexa solo esa carpeta como única fuente (reemplaza el índice vectorial).",
        key="path_ext",
    )
    if st.button("📂 Indexar carpeta indicada", key="idx_ext"):
        path = (ruta_externa or "").strip()
        if not path:
            st.warning("Escribe una ruta absoluta.")
        else:
            with st.spinner("Leyendo archivos y vectorizando..."):
                try:
                    n, nfiles = indexar_carpeta_en_sistema(
                        path, recursivo=recursivo, reemplazar=True
                    )
                    st.success(
                        f"Índice actualizado: **{n}** fragmentos desde **{nfiles}** archivos."
                    )
                except Exception as e:
                    st.error(str(e))

    st.divider()
    st.markdown("**Subir archivos** (se guardan en `docs/` y se fusionan con el índice)")
    archivos = st.file_uploader(
        "Arrastra PDF, TXT, MD o DOCX",
        accept_multiple_files=True,
        type=["pdf", "txt", "md", "docx"],
    )
    if st.button("🚀 Indexar archivos subidos"):
        if archivos:
            with st.spinner("Indexando..."):
                n, rutas = procesar_y_indexar(archivos)
                st.success(f"Añadidos **{n}** fragmentos al índice.")
                for r in rutas:
                    st.caption(f"Guardado: `{r}`")
        else:
            st.warning("Sube al menos un archivo.")
    if st.button("🗑️ Borrar índice"):
        if os.path.exists(DB_PATH):
            import shutil

            shutil.rmtree(DB_PATH)
            st.success("Índice eliminado.")
            st.rerun()

    st.divider()
    st.caption(
        "Modos **Resumen / Cuestionario / Guía** usan prompts dedicados y más "
        "fragmentos recuperados que el chat."
    )
    if st.button("🧹 Borrar historial del chat"):
        st.session_state.messages = []
        st.rerun()

tab_chat, tab_res, tab_quiz, tab_guia = st.tabs(
    ["💬 Chat", "📝 Resumen", "❓ Cuestionario", "📖 Guía de estudio"]
)

with tab_chat:
    st.caption(
        f"Modelo: `{model_id_chat}` · **Memoria conversacional** en el chat: el asistente usa "
        "los turnos anteriores solo para entender seguimientos; los hechos salen de los documentos recuperados."
    )
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("fuentes"):
                with st.expander("Fuentes (fragmentos)"):
                    for f in message["fuentes"]:
                        st.text(f)

    if prompt := st.chat_input("Tu pregunta..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if not os.path.exists(DB_PATH):
                respuesta = "Indexa documentos en el panel izquierdo primero."
                st.markdown(respuesta)
                fuentes = []
            else:
                with st.spinner("Generando..."):
                    try:
                        hist = _historial_para_prompt(
                            st.session_state.messages[:-1]
                        )
                        out = ejecutar_modo(
                            ModoContenido.CHAT,
                            instruccion=prompt,
                            model_id=model_id_chat,
                            historial_conversacion=hist,
                        )
                        respuesta = out["texto"]
                        fuentes = out["fuentes"]
                        st.markdown(respuesta)
                        with st.expander("Fuentes recuperadas"):
                            for f in fuentes:
                                st.text(f)
                    except Exception as e:
                        respuesta = f"Error: {e}"
                        fuentes = []
                        st.error(respuesta)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": respuesta,
                "fuentes": fuentes,
            }
        )

with tab_res:
    st.markdown(
        "Genera un **resumen estructurado** (tipo informe corto) a partir de los documentos indexados."
    )
    tema_res = st.text_input(
        "Enfoque (opcional)",
        placeholder="Ej.: resumen para un ejecutivo, o solo la parte legal",
        key="tema_res",
    )
    if st.button("Generar resumen", key="btn_res"):
        if not os.path.exists(DB_PATH):
            st.warning("Primero indexa al menos un documento.")
        else:
            instruccion = (
                "Resume el contenido para un lector que no ha leído el documento completo."
            )
            if tema_res.strip():
                instruccion += f" Enfoque: {tema_res.strip()}."
            with st.spinner("Leyendo fragmentos y redactando..."):
                try:
                    out = ejecutar_modo(
                        ModoContenido.RESUMEN,
                        instruccion=instruccion,
                        model_id=model_id_chat,
                        tema_recuperacion=tema_res,
                    )
                    st.markdown(out["texto"])
                    with st.expander("Fuentes"):
                        for f in out["fuentes"]:
                            st.text(f)
                except Exception as e:
                    st.error(str(e))

with tab_quiz:
    st.markdown(
        "Genera un **test tipo examen** con 4 opciones y explicación de la correcta (JSON interno)."
    )
    n_preg = st.slider("Número de preguntas", min_value=3, max_value=20, value=8)
    tema_quiz = st.text_input(
        "Tema o área (opcional)",
        placeholder="Ej.: fechas, definiciones, apartado 2",
        key="tema_quiz",
    )
    if st.button("Generar cuestionario", key="btn_quiz"):
        if not os.path.exists(DB_PATH):
            st.warning("Primero indexa al menos un documento.")
        else:
            instruccion = (
                f"Genera exactamente {n_preg} preguntas de test en español. "
                "Cada una con 4 opciones y una sola correcta."
            )
            if tema_quiz.strip():
                instruccion += f" Prioriza el tema: {tema_quiz.strip()}."
            with st.spinner("Creando preguntas desde el contexto..."):
                try:
                    out = ejecutar_modo(
                        ModoContenido.CUESTIONARIO,
                        instruccion=instruccion,
                        model_id=model_id_chat,
                        tema_recuperacion=tema_quiz,
                    )
                    data = out.get("cuestionario_json")
                    if data:
                        _render_cuestionario_json(data)
                        with st.expander("JSON crudo (exportar)"):
                            st.code(out["texto"], language="json")
                    else:
                        st.warning(
                            "No se pudo parsear JSON; mostrando texto del modelo."
                        )
                        st.markdown(out["texto"])
                    with st.expander("Fuentes"):
                        for f in out["fuentes"]:
                            st.text(f)
                except Exception as e:
                    st.error(str(e))

with tab_guia:
    st.markdown(
        "Guía de estudio: **mapa del tema**, **preguntas de autoevaluación** y **qué repasar**."
    )
    tema_guia = st.text_input(
        "Ángulo (opcional)",
        placeholder="Ej.: preparar examen tipo test",
        key="tema_guia",
    )
    if st.button("Generar guía de estudio", key="btn_guia"):
        if not os.path.exists(DB_PATH):
            st.warning("Primero indexa al menos un documento.")
        else:
            instruccion = "Elabora una guía de estudio clara basada en el contexto."
            if tema_guia.strip():
                instruccion += f" Objetivo: {tema_guia.strip()}."
            with st.spinner("Generando guía..."):
                try:
                    out = ejecutar_modo(
                        ModoContenido.GUIA_ESTUDIO,
                        instruccion=instruccion,
                        model_id=model_id_chat,
                        tema_recuperacion=tema_guia,
                    )
                    st.markdown(out["texto"])
                    with st.expander("Fuentes"):
                        for f in out["fuentes"]:
                            st.text(f)
                except Exception as e:
                    st.error(str(e))
