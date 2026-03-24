"""
Interfaz Streamlit RAG + modos tipo NotebookLM (resumen, cuestionario, guía).
Ejecutar: ./run_streamlit_lmstudio.sh
"""
import streamlit as st
import os
import shutil
import subprocess
import json
import html as html_module
import time
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit.components.v1 as components
from langchain_community.document_loaders import PyPDFLoader, TextLoader

from office_docs import (
    EXTENSIONES_SOPORTADAS,
    cargar_un_archivo,
    indexar_carpeta_en_sistema,
    vectorizar_y_persistir,
)
from rag_chain_lm import LM_STUDIO_MODEL, MODELOS_CHAT_LM_STUDIO
from prompts_notebooklm import ModoContenido
from rag_modes_lm import ejecutar_modo, listar_fuentes_indexadas

warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

DB_PATH = "./chroma_db"
DOCS_PATH = "./docs"


def _fuentes_rag_seleccionadas() -> Optional[List[str]]:
    """Rutas elegidas en el multiselect; None = usar todo el índice."""
    sel = st.session_state.get("fuentes_sel")
    if not sel:
        return None
    return list(sel)


def _mensaje_error_lm_studio(exc: BaseException) -> str:
    """Traduce errores del cliente OpenAI/LM Studio (modelo no cargado, id incorrecto)."""
    raw = str(exc)
    if "Failed to load model" in raw or (
        "invalid_request_error" in raw and "model" in raw.lower()
    ):
        return (
            "LM Studio no puede usar el modelo con el id seleccionado. "
            "Carga el modelo en LM Studio (Chat → Load) y en el panel elige el mismo id que "
            "aparece en GET /v1/models (por ejemplo qwen/qwen3.5-9b). "
            "El id por defecto meta-llama-3.1-8b-instruct solo funciona si ese modelo está "
            f"descargado y cargado. Detalle: {raw}"
        )
    return raw


def _nombre_archivo_seguro(nombre: str) -> str:
    base = os.path.basename(nombre)
    if not base or base.strip() != base:
        return "documento_subido"
    return base


def _abrir_lm_studio_escritorio() -> tuple[bool, str]:
    """
    Intenta lanzar la aplicación de escritorio LM Studio (no es la API :1234).
    Configura LM_STUDIO_EXECUTABLE con la ruta al binario si no está en PATH.
    """
    exe = (os.environ.get("LM_STUDIO_EXECUTABLE") or "").strip()
    if exe and os.path.isfile(exe):
        try:
            if os.name == "nt":
                os.startfile(exe)  # type: ignore[attr-defined]
            else:
                subprocess.Popen([exe], start_new_session=True)
            return True, ""
        except OSError as e:
            return False, str(e)
    for name in ("lm-studio", "lmstudio"):
        path = shutil.which(name)
        if path:
            try:
                subprocess.Popen([path], start_new_session=True)
                return True, ""
            except OSError as e:
                return False, str(e)
    return (
        False,
        "No se encontró LM Studio en PATH. Abre la app manualmente o define la variable "
        "de entorno LM_STUDIO_EXECUTABLE con la ruta al ejecutable.",
    )

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


def _resolver_ruta_fuente_cuestionario(
    candidato: str, catalogo: List[str]
) -> Optional[str]:
    """Alinea el texto devuelto por el modelo con una ruta del índice."""
    if not catalogo:
        return None
    t = (candidato or "").strip()
    if not t:
        return catalogo[0] if len(catalogo) == 1 else None
    t_exp = os.path.abspath(os.path.expanduser(t))
    if os.path.isfile(t_exp):
        return t_exp
    t_low = t.lower()
    for f in catalogo:
        try:
            if os.path.abspath(f).lower() == t_low:
                return f
        except OSError:
            continue
    for f in catalogo:
        fl = f.lower()
        if t_low in fl or fl in t_low:
            return f
        base = os.path.basename(f).lower()
        if base in t_low or t_low in base:
            return f
    return None


