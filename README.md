# RAG local con LM Studio

Aplicación de **consulta aumentada por recuperación (RAG)** sobre documentación propia: los textos se fragmentan, se vectorizan en local con **ChromaDB** y **sentence-transformers**, y un modelo de lenguaje servido por **LM Studio** (API compatible con OpenAI) genera respuestas **basadas en los fragmentos recuperados**.

Interfaz principal: **Streamlit** (`app_lmstudio.py`) con chat con memoria, resumen, cuestionario interactivo (JSON + opciones A–D), guía de estudio, filtrado por documentos indexados y reindexación programable (`reindex.py`).

---

## En qué consiste el proyecto

| Aspecto | Detalle |
|--------|---------|
| **Privacidad** | Embeddings y índice en disco local; el LLM se ejecuta en tu máquina vía LM Studio. |
| **Stack** | Python, LangChain, ChromaDB, Streamlit, LM Studio (OpenAI-compatible). |
| **Documentos** | PDF, TXT, Markdown, DOCX (indexación por carpeta o subida). |
| **Modos** | Chat RAG, resumen ejecutivo, cuestionario con trazabilidad a fuentes, guía de estudio. |

---

## Requisitos

- **Python 3.10+** (recomendado 3.11).
- **LM Studio** con servidor local activo y modelo de chat cargado ([lmstudio.ai](https://lmstudio.ai/)).
- Espacio para `./chroma_db` y caché de Hugging Face la primera vez que se cargan embeddings.

---

## Instalación rápida

```bash
git clone https://github.com/gracobjo/rag_local_lmstudio.git
cd rag_local_lmstudio
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Variables opcionales (antes de arrancar Streamlit):

```bash
export LM_STUDIO_BASE_URL="http://localhost:1234/v1"
export LM_STUDIO_MODEL="tu-id-exacto-segun-v1-models"
```

---

## Arranque

1. Inicia LM Studio y el **servidor local** (puerto habitual **1234**).
2. Carga un modelo en la pestaña Chat del propio LM Studio.
3. Desde la raíz del proyecto:

```bash
chmod +x run_streamlit_lmstudio.sh   # solo la primera vez
./run_streamlit_lmstudio.sh
```

Abre la URL que muestre la consola (por defecto `http://localhost:8501`).

---

## Flujo mínimo (enunciado práctica RAG)

Orden alineado con el PDF *Práctica Final RAG / LangChain* (Apartados A–C):

1. Coloca en **`./docs`** al menos **3 ficheros PDF o TXT** y un mínimo recomendado de **~10 páginas** en total (requisito del enunciado para la entrega).
2. Activa el venv y ejecuta **`python ingest.py`** — construye o actualiza **`./chroma_db`** (Apartado A: carga + chunks + embeddings locales).
3. Con LM Studio en marcha, ejecuta **`python agent.py`** — agente CLI con tools RAG + fecha + búsqueda por palabra (Apartado C). Opcional: `python agent_lmstudio.py` si usas la variante con `rag_chain_lm`.
4. La interfaz completa Streamlit (`./run_streamlit_lmstudio.sh`) es **adicional** al mínimo del enunciado; para la práctica basta ingest + agent si así lo pide el profesor.

La cadena RAG clásica está en **`rag_chain.py`** (Apartado B); la app principal usa **`rag_chain_lm.py`** con ids de modelo reales.

---

## Documentación

| Documento | Contenido |
|-----------|-----------|
| [Manual de usuario](docs/MANUAL_USUARIO.md) | Funciones, panel lateral, pestañas, limitaciones. |
| [Manual de desarrollo](docs/MANUAL_DESARROLLO.md) | Entorno, variables, LM Studio, `reindex.py`, cron, depuración. |
| [Casos de uso](docs/CASOS_DE_USO.md) | Actores, precondiciones y flujos por caso. |
| [Diagramas UML (Mermaid)](docs/DIAGRAMAS_UML_MERMAID.md) | Componentes, secuencias, estados, casos de uso (vista gráfica). |
| [Requisitos (spec de pruebas + RF producto)](.kiro/specs/rag-testing-system/requirements.md) | Criterios de aceptación para tests y resumen de requisitos funcionales. |
| [Diseño técnico (pruebas)](.kiro/specs/rag-testing-system/design.md) | Arquitectura del sistema de pruebas y módulos del producto. |

Índice breve de la carpeta `docs/`: [docs/README.md](docs/README.md).

---

## Scripts útiles

| Script | Uso |
|--------|-----|
| `ingest.py` | Indexa PDF/TXT de `./docs` en `./chroma_db` (Apartado A del enunciado). |
| `run_streamlit_lmstudio.sh` | Lanza la app Streamlit principal. |
| `reindex.py` | Reindexa una carpeta desde línea de órdenes (cron, post-sync). |
| `run_reindex.sh` | Activa `venv` y delega en `reindex.py`. |
| `run_api_lmstudio.sh` | API REST alternativa (FastAPI), si la usas. |

---

## Presentación y demo

- Prepara un **índice pequeño** y un modelo ya **cargado** en LM Studio antes de la demo.
- Comprueba `GET /v1/models` (o la UI de LM Studio) para que el **id del modelo** coincida con el selector o con `LM_STUDIO_MODEL`.
- Para narrativa de **nube → disco → índice**, véase el manual de desarrollo (`reindex.py`, ejemplos en `docs/examples/`).

---

## Licencia y autoría

Ajusta esta sección según la licencia que aplique a tu entrega (proyecto académico, código interno, etc.).

---

*Repositorio orientado a uso local; las rutas `./docs` y `./chroma_db` son relativas al directorio desde el que se ejecuta Streamlit.*
