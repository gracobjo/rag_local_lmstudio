# Requirements Document

## Introduction

Este documento define los requisitos para un sistema de pruebas completo que verifique la funcionalidad del proyecto RAG (Retrieval-Augmented Generation) local. El sistema RAG utiliza LangChain, ChromaDB y LM Studio para proporcionar interfaces: CLI (`agent.py` / `agent_lmstudio.py`), API REST (`api_service.py` / `api_service_lmstudio.py`) y aplicación Streamlit principal **`app_lmstudio.py`** (sustituye o complementa el dashboard legado `app_dashboard.py`). El sistema de pruebas debe validar todos los componentes críticos, incluyendo ingesta de documentos (incl. **carpeta de oficina** vía `office_docs.py`), recuperación de información, **modos de contenido tipo NotebookLM** (`prompts_notebooklm.py`, `rag_modes_lm.py`), **cuestionario interactivo** y **filtrado por documentos**, **memoria conversacional** en el chat, funcionamiento de interfaces, integración con LM Studio (incl. **ids de modelo** alineados con `GET /v1/models`) y manejo de errores.

La **documentación de usuario**, **casos de uso** (`docs/CASOS_DE_USO.md`) y el **[README](../../../README.md)** de presentación en la raíz del repositorio deben mantenerse coherentes con los requisitos funcionales siguientes y con los criterios de aceptación de las secciones **Requirement 11** y **Requirement 12**.

## Documentación de requisitos funcionales del producto

Resumen en español del comportamiento esperado de la aplicación (para manuales, diagramas y presentación). Los **criterios formales de la Test_Suite** siguen en las secciones *Requirement 1–13* más abajo.

| ID | Requisito funcional | Descripción breve |
|----|----------------------|-------------------|
| **RF-01** | Ingesta multi-formato | Cargar PDF, TXT, Markdown y DOCX; troceado configurable; embeddings locales (`all-MiniLM-L6-v2`); persistencia en Chroma (`./chroma_db`). |
| **RF-02** | Indexación por carpeta o fusión | Indexar `./docs` o ruta absoluta con **reemplazo** del índice como fuente única; subidas a `./docs` con **fusión** incremental al índice existente. |
| **RF-03** | Chat RAG con memoria | Recuperación de fragmentos relevantes; prompt con historial de turnos para seguimientos; hechos acotados al contexto recuperado. |
| **RF-04** | Filtro por documentos | Multiselect de rutas (`source`) para limitar resumen, cuestionario, guía y chat a archivos seleccionados (vacío = todo el índice). |
| **RF-05** | Resumen estructurado | Modo resumen con enfoque opcional; salida Markdown; Guardar / Imprimir; persistencia del último resultado en sesión. |
| **RF-06** | Cuestionario JSON + UI interactiva | Generación JSON según `prompts_notebooklm`; parseo tolerante; UI con A–D, Comprobar, feedback y campos de trazabilidad (`fuente_archivo`, `numero_fragmento`, `donde_encontrarlo`). |
| **RF-07** | Guía de estudio | Modo guía con ángulo opcional; Markdown; Guardar / Imprimir. |
| **RF-08** | Contexto cuestionario con rutas | En modo cuestionario, el contexto enviado al LLM incluye la ruta de archivo por fragmento para favorecer citas correctas en el JSON. |
| **RF-09** | Contrato LM Studio | URL base (`LM_STUDIO_BASE_URL`), `id` de modelo alineado con `GET /v1/models`; mensajes claros si el modelo no está cargado o el `id` es inválido. |
| **RF-10** | Panel LM Studio opcional | Abrir app de escritorio (`LM_STUDIO_EXECUTABLE` / PATH); iframe opcional (`LM_STUDIO_EMBED_URL`, `LM_STUDIO_EMBED_HEIGHT`). |
| **RF-11** | Reindexación CLI | `reindex.py` reutiliza `indexar_carpeta_en_sistema`; opciones `--path`, `--merge`, `--db`, `--no-recursive`; sin LM Studio para la ingesta. |
| **RF-12** | Operación nube → disco | Documentación de flujos con sync (p. ej. `rclone`) + `reindex` periódico o manual. |
| **RF-13** | Chroma estable | Uso de `chromadb.PersistentClient` vía `chroma_lm.py` para abrir `./chroma_db` de forma coherente entre versiones. |
| **RF-14** | Gestión de sesión UI | Borrar historial de chat sin borrar índice; borrar índice desde la UI con efecto en `chroma_db` y selección de fuentes. |

**Trazabilidad:** los casos de uso textuales **CU-01–CU-12** en `docs/CASOS_DE_USO.md` cubren estos requisitos desde la perspectiva del usuario.

