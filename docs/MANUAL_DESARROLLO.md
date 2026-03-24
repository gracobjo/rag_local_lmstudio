# Manual de desarrollo — RAG local con LM Studio

Este documento describe cómo **configurar el entorno**, **levantar LM Studio**, **exponer la API local**, **arrancar la aplicación Streamlit** y **alinear los identificadores de modelo** con el código. Complementa el [manual de usuario](./MANUAL_USUARIO.md) y los [diagramas técnicos](./DIAGRAMAS_UML_MERMAID.md).

---

## 1. Alcance y componentes

| Componente | Función en el proyecto |
|------------|-------------------------|
| **Python + venv** | Ejecuta Streamlit, LangChain, Chroma y embeddings locales. |
| **LM Studio** | Sirve el LLM de chat mediante API **compatible con OpenAI** (HTTP). |
| **sentence-transformers** (`all-MiniLM-L6-v2`) | Genera vectores de los fragmentos de documento; se descarga la primera vez que indexas o consultas el índice. |
| **Chroma** | Persiste el índice en `./chroma_db` (ruta relativa al directorio de trabajo al lanzar Streamlit). |

La aplicación **no** envía tus PDF a un LLM en la nube para generar embeddings: los embeddings son locales; solo las **respuestas de chat/resumen/etc.** van al servidor LM Studio que tú controles.

---

## 2. Estructura del repositorio y módulos Python

### 2.1 Carpetas relevantes

| Ubicación | Contenido |
|-----------|-----------|
| **Raíz del repo** | Código Python, `requirements.txt`, `reindex.py`, scripts `run_*.sh`. |
| **`docs/`** | Documentación Markdown (manual de usuario, desarrollo, diagramas UML). |
| **`./docs/`** (datos) | Manuales de trabajo: PDF, TXT, MD, DOCX. Se crea al usar la app; puede estar vacía al clonar. |
| **`./chroma_db/`** | Índice vectorial Chroma (generado al indexar). Suele ignorarse en Git. |
| **`venv/`** | Entorno virtual de Python (no forma parte del diseño lógico del proyecto). |
| **`.kiro/`** | Especificaciones de diseño y tareas de pruebas. |

### 2.2 Ficheros `.py` — núcleo (LM Studio + Streamlit)

| Archivo | Función |
|---------|---------|
| `app_lmstudio.py` | Interfaz Streamlit: modelo, indexación, multiselect de fuentes, Chat / Resumen / Cuestionario / Guía. |
| `office_docs.py` | Carga de documentos, troceado, vectorización en Chroma; **`indexar_carpeta_en_sistema`** (compartido con `reindex.py`). |
| `chroma_lm.py` | Cliente Chroma con `PersistentClient` y helpers para LangChain. |
| `rag_chain_lm.py` | URL LM Studio, `DB_PATH`, lista de modelos, `crear_cadena_rag()`. |
| `rag_modes_lm.py` | Modos tipo NotebookLM, recuperación, filtro por fuentes, llamada al LLM. |
| `prompts_notebooklm.py` | Prompts por modo, temperaturas y amplitud de recuperación. |
| `reindex.py` | Reindexación por **CLI** (sin Streamlit ni LM Studio) para cron / sincronización. |

### 2.3 Ficheros `.py` — interfaces alternativas o legado

| Archivo | Función |
|---------|---------|
| `agent_lmstudio.py` / `agent.py` | Agente ReAct con herramienta RAG (`rag_chain_lm` vs `rag_chain`). |
| `api_service_lmstudio.py` / `api_service.py` | API REST FastAPI (variante LM Studio vs legada). |
| `app_dashboard.py` | Streamlit antiguo sin modos NotebookLM. |
| `ingesta.py` | Ingesta básica PDF/TXT; predecesor de `office_docs.py`. |
| `rag_chain.py` | Cadena RAG sin la configuración centralizada de `rag_chain_lm.py`. |

---

## 3. Fuente de verdad en la nube y reindexación programada

Puedes usar una **carpeta en la nube** como única fuente de verdad **si** la sincronizas a disco (cliente oficial, **rclone**, etc.) y luego **vuelves a indexar** esa carpeta local. El índice vectorial sigue siendo local (`./chroma_db`); no hace falta LM Studio para indexar.

### 3.1 Flujo recomendado