def _render_cuestionario_interactivo(
    data: dict,
    fuentes_catalogo: List[str],
    instance_key: str,
) -> None:
    """Cuestionario tipo test: elegir opción, comprobar, feedback y referencia a fuente."""
    if not data or "preguntas" not in data:
        return
    st.subheader(data.get("titulo", "Cuestionario"))
    st.caption(
        "Pulsa **A–D** para elegir y luego **Comprobar respuesta**. "
        "Verás si acertaste, la opción correcta resaltada, la explicación y la ruta al documento indexado."
    )
    for idx, p in enumerate(data.get("preguntas", [])):
        opciones = (p.get("opciones") or [])[:4]
        if len(opciones) < 2:
            continue
        pid = str(p.get("id", idx + 1))
        sel_key = f"quiz_sel_{instance_key}_{pid}"
        rev_key = f"quiz_rev_{instance_key}_{pid}"
        if sel_key not in st.session_state:
            st.session_state[sel_key] = None
        if rev_key not in st.session_state:
            st.session_state[rev_key] = False

        correct_idx = int(p.get("indice_correcta", 0))
        correct_idx = max(0, min(correct_idx, len(opciones) - 1))

        st.markdown(f"**Pregunta {pid}** — {p.get('pregunta', '')}")

        if not st.session_state[rev_key]:
            cols = st.columns(len(opciones))
            for i, opt in enumerate(opciones):
                with cols[i]:
                    if st.button(
                        chr(65 + i),
                        key=f"qb_{instance_key}_{pid}_{i}",
                        help=str(opt)[:800],
                        use_container_width=True,
                    ):
                        st.session_state[sel_key] = i
            chosen = st.session_state[sel_key]
            if chosen is not None and 0 <= chosen < len(opciones):
                st.caption(f"Selección: **{chr(65+chosen)})** {opciones[chosen]}")
            if st.button(
                "Comprobar respuesta",
                key=f"qchk_{instance_key}_{pid}",
                disabled=chosen is None,
            ):
                st.session_state[rev_key] = True
        else:
            chosen = st.session_state.get(sel_key)
            for i, opt in enumerate(opciones):
                letter = chr(65 + i)
                txt = html_module.escape(str(opt))
                if i == correct_idx:
                    st.markdown(
                        f'<div style="background:rgba(46,125,50,0.42);padding:10px;border-radius:8px;'
                        f'border-left:4px solid #66bb6a;margin:6px 0;">'
                        f"✅ <b>{letter})</b> {txt} — <i>correcta</i></div>",
                        unsafe_allow_html=True,
                    )
                elif chosen is not None and i == chosen:
                    st.markdown(
                        f'<div style="background:rgba(183,28,28,0.38);padding:10px;border-radius:8px;'
                        f'border-left:4px solid #ef5350;margin:6px 0;">'
                        f"❌ <b>{letter})</b> {txt}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<div style="padding:8px;margin:4px 0;opacity:0.78">'
                        f"<b>{letter})</b> {txt}</div>",
                        unsafe_allow_html=True,
                    )

            if chosen == correct_idx:
                st.success("¡Correcto!")
            elif chosen is None:
                st.warning("No habías elegido ninguna opción.")
            else:
                st.error("Incorrecto.")

            st.markdown("**Explicación**")
            st.info(p.get("explicacion", "") or "—")

            fuente_txt = (p.get("fuente_archivo") or p.get("fuente") or "").strip()
            path_res = _resolver_ruta_fuente_cuestionario(fuente_txt, fuentes_catalogo)
            frag = p.get("numero_fragmento") or p.get("fragmento")
            donde = (p.get("donde_encontrarlo") or p.get("ubicacion") or "").strip()

            st.markdown("**Fuente en la documentación indexada**")
            if frag:
                st.caption(
                    f"Fragmento de contexto al generar el cuestionario: **[Fragmento {frag}]**"
                )
            if donde:
                st.markdown(donde)

            if path_res and os.path.isfile(path_res):
                st.code(path_res, language="text")
                try:
                    uri = Path(path_res).expanduser().resolve().as_uri()
                    st.markdown(
                        f"[Enlace al archivo local (`file://`)]({uri}) — "
                        "muchos navegadores bloquean `file://`; abre la ruta con el explorador si no funciona."
                    )
                except ValueError:
                    st.caption("No se pudo generar URI file:// para esta ruta.")
            elif path_res:
                st.code(path_res, language="text")
            elif fuente_txt:
                st.text(fuente_txt)
            else:
                st.caption(
                    "Sin campo `fuente_archivo` en el JSON. Comprueba la lista global de fuentes al final."
                )

            st.divider()