## Glossary

- **RAG_System**: Sistema completo de Retrieval-Augmented Generation que incluye ingesta, recuperación y generación de respuestas
- **Test_Suite**: Conjunto de pruebas automatizadas para validar el sistema RAG
- **Ingestion_Module**: Componente que carga y procesa documentos (`ingest.py`, `office_docs.py`)
- **RAG_Chain**: Cadena de recuperación y generación de respuestas (rag_chain.py)
- **CLI_Interface**: Interfaz de línea de comandos del agente (agent.py)
- **API_Service**: Servicio REST API (api_service.py)
- **Dashboard**: Interfaz web Streamlit legada (app_dashboard.py), si aplica
- **App_Streamlit_LM**: Interfaz principal Streamlit con LM Studio (`app_lmstudio.py`): pestañas Chat / Resumen / Cuestionario / Guía, selector de modelo, multiselect de documentos indexados, indexación por carpeta, memoria conversacional, cuestionario interactivo (opciones y comprobación), guardar/imprimir salidas, panel LM Studio opcional (embed / escritorio)
- **Office_Docs_Module**: Módulo de carga e indexación por carpeta (`office_docs.py`): PDF, TXT, Markdown, DOCX; indexación recursiva; vectorización con reemplazo total del índice o fusión incremental
- **Prompting_NotebookLM**: Plantillas y modos de contenido (`prompts_notebooklm.py`)
- **RAG_Modes_LM**: Ejecución de modos sobre Chroma + LM Studio (`rag_modes_lm.py`)
- **Reindex_CLI**: Script de línea de comandos `reindex.py` que invoca `indexar_carpeta_en_sistema` en `office_docs.py` para reindexar tras sync a disco o desde cron (sin Streamlit ni LM Studio para la ingesta)
- **ChromaDB**: Base de datos vectorial para almacenar embeddings
- **LM_Studio**: Servidor local de modelos de lenguaje
- **Agent_Tools**: Herramientas del agente (consultar_documentos, obtener_fecha_actual, buscar_palabra_clave_en_texto)
- **Test_Document**: Documento de prueba utilizado para validar funcionalidad
- **Embedding_Model**: Modelo sentence-transformers/all-MiniLM-L6-v2 para generar embeddings
- **Round_Trip_Test**: Prueba que verifica que una operación y su inversa retornan al estado original

## Requirements

### Requirement 1: Pruebas de Ingesta de Documentos

**User Story:** Como desarrollador, quiero verificar que el módulo de ingesta procesa correctamente documentos PDF y TXT, para asegurar que la base de conocimiento se construye adecuadamente.

#### Acceptance Criteria

1. WHEN a valid PDF file is provided, THE Ingestion_Module SHALL load and split the document into chunks
2. WHEN a valid TXT file is provided, THE Ingestion_Module SHALL load and split the document into chunks with UTF-8 encoding
3. WHEN documents are split, THE Ingestion_Module SHALL create chunks with size 500 and overlap 50
4. WHEN chunks are created, THE Ingestion_Module SHALL generate embeddings using the Embedding_Model
5. WHEN embeddings are generated, THE Ingestion_Module SHALL store them in ChromaDB at the configured DB_PATH
6. WHEN an unsupported file format is provided, THE Ingestion_Module SHALL skip the file and continue processing
7. WHEN the docs folder does not exist, THE Ingestion_Module SHALL handle the error gracefully and return an empty document list
8. THE Test_Suite SHALL verify that the number of chunks created matches the expected count for known test documents
9. WHEN the Office_Docs_Module loads a folder, THE Ingestion_Module SHALL accept PDF, TXT, MD/Markdown and DOCX (con dependencia `docx2txt` para DOCX), and SHALL support recursive directory walking
10. WHEN App_Streamlit_LM saves uploaded files, THE files SHALL be persisted under `./docs/` (además de vectorizarse)
11. WHEN a full-folder reindex is requested (docs/ or absolute path), THE vector store SHALL be rebuilt as single source of truth (replace index); WHEN incremental upload indexing is used, THE new chunks SHALL be merged into the existing Chroma index without requiring LM Studio for ingestion
12. WHEN Reindex_CLI is run with `--path` pointing to a folder on disk (e.g. after cloud sync to a local mirror), THE Office_Docs_Module SHALL use the same indexing logic as the Streamlit “index folder” action; WHEN `--merge` is omitted, THE vector store SHALL be replaced; WHEN `--merge` is set, THE new chunks SHALL be merged into the existing Chroma index
13. WHEN operators document cloud-as-source-of-truth workflows, THE documentation SHALL describe sync-to-disk plus periodic or manual `reindex.py` execution (including optional `rclone` and `cron` examples)