1. Configurar **sync** hacia una ruta fija (p. ej. `./docs` o `/datos/manual_empresa`).
2. Tras cada sync (o en horario fijo), ejecutar **`reindex.py`** con `--path` apuntando a esa carpeta.
3. Por defecto, **reindex** **reemplaza** el índice completo (misma semántica que «Indexar carpeta» con reemplazo). Usa `--merge` solo si quieres **añadir** a un índice existente.

### 3.2 `reindex.py` (raíz del proyecto)

No requiere Streamlit. Ejecuta siempre desde la **raíz del repo** (o ajusta rutas):

```bash
source venv/bin/activate
python reindex.py --path ./docs
python reindex.py --path /ruta/absoluta/carpeta_sync
```

**Opciones:**

| Opción | Significado |
|--------|---------------|
| `--path` | Carpeta con documentos (obligatorio). |
| `--no-recursive` | Solo el primer nivel de directorios. |
| `--merge` | Fusionar con el índice existente (no borrar `chroma_db` previo). Sin `--merge`, se **reemplaza** el índice. |
| `--db` | Directorio del índice Chroma (por defecto: variable `RAG_CHROMA_PATH` si existe, si no `./chroma_db` como en `rag_chain_lm`). |

### 3.3 Ejemplo con `cron` (Linux)

Tras sincronizar (manual o con otro cron), reindexar cada noche a las 2:15:

```cron
15 2 * * * cd /ruta/al/rag_project && /ruta/al/rag_project/venv/bin/python reindex.py --path ./docs >> /var/log/rag_reindex.log 2>&1
```

Ajusta `cd` y la ruta a `python`. Usa `flock` o similar si quieres evitar solapamientos.

### 3.4 Ejemplo con `rclone` + reindex

`rclone sync` descarga la nube a disco local; luego **reindex** reconstruye el vector store:

```bash
rclone sync remote:mi_carpeta /ruta/local/docs
cd /ruta/al/rag_project && ./venv/bin/python reindex.py --path /ruta/local/docs
```

Un script de ejemplo comentado está en `docs/examples/reindex_cron_rclone.example.sh`.

### 3.5 `run_reindex.sh`

Script opcional en la raíz que activa el venv y delega en `reindex.py` (misma línea de órdenes que `./run_reindex.sh --path ./docs`).

---

## 4. Preparar el proyecto en Python

### 4.1 Versión de Python

Usa **Python 3.10+** (recomendado 3.11 si está disponible). Comprueba con:

```bash
python3 --version
```

### 4.2 Entorno virtual (recomendado)

En la raíz del repositorio:

```bash
cd /ruta/al/rag_project
python3 -m venv venv
source venv/bin/activate   # Linux / macOS
# Windows: venv\Scripts\activate
```

### 4.3 Dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Incluye entre otros: `streamlit`, `langchain`, `chromadb`, `sentence-transformers`, `langchain-openai`, `pypdf`, `docx2txt`. Si algo falla al cargar `.docx`, verifica que `docx2txt` esté instalado (ya figura en `requirements.txt`).

---

## 5. Variables de entorno

Se leen principalmente desde `rag_chain_lm.py` y el script de arranque.

| Variable | Significado | Valor por defecto |
|----------|-------------|-------------------|
| `LM_STUDIO_BASE_URL` | URL base de la API tipo OpenAI (debe terminar en `/v1` si el cliente espera rutas `/v1/...`). | `http://localhost:1234/v1` |
| `LM_STUDIO_MODEL` | Id del modelo por defecto si no eliges otro en la interfaz; también usado por `run_streamlit_lmstudio.sh` si exportas antes de arrancar. | `meta-llama-3.1-8b-instruct` |
| `LM_STUDIO_EXECUTABLE` | Ruta absoluta al binario de LM Studio (opcional). Usada por el botón **Abrir LM Studio** si `lm-studio` no está en `PATH`. | — |
| `LM_STUDIO_EMBED_URL` | Si se define, el panel lateral puede activar una **vista embebida** (iframe) bajo las pestañas; no sustituye la app de escritorio (p. ej. documentación interna o una URL que permita `iframe`). | — |
| `LM_STUDIO_EMBED_HEIGHT` | Alto en píxeles del iframe cuando `LM_STUDIO_EMBED_URL` está definido. | `560` |

La **interfaz gráfica completa** de LM Studio (descargar/cargar modelos) solo existe como aplicación de escritorio; el puerto **1234** expone la **API**, no una réplica embebible de esa ventana.

Ejemplo antes de arrancar Streamlit:

```bash
export LM_STUDIO_BASE_URL="http://localhost:1234/v1"
export LM_STUDIO_MODEL="nombre-exacto-del-modelo-en-lm-studio"
./run_streamlit_lmstudio.sh
```

Si LM Studio escucha en **otro puerto** o en otra máquina, ajusta solo `LM_STUDIO_BASE_URL` (y firewall/red según corresponda).

---

## 6. LM Studio: instalación, modelo y servidor

Los pasos pueden variar ligeramente según la versión de LM Studio; la idea general es esta.

### 6.1 Instalar y descargar un modelo

1. Instala **LM Studio** desde [https://lmstudio.ai/](https://lmstudio.ai/) (Windows, macOS o Linux).
2. Abre la pestaña de **descarga de modelos**, elige un modelo en formato compatible (p. ej. GGUF) acorde a tu RAM/VRAM.
3. Descarga el modelo y espera a que el archivo esté disponible en el disco local del LM Studio.

### 6.2 Cargar el modelo en el chat

1. Ve a la sección **Chat** (o equivalente para cargar un modelo en memoria).
2. Selecciona el modelo descargado y **cárgalo** (Load) para que quede listo para inferencia.

Sin modelo cargado, el servidor puede no responder o devolver errores al llamar a `/v1/chat/completions`.

### 6.3 Poner en marcha el servidor local (API)

1. Abre la pestaña **Server** (o **Local Server**).
2. Comprueba el **puerto** (por defecto suele ser **1234**).
3. Activa **Start Server** (o el interruptor equivalente).
4. Asegúrate de que la API sea **compatible con OpenAI** (LM Studio lo ofrece de forma nativa para clientes tipo `ChatOpenAI` con `base_url` apuntando a `http://localhost:PUERTO/v1`).

La aplicación usa `langchain_openai.ChatOpenAI` con `api_key` ficticia (`lm-studio`) porque LM Studio no exige una clave real en local.

### 6.4 Comprobar que el servidor responde

Con el servidor en marcha:

```bash
curl -s http://localhost:1234/v1/models | head
```

Debes ver un JSON con la lista de modelos. El campo `id` de cada modelo es el que debes usar en la app (selector o campo **Otro id**).

Si cambias el puerto en LM Studio, actualiza `LM_STUDIO_BASE_URL` para que coincida (p. ej. `http://localhost:5678/v1`).

---

## 7. Lista de modelos en código (`MODELOS_CHAT_LM_STUDIO`)

En `rag_chain_lm.py` existe un diccionario:

```python
MODELOS_CHAT_LM_STUDIO: dict[str, str] = {
    "meta-llama-3.1-8b-instruct": "Llama 3.1 8B Instruct",
    ...
}
```

- La **clave** debe coincidir con el **`id`** que devuelve LM Studio en `/v1/models`.
- El **valor** es solo etiqueta legible en el desplegable de Streamlit.

**Cuando añadas un modelo nuevo:** incorpora una entrada `id: "Nombre legible"` o usa siempre el campo **Otro id** en la barra lateral sin tocar el código.

---

## 8. Arrancar la aplicación Streamlit

Desde la **raíz del proyecto** (donde está `app_lmstudio.py`):

```bash
chmod +x run_streamlit_lmstudio.sh   # solo la primera vez
./run_streamlit_lmstudio.sh
```

El script:

- Activa `venv/bin/activate` si existe.
- Exporta `LM_STUDIO_MODEL` con valor por defecto si no estaba definida.
- Ejecuta `streamlit run app_lmstudio.py`.

Streamlit mostrará una URL local, habitualmente **`http://localhost:8501`**. Abre esa URL en el navegador.

Arranque manual equivalente:

```bash
source venv/bin/activate
streamlit run app_lmstudio.py
```

Opciones útiles de Streamlit (puerto, headless, etc.): `streamlit run app_lmstudio.py --server.port 8502`.

---

## 9. Seleccionar el modelo en la interfaz

1. En la **barra lateral**, sección **Modelo LLM**, elige un modelo de la lista (ids definidos en `MODELOS_CHAT_LM_STUDIO`).
2. Si tu modelo **no** está en la lista, escribe su **`id` exacto** en **Otro id** (como en `/v1/models`). Ese valor **tiene prioridad** sobre el desplegable.
3. Asegúrate de que el mismo modelo esté **cargado y sirviendo** en LM Studio; si el id no existe en el servidor, fallará la generación.

El modelo elegido aplica a **chat, resumen, cuestionario y guía** (todos pasan por `rag_modes_lm.ejecutar_modo` con ese `model_id`).

---

## 10. Configuración de rutas y datos en disco

| Ruta (por defecto) | Uso |
|--------------------|-----|
| `./chroma_db` | Índice Chroma (embeddings de fragmentos). Definido como `DB_PATH` en `rag_chain_lm.py` y coherente en `app_lmstudio.py`. |
| `./docs` | Carpeta de documentos del proyecto y destino de archivos subidos desde Streamlit (`DOCS_PATH` en `app_lmstudio.py`). |

**Importante:** las rutas son relativas al **directorio de trabajo actual** al ejecutar `streamlit`. Lanza siempre desde la raíz del proyecto para que `./chroma_db` y `./docs` apunten al sitio esperado.

Parámetros de troceado (tamaño de chunk y solapamiento) están en `office_docs.vectorizar_y_persistir` (`chunk_size=500`, `chunk_overlap=50`). Ajustarlos implica reindexar para que el efecto sea completo.

---

## 11. Embeddings y primera indexación

- El modelo **`sentence-transformers/all-MiniLM-L6-v2`** se descarga vía Hugging Face la primera vez (cache habitual `~/.cache/huggingface`).
- Sin red en la primera descarga, fallará la creación del índice o la carga de Chroma.
- Tras cambiar el modelo de embeddings en código, conviene **borrar** `./chroma_db` y volver a indexar para mantener consistencia dimensional.

---

## 12. Depuración rápida

| Síntoma | Qué revisar |
|---------|-------------|
| Error de conexión al LLM | LM Studio con servidor iniciado; puerto y `LM_STUDIO_BASE_URL`; firewall. |
| `404` o modelo no encontrado | `id` del modelo igual al de `/v1/models`; modelo cargado en LM Studio. |
| Respuestas vacías o muy lentas | Tamaño del modelo vs. hardware; contexto muy largo; temperaturas en `prompts_notebooklm.configuracion_modo`. |
| Índice vacío o rutas raras | Ejecutar Streamlit desde la raíz del repo; permisos en `./docs` y `./chroma_db`. |
| Cuestionario sin JSON válido | Modelo instruct y temperatura; repetir generación; ver `PROMPT_CUESTIONARIO` en `prompts_notebooklm.py`. |
| **`Could not connect to tenant default_tenant`** (ChromaDB) | Suele deberse a un `./chroma_db` creado con **otra versión** de `chromadb` o a datos corruptos. **Cierra la app**, borra la carpeta `./chroma_db` (o usa **Borrar índice** en el panel), ejecuta `pip install -r requirements.txt` para alinear `chromadb` con el proyecto y **vuelve a indexar**. El código usa `chromadb.PersistentClient` vía `chroma_lm.py` para abrir el índice de forma estable. |

Comando útil para ver solo modelos disponibles:

```bash
curl -s http://localhost:1234/v1/models | python3 -m json.tool
```

---

## 13. Archivos clave para desarrolladores

| Archivo | Rol |
|---------|-----|
| `app_lmstudio.py` | UI Streamlit, indexación, multiselect de fuentes, llamadas a modos. |
| `rag_modes_lm.py` | Recuperación, filtro por `source`, invocación al LLM. |
| `office_docs.py` | Carga de ficheros, split, persistencia Chroma; **`indexar_carpeta_en_sistema`** (UI y `reindex.py`). |
| `reindex.py` | CLI de reindexación (sin LM Studio ni Streamlit); pensado para cron y post-sync. |
| `prompts_notebooklm.py` | Prompts, temperaturas y `k` de fragmentos por modo. |
| `rag_chain_lm.py` | `DB_PATH`, URL LM Studio, diccionario de modelos, cadena RAG de referencia. |
| `chroma_lm.py` | Cliente Chroma persistente (`PersistentClient`) compartido con LangChain; evita errores de tenant al abrir `./chroma_db`. |
| `run_streamlit_lmstudio.sh` | Arranque con venv y variable por defecto de modelo. |
| `run_reindex.sh` | Opcional: activa venv y ejecuta `reindex.py`. |

---

## 14. Referencias

- [Manual de usuario](./MANUAL_USUARIO.md) — uso final de la aplicación.
- [Diagramas UML (Mermaid)](./DIAGRAMAS_UML_MERMAID.md) — arquitectura y flujos.

---

*Documento orientado a desarrollo y operación local; adapta puertos y rutas si despliegas en otro entorno.*