def _render_guardar_imprimir(
    key_base: str,
    titulo_imprimir: str,
    texto: str,
    fuentes: List[str],
    nombre_descarga: str,
    mime: str = "text/markdown",
    json_data: Optional[Dict[str, Any]] = None,
    nombre_json: str = "cuestionario.json",
) -> None:
    """Botones Guardar (descarga) e iframe con botón Imprimir."""
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "💾 Guardar",
            data=texto.encode("utf-8"),
            file_name=nombre_descarga,
            mime=mime,
            key=f"dl_txt_{key_base}",
            help="Descarga el texto mostrado",
        )
    with c2:
        if json_data is not None:
            st.download_button(
                "💾 Guardar JSON",
                data=json.dumps(json_data, ensure_ascii=False, indent=2).encode("utf-8"),
                file_name=nombre_json,
                mime="application/json",
                key=f"dl_json_{key_base}",
            )
        else:
            st.empty()

    safe = html_module.escape(texto)
    safe_f = html_module.escape("\n".join(fuentes)) if fuentes else ""
    bloque_fuentes = (
        f"<h3 style='font-size:12px;margin:12px 0 4px'>Fuentes</h3>"
        f"<pre style='font-size:11px;white-space:pre-wrap'>{safe_f}</pre>"
        if fuentes
        else ""
    )
    tit = html_module.escape(titulo_imprimir)
    h = min(380 + min(len(texto) // 80, 40) * 8, 720)
    print_html = f"""<div style="border:1px solid #555;border-radius:8px;padding:12px;background:#1a1c24;color:#e8eaed;">
  <p style="margin:0 0 8px;font-size:13px;font-weight:600">{tit}</p>
  <pre style="white-space:pre-wrap;font-family:system-ui,sans-serif;font-size:13px;margin:0;line-height:1.45">{safe}</pre>
  {bloque_fuentes}
  <button type="button" style="margin-top:12px;padding:8px 16px;border-radius:6px;border:none;background:#4CAF50;color:#fff;cursor:pointer;font-size:14px"
    onclick="window.print()">🖨️ Imprimir</button>
</div>"""
    components.html(print_html, height=h, scrolling=True)


with st.sidebar:
    if msg := st.session_state.pop("index_ok_msg", None):
        st.success(msg)

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

    st.caption(
        "Ese id debe existir en LM Studio y el modelo **cargado** en Chat. "
        "Si aparece «Failed to load model», elige otro modelo en la lista o escribe el id exacto en **Otro id**."
    )

    with st.expander("🖥️ LM Studio — cargar otro modelo", expanded=False):
        st.markdown(
            "La ventana completa de LM Studio es una **aplicación de escritorio**; el navegador "
            "no puede mostrarla dentro de esta página como si fuera una pestaña. "
            "El puerto **1234** solo sirve para la **API** (chat desde esta app), no para la interfaz gráfica."
        )
        if st.button("Abrir LM Studio en el escritorio", key="btn_open_lmstudio", type="secondary"):
            ok, err = _abrir_lm_studio_escritorio()
            if ok:
                st.success(
                    "Si LM Studio se abrió: ve a **Chat**, pulsa **Load** y elige el modelo. "
                    "Luego selecciona el **mismo id** arriba (Modelo / Otro id)."
                )
            else:
                st.warning(err)
        c1, c2 = st.columns(2)
        with c1:
            st.link_button("lmstudio.ai", "https://lmstudio.ai/")
        with c2:
            st.link_button("API local :1234", "http://127.0.0.1:1234/v1/models")
        _embed = (os.environ.get("LM_STUDIO_EMBED_URL") or "").strip()
        if _embed:
            st.checkbox(
                "Mostrar vista web embebida debajo de las pestañas",
                key="lm_show_embed_panel",
                help="URL definida en LM_STUDIO_EMBED_URL (p. ej. documentación o proxy interno).",
            )
        else:
            st.caption(
                "Opcional: exporta **LM_STUDIO_EMBED_URL** con una URL HTTPS/HTTP para "
                "incrustar una página (no sustituye la app de escritorio)."
            )

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
                    st.session_state["index_ok_msg"] = (
                        f"Índice actualizado: **{n}** fragmentos desde **{nfiles}** archivos."
                    )
                    st.rerun()
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
                    st.session_state["index_ok_msg"] = (
                        f"Índice actualizado: **{n}** fragmentos desde **{nfiles}** archivos."
                    )
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    st.divider()
    st.markdown("**Subir archivos** (se guardan en `docs/` y se fusionan con el índice)")
    st.caption(
        "⚠️ Tras subir, pulsa **Indexar documentos**; si no, el cuestionario seguirá usando solo lo ya indexado."
    )
    archivos = st.file_uploader(
        "Arrastra PDF, TXT, MD o DOCX",
        accept_multiple_files=True,
        type=["pdf", "txt", "md", "docx"],
    )
    if st.button("🚀 Indexar archivos subidos"):
        if archivos:
            with st.spinner("Indexando..."):
                n, rutas = procesar_y_indexar(archivos)
                nombres = ", ".join(os.path.basename(r) for r in rutas)
                st.session_state["index_ok_msg"] = (
                    f"Añadidos **{n}** fragmentos: {nombres}"
                )
                st.rerun()
        else:
            st.warning("Sube al menos un archivo.")
    if st.button("🗑️ Borrar índice"):
        if os.path.exists(DB_PATH):
            import shutil

            shutil.rmtree(DB_PATH)
            if "fuentes_sel" in st.session_state:
                del st.session_state["fuentes_sel"]
            st.success("Índice eliminado.")
            st.rerun()

    st.divider()
    st.subheader("📑 Contexto RAG")
    if os.path.exists(DB_PATH):
        opts = listar_fuentes_indexadas()
        if opts:

            def _etiqueta_fuente(p: str) -> str:
                base = os.path.basename(p)
                return base if base else p

            st.multiselect(
                "Documentos a usar (vacío = **todos** los indexados)",
                options=opts,
                default=[],
                key="fuentes_sel",
                format_func=_etiqueta_fuente,
                help="Selecciona uno o varios archivos ya vectorizados. "
                "Las preguntas, resúmenes y cuestionarios solo usarán fragmentos de esos ficheros.",
            )
        else:
            st.caption("El índice no expone fuentes; reindexa los documentos.")
    else:
        st.caption("Sin índice: aún no hay documentos vectorizados.")

    st.divider()
    st.caption(
        "Modos **Resumen / Cuestionario / Guía** usan prompts dedicados y más "
        "fragmentos recuperados que el chat."
    )
    if st.button("🧹 Borrar historial del chat"):
        st.session_state.messages = []
        st.rerun()

_embed_url = (os.environ.get("LM_STUDIO_EMBED_URL") or "").strip()
if _embed_url and st.session_state.get("lm_show_embed_panel"):
    _embed_h = int(os.environ.get("LM_STUDIO_EMBED_HEIGHT", "560"))
    st.markdown("##### Vista web (LM_STUDIO_EMBED_URL)")
    st.caption(
        "Esto no es la ventana nativa de LM Studio. Para cargar modelos usa la app de escritorio "
        "o el botón **Abrir LM Studio** en el panel."
    )
    components.iframe(_embed_url, height=_embed_h, scrolling=True)
    st.divider()

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
                            fuentes_permitidas=_fuentes_rag_seleccionadas(),
                        )
                        respuesta = out["texto"]
                        fuentes = out["fuentes"]
                        st.markdown(respuesta)
                        with st.expander("Fuentes recuperadas"):
                            for f in fuentes:
                                st.text(f)
                    except Exception as e:
                        respuesta = _mensaje_error_lm_studio(e)
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
                        fuentes_permitidas=_fuentes_rag_seleccionadas(),
                    )
                    st.session_state["saved_resumen"] = {
                        "texto": out["texto"],
                        "fuentes": out["fuentes"],
                    }
                except Exception as e:
                    st.error(_mensaje_error_lm_studio(e))

    saved_res = st.session_state.get("saved_resumen")
    if saved_res:
        st.markdown("---")
        st.subheader("Último resumen generado")
        _render_guardar_imprimir(
            key_base="resumen",
            titulo_imprimir="Resumen",
            texto=saved_res["texto"],
            fuentes=saved_res["fuentes"],
            nombre_descarga="resumen.md",
        )
        st.markdown(saved_res["texto"])
        with st.expander("Fuentes"):
            for f in saved_res["fuentes"]:
                st.text(f)