### Requirement 2: Pruebas de Recuperación RAG

**User Story:** Como desarrollador, quiero verificar que la cadena RAG recupera información relevante de los documentos indexados, para garantizar respuestas precisas a las consultas.

#### Acceptance Criteria

1. WHEN a query is submitted, THE RAG_Chain SHALL retrieve the 4 most relevant document chunks from ChromaDB
2. WHEN relevant chunks are retrieved, THE RAG_Chain SHALL send them as context to LM_Studio
3. WHEN LM_Studio is unavailable, THE RAG_Chain SHALL return a connection error message
4. WHEN a query has no relevant information in the indexed documents, THE RAG_Chain SHALL respond with "No tengo información sobre eso"
5. THE Test_Suite SHALL verify that retrieved chunks have relevance scores above a minimum threshold
6. THE Test_Suite SHALL verify that source documents are correctly tracked and returned with responses
7. WHEN the same query is submitted multiple times, THE RAG_Chain SHALL return consistent results (idempotence property)

### Requirement 3: Pruebas de Herramientas del Agente

**User Story:** Como desarrollador, quiero verificar que las herramientas del agente funcionan correctamente, para asegurar que el agente puede ejecutar acciones específicas.

#### Acceptance Criteria

1. WHEN consultar_documentos tool is invoked with a query, THE Agent_Tools SHALL return a response from the RAG_Chain
2. WHEN obtener_fecha_actual tool is invoked, THE Agent_Tools SHALL return the current system date and time in the format "%A, %d de %B de %Y, %H:%M"
3. WHEN buscar_palabra_clave_en_texto tool is invoked with a keyword, THE Agent_Tools SHALL return the count of occurrences in relevant document fragments
4. WHEN a tool encounters an error, THE Agent_Tools SHALL return a descriptive error message instead of crashing
5. THE Test_Suite SHALL verify that each tool returns the expected data type
6. THE Test_Suite SHALL verify that tool execution time is within acceptable limits (under 30 seconds per tool)

### Requirement 4: Pruebas de la Interfaz CLI

**User Story:** Como desarrollador, quiero verificar que la interfaz CLI del agente procesa comandos correctamente, para asegurar una experiencia de usuario funcional.

#### Acceptance Criteria

1. WHEN the CLI_Interface is started, THE CLI_Interface SHALL initialize the agent executor successfully
2. WHEN a user query is submitted, THE CLI_Interface SHALL invoke the agent and return a response
3. WHEN the agent needs to use a tool, THE CLI_Interface SHALL display the reasoning process (verbose mode)
4. WHEN the agent reaches max_iterations limit, THE CLI_Interface SHALL stop execution and return the current state
5. WHEN a parsing error occurs, THE CLI_Interface SHALL handle it gracefully without crashing
6. THE Test_Suite SHALL verify that the CLI can process at least 5 consecutive queries without errors

### Requirement 5: Pruebas de la API REST

**User Story:** Como desarrollador, quiero verificar que el servicio API REST responde correctamente a las solicitudes HTTP, para garantizar la integración con aplicaciones externas.

#### Acceptance Criteria

1. WHEN a GET request is sent to the root endpoint, THE API_Service SHALL return status "online" with server time
2. WHEN a POST request is sent to /chat with valid session_id and pregunta, THE API_Service SHALL return a ChatResponse with respuesta and timestamp
3. WHEN a POST request is sent to /upload with a valid PDF or TXT file, THE API_Service SHALL save the file and trigger indexing
4. WHEN a POST request is sent to /upload with an unsupported file format, THE API_Service SHALL return HTTP 400 error
5. WHEN a DELETE request is sent to /session/{session_id}, THE API_Service SHALL clear the conversation memory for that session
6. WHEN multiple requests are sent with the same session_id, THE API_Service SHALL maintain conversation context across requests
7. WHEN LM_Studio is unavailable, THE API_Service SHALL return HTTP 500 error with descriptive message
8. THE Test_Suite SHALL verify that API response times are under 5 seconds for chat requests (excluding LLM processing time)

### Requirement 6: Pruebas de Integración con LM Studio

**User Story:** Como desarrollador, quiero verificar que la integración con LM Studio funciona correctamente, para asegurar que el sistema puede generar respuestas usando el modelo local.

#### Acceptance Criteria

1. WHEN LM_Studio is running on localhost:1234, THE RAG_System SHALL successfully connect and send requests
2. WHEN a request is sent to LM_Studio, THE RAG_System SHALL receive a valid response within the timeout period
3. WHEN LM_Studio is not running, THE RAG_System SHALL detect the connection failure and return an appropriate error message
4. THE Test_Suite SHALL verify that the LM_Studio connection uses the correct base_url "http://localhost:1234/v1"
5. THE Test_Suite SHALL verify that requests include the configured temperature parameter (0.1)
6. THE Test_Suite SHALL include a mock LM_Studio server for testing without requiring the actual service

### Requirement 7: Pruebas de Manejo de Errores

**User Story:** Como desarrollador, quiero verificar que el sistema maneja errores de forma robusta, para prevenir fallos catastróficos en producción.

#### Acceptance Criteria

1. WHEN ChromaDB directory does not exist, THE RAG_System SHALL return a clear error message indicating the database needs initialization
2. WHEN an invalid file path is provided, THE Ingestion_Module SHALL handle the FileNotFoundError gracefully
3. WHEN embeddings generation fails, THE Ingestion_Module SHALL log the error and continue with remaining documents
4. WHEN a malformed query is submitted, THE RAG_Chain SHALL handle the error without crashing
5. WHEN memory allocation fails during document processing, THE RAG_System SHALL release resources and report the error
6. THE Test_Suite SHALL verify that all error messages are descriptive and include actionable information
7. THE Test_Suite SHALL verify that the system can recover from transient errors (retry logic where applicable)

### Requirement 8: Pruebas de Propiedades del Sistema

**User Story:** Como desarrollador, quiero verificar propiedades invariantes del sistema, para asegurar comportamiento consistente bajo diferentes condiciones.

#### Acceptance Criteria

1. THE Test_Suite SHALL verify that document chunk count equals the sum of chunks from all processed documents (invariant property)
2. THE Test_Suite SHALL verify that indexing a document twice does not duplicate chunks in ChromaDB (idempotence property)
3. THE Test_Suite SHALL verify that the order of document processing does not affect the final indexed content (confluence property)
4. THE Test_Suite SHALL verify that retrieved document chunks always have valid metadata including source file path (invariant property)
5. THE Test_Suite SHALL verify that conversation memory size grows linearly with the number of messages (invariant property)
6. THE Test_Suite SHALL verify that session isolation is maintained (queries in session A do not affect session B)

### Requirement 9: Pruebas de Rendimiento y Límites

**User Story:** Como desarrollador, quiero verificar que el sistema funciona dentro de límites de rendimiento aceptables, para garantizar una experiencia de usuario satisfactoria.

#### Acceptance Criteria

1. WHEN processing a 10-page PDF document, THE Ingestion_Module SHALL complete indexing within 60 seconds
2. WHEN retrieving documents from ChromaDB, THE RAG_Chain SHALL return results within 2 seconds
3. WHEN the API receives 10 concurrent requests, THE API_Service SHALL handle all requests without errors
4. THE Test_Suite SHALL verify that memory usage remains below 2GB during normal operation
5. THE Test_Suite SHALL verify that ChromaDB size grows proportionally to the number of indexed documents
6. THE Test_Suite SHALL verify that the system can handle at least 100 documents in the knowledge base

### Requirement 10: Infraestructura de Pruebas y Reportes

**User Story:** Como desarrollador, quiero una infraestructura de pruebas automatizada con reportes claros, para facilitar el desarrollo continuo y la detección temprana de regresiones.

#### Acceptance Criteria

1. THE Test_Suite SHALL use pytest as the testing framework
2. THE Test_Suite SHALL organize tests in separate modules by component (e.g. `test_ingest.py`, `test_rag_chain.py`, `test_rag_chain_lm.py`, `test_office_docs.py`, `test_rag_modes_lm.py`, `test_app_lmstudio.py`, `test_agent.py`, `test_api.py`)
3. THE Test_Suite SHALL provide fixtures for common test setup (test documents, mock LM Studio, temporary ChromaDB)
4. THE Test_Suite SHALL generate coverage reports showing at least 80% code coverage
5. THE Test_Suite SHALL include integration tests that verify end-to-end workflows
6. THE Test_Suite SHALL provide clear test output with pass/fail status and execution time for each test
7. THE Test_Suite SHALL include a README with instructions for running tests and interpreting results
8. WHEN tests fail, THE Test_Suite SHALL provide detailed error messages with context for debugging
9. THE Test_Suite SHALL support running tests in isolation (each test cleans up its resources)
10. THE Test_Suite SHALL include a CI/CD configuration file for automated testing on code changes

### Requirement 11: Pruebas de la aplicación Streamlit LM (`app_lmstudio.py`)