with tab_quiz:
    st.markdown(
        "Genera un **test**: eliges la opción (A–D), **compruebas** y ves si acertaste, "
        "la respuesta correcta resaltada, la **explicación** y la **ruta / enlace** a la documentación indexada."
    )
    st.caption(
        "En el panel izquierdo, **Documentos a usar** limita el cuestionario a uno o varios "
        "ficheros ya indexados; vacío = todo el índice."
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
                        fuentes_permitidas=_fuentes_rag_seleccionadas(),
                    )
                    st.session_state["saved_cuestionario"] = {
                        "texto": out["texto"],
                        "fuentes": out["fuentes"],
                        "cuestionario_json": out.get("cuestionario_json"),
                        "error_filtro": bool(out.get("error_filtro")),
                        "instance_key": str(int(time.time() * 1000)),
                    }
                except Exception as e:
                    st.error(_mensaje_error_lm_studio(e))

    saved_q = st.session_state.get("saved_cuestionario")
    if saved_q:
        st.markdown("---")
        st.subheader("Último cuestionario generado")
        if saved_q.get("error_filtro"):
            st.error(saved_q["texto"])
        else:
            data = saved_q.get("cuestionario_json")
            texto_imp = saved_q["texto"]
            _render_guardar_imprimir(
                key_base="quiz",
                titulo_imprimir="Cuestionario",
                texto=texto_imp,
                fuentes=saved_q["fuentes"],
                nombre_descarga="cuestionario.txt"
                if not data
                else "cuestionario_texto.md",
                mime="text/plain" if not data else "text/markdown",
                json_data=data,
                nombre_json="cuestionario.json",
            )
            if data:
                if not saved_q.get("instance_key"):
                    saved_q["instance_key"] = str(int(time.time() * 1000))
                _render_cuestionario_interactivo(
                    data,
                    saved_q.get("fuentes") or [],
                    str(saved_q["instance_key"]),
                )
                with st.expander("JSON crudo (exportar)"):
                    st.code(texto_imp, language="json")
            else:
                st.warning(
                    "No se pudo parsear JSON; mostrando texto del modelo. "
                    "Prueba bajar la temperatura en el modelo o repetir la generación."
                )
                st.markdown(texto_imp)
            with st.expander("Fuentes"):
                for f in saved_q["fuentes"]:
                    st.text(f)

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
                        fuentes_permitidas=_fuentes_rag_seleccionadas(),
                    )
                    st.session_state["saved_guia"] = {
                        "texto": out["texto"],
                        "fuentes": out["fuentes"],
                    }
                except Exception as e:
                    st.error(_mensaje_error_lm_studio(e))

    saved_g = st.session_state.get("saved_guia")
    if saved_g:
        st.markdown("---")
        st.subheader("Última guía generada")
        _render_guardar_imprimir(
            key_base="guia",
            titulo_imprimir="Guía de estudio",
            texto=saved_g["texto"],
            fuentes=saved_g["fuentes"],
            nombre_descarga="guia_estudio.md",
        )
        st.markdown(saved_g["texto"])
        with st.expander("Fuentes"):
            for f in saved_g["fuentes"]:
                st.text(f)