**User Story:** Como desarrollador, quiero verificar la aplicación Streamlit principal que concentra chat, documentación de oficina y modos de generación, para asegurar regresiones mínimas en la experiencia de usuario.

#### Acceptance Criteria

1. THE Test_Suite SHALL reference `app_lmstudio.py` como superficie de UI principal (junto a mocks de Streamlit o pruebas de import/lógica donde aplique)
2. WHEN the user switches LLM model id in the sidebar, THE App_Streamlit_LM SHALL pass that id to ChatOpenAI-compatible calls (mismo criterio que `rag_chain_lm.LM_STUDIO_MODEL` / variable de entorno)
3. WHEN indexing from `./docs` or an absolute path, THE App_Streamlit_LM SHALL invoke Office_Docs_Module with `reemplazar_indice=True` for full-folder single-source behaviour
4. WHEN uploading files, THE App_Streamlit_LM SHALL persist copies under `./docs/` and call `vectorizar_y_persistir(..., reemplazar_indice=False)` to merge chunks
5. THE Test_Suite SHALL cover tabbed areas: Chat, Resumen, Cuestionario, Guía de estudio at minimum at integration or smoke level where feasible
6. WHEN the user selects one or more indexed source files in the sidebar multiselect, THE App_Streamlit_LM SHALL restrict retrieval/filtering so that generated content (resumen, cuestionario, guía) uses only chunks from those sources where the implementation applies metadata filtering
7. WHEN Cuestionario JSON is successfully parsed, THE App_Streamlit_LM SHALL render **interactive** questions (radio A–D, **Comprobar**, feedback correcto/incorrecto, explicación) and SHALL expose traceability fields (`fuente_archivo`, `numero_fragmento`, `donde_encontrarlo`) with resolvable file links where paths are known
8. WHEN Resumen, Cuestionario or Guía outputs are generated, THE App_Streamlit_LM SHALL keep the latest structured result in session state and SHALL offer **Guardar** (download JSON/text) and **Imprimir** (browser print) actions consistent with the UI implementation
9. WHEN `LM_STUDIO_EMBED_URL` is set, THE App_Streamlit_LM MAY show an optional web embed in the LM Studio expander; WHEN `LM_STUDIO_EXECUTABLE` is set, THE UI MAY offer opening the LM Studio desktop app from the sidebar
10. WHEN LM Studio returns an error indicating no loaded model (or equivalent), THE App_Streamlit_LM SHALL surface a clear, user-facing message instead of a raw stack trace

### Requirement 12: Pruebas de modos de contenido y memoria conversacional

**User Story:** Como desarrollador, quiero verificar los modos tipo NotebookLM y la memoria del chat, para validar prompts y flujo RAG multimodo.

#### Acceptance Criteria

1. WHEN ModoContenido.CHAT runs with non-empty `historial_conversacion`, THE RAG_Modes_LM SHALL use `PROMPT_CHAT_MEMORIA` and SHALL combine retrieval query with recent history for follow-up questions
2. WHEN Resumen, Cuestionario or Guía modes run, THE RAG_Modes_LM SHALL use distinct prompts and retrieval breadth (`k` / temperature) per `configuracion_modo`
3. WHEN Cuestionario mode returns JSON, THE App_Streamlit_LM SHALL attempt to parse and render structured questions; WHEN JSON is invalid, THE UI SHALL fall back to raw model text
4. WHEN Cuestionario retrieval builds context, THE RAG_Modes_LM SHALL annotate each chunk with its source file path (or equivalent metadata) so the model can populate `fuente_archivo`, `numero_fragmento`, and related traceability fields in the JSON schema from `prompts_notebooklm.py`
5. THE Test_Suite SHALL verify that facts in generated answers remain conditioned on retrieved context (no fabricated citations from empty index) where testable with mocks

### Requirement 13: Contrato LM Studio (modelo e identificadores)

**User Story:** Como desarrollador, quiero que las pruebas reflejen el contrato real del servidor local (OpenAI-compatible), evitando el placeholder `local-model` cuando el despliegue usa ids reales de `GET /v1/models`.

#### Acceptance Criteria

1. THE Test_Suite SHALL allow configuring `LM_STUDIO_MODEL` / `LM_STUDIO_BASE_URL` via environment for tests against mocks
2. THE Mock LM Studio server SHOULD accept `model` field in chat completions body and echo or validate it for regression tests
3. THE Test_Suite SHALL document that production ids (e.g. `meta-llama-3.1-8b-instruct`, `qwen/qwen3.5-9b`) come from the running LM Studio instance, not a hardcoded `local-model` string in `rag_chain_lm`
