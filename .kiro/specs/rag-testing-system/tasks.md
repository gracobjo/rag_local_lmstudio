# Implementation Plan: Sistema de Pruebas RAG

## Overview

Este plan descompone la implementación del sistema de pruebas RAG en tareas ejecutables. El sistema validará un proyecto RAG que utiliza LangChain, ChromaDB y LM Studio mediante pruebas unitarias, de integración y basadas en propiedades (property-based testing). **El producto actual expone sobre todo `app_lmstudio.py`, `office_docs.py`, `rag_chain_lm.py`, `rag_modes_lm.py` y `prompts_notebooklm.py`**; las pruebas deben ampliarse para cubrir estos módulos además de `ingesta.py`, `rag_chain.py`, `agent.py` y `api_service.py`. El objetivo es alcanzar 80% de cobertura de código con pytest y hypothesis.

## Tasks

- [x] 0. Ingesta programada y documentación operativa (producto)
  - [x] 0.1 Centralizar `indexar_carpeta_en_sistema` en `office_docs.py` y reutilizarla desde `app_lmstudio.py`
  - [x] 0.2 Añadir `reindex.py` (CLI: `--path`, `--merge`, `--db`, `--no-recursive`) y `run_reindex.sh`
  - [x] 0.3 Documentar estructura de repo, módulos `.py`, flujo nube→disco→reindex en `docs/MANUAL_DESARROLLO.md`; ejemplo `docs/examples/reindex_cron_rclone.example.sh`
  - [x] 0.4 Actualizar diagramas en `docs/DIAGRAMAS_UML_MERMAID.md` (componentes + ingesta programada)
  - _Requirements: 1.11–1.13_

- [x] 0.5 Cuestionario interactivo, trazabilidad y UX LM Studio (producto)
  - [x] 0.5.1 Esquema JSON ampliado en `prompts_notebooklm.py` (`fuente_archivo`, `numero_fragmento`, `donde_encontrarlo`, etc.)
  - [x] 0.5.2 Contexto de recuperación en modo CUESTIONARIO con `(archivo: ruta)` por fragmento en `rag_modes_lm.py`
  - [x] 0.5.3 UI `_render_cuestionario_interactivo` en `app_lmstudio.py` (A–D, Comprobar, feedback, enlaces `file://` cuando aplica)
  - [x] 0.5.4 Multiselect de fuentes indexadas; persistencia de último resumen/cuestionario/guía; `_render_guardar_imprimir`
  - [x] 0.5.5 Panel LM Studio: `LM_STUDIO_EMBED_URL`, `LM_STUDIO_EMBED_HEIGHT`, `LM_STUDIO_EXECUTABLE`; mensajes amigables si el modelo no está cargado
  - [x] 0.5.6 `chroma_lm.py` con `PersistentClient`; documentación de diagramas alineada con flujos actuales
  - _Requirements: 11.6–11.10, 12.4_

- [x] 0.6 Presentación, requisitos funcionales y casos de uso (documentación)
  - [x] 0.6.1 `README.md` en raíz; `docs/CASOS_DE_USO.md`; `docs/README.md` (índice)
  - [x] 0.6.2 Tabla RF-01–RF-14 y enlaces en `requirements.md`; manuales usuario/desarrollo actualizados
  - [x] 0.6.3 Diagramas Mermaid: casos de uso ampliados + matriz RF ↔ CU en `DIAGRAMAS_UML_MERMAID.md`
  - _Requirements: documentación alineada con Req. 11–12 y RF_

- [ ] 1. Configurar infraestructura de testing
  - [ ] 1.1 Crear estructura de directorios y archivos base
    - Crear directorio `tests/` con subdirectorios `fixtures/`, `mocks/`, `utils/`
    - Crear archivos vacíos: `conftest.py`, `test_ingesta.py`, `test_rag_chain.py`, `test_rag_chain_lm.py`, `test_agent.py`, `test_api.py`, `test_dashboard.py`, `test_app_lmstudio.py`, `test_office_docs.py`, `test_rag_modes_lm.py`, `test_integration.py`, `test_properties.py`
    - Crear `requirements-dev.txt` con dependencias de testing
    - _Requirements: 10.1, 10.2_
  
  - [ ] 1.2 Configurar pytest con pytest.ini
    - Crear archivo `pytest.ini` con configuración de testpaths, markers, y opciones de coverage
    - Configurar markers: unit, integration, slow, requires_lm_studio
    - Configurar coverage mínimo de 80%
    - _Requirements: 10.1, 10.4_
  
  - [ ] 1.3 Implementar fixtures compartidas en conftest.py
    - Implementar fixture `mock_lm_studio_server` (scope="session")
    - Implementar fixture `temp_chroma_db` (scope="function")
    - Implementar fixture `test_documents` (scope="session")
    - Implementar fixture `clean_environment` (autouse=True)
    - Implementar fixture `api_client` (scope="function")
    - _Requirements: 10.3, 10.9_

- [ ] 2. Implementar mock del servidor LM Studio
  - [ ] 2.0 Alinear mock con API real
    - Soportar `GET /v1/models` con lista de ids de ejemplo (`meta-llama-3.1-8b-instruct`, etc.) para pruebas de configuración
    - Aceptar campo `model` en el cuerpo de `chat/completions` y reflejarlo en la respuesta mock
    - _Requirements: 13_
  - [ ] 2.1 Crear clase MockLMStudioServer
    - Implementar servidor HTTP mock en `mocks/mock_lm_studio.py`
    - Implementar métodos: `__init__`, `start`, `stop`, `set_response`, `set_error`, `get_request_history`
    - Usar threading para ejecutar servidor en background
    - Simular endpoint POST /v1/chat/completions
    - _Requirements: 6.6_
  
  - [ ] 2.2 Implementar respuestas configurables y registro de solicitudes
    - Permitir configurar respuestas mock personalizadas
    - Registrar historial de solicitudes recibidas
    - Simular latencia configurable
    - Simular errores de conexión y timeouts
    - _Requirements: 6.6_

- [ ] 3. Crear documentos y datos de prueba
  - [ ] 3.1 Crear fixtures de documentos de prueba
    - Crear directorio `tests/fixtures/test_documents/`
    - Crear archivos de prueba: PDF simple, TXT simple, PDF grande
    - Implementar `fixtures/test_data.py` con TestDocument dataclass
    - Implementar `fixtures/mock_responses.py` con MockLMStudioResponse dataclass
    - _Requirements: 10.3_

- [ ] 4. Implementar pruebas del módulo de ingesta
  - [ ] 4.1 Escribir pruebas de carga de documentos
    - Implementar `test_load_pdf_document` en `test_ingesta.py`
    - Implementar `test_load_txt_document_utf8`
    - Implementar `test_unsupported_file_format`
    - Implementar `test_missing_docs_folder`
    - _Requirements: 1.1, 1.2, 1.6, 1.7_
  
  - [ ] 4.2 Escribir pruebas de chunking y embeddings
    - Implementar `test_document_chunking` verificando size=500 y overlap=50
    - Implementar `test_embedding_generation`
    - Implementar `test_chromadb_storage`
    - Implementar `test_chunk_count_matches_expected`
    - _Requirements: 1.3, 1.4, 1.5, 1.8_

- [ ] 5. Implementar pruebas de la cadena RAG
  - [ ] 5.0 (Opcional) Pruebas de `rag_chain_lm.py`
    - Verificar que `crear_cadena_rag` usa `LM_STUDIO_MODEL` y URL de entorno cuando están definidos
    - Mock de ChatOpenAI o del cliente HTTP para no requerir LM Studio en CI
    - _Requirements: 13, 6_
  - [ ] 5.1 Escribir pruebas de recuperación de chunks
    - Implementar `test_retrieve_relevant_chunks` verificando k=4 (cadena legada); para `rag_modes_lm` verificar `k` según `configuracion_modo`
    - Implementar `test_relevance_scores_threshold`
    - Implementar `test_source_tracking`
    - _Requirements: 2.1, 2.5, 2.6_
  
  - [ ] 5.2 Escribir pruebas de integración con LM Studio
    - Implementar `test_send_context_to_lm_studio`
    - Implementar `test_lm_studio_unavailable`
    - Implementar `test_no_relevant_information`
    - Implementar `test_query_idempotence`
    - _Requirements: 2.2, 2.3, 2.4, 2.7_

- [ ] 6. Implementar pruebas de herramientas del agente
  - [ ] 6.1 Escribir pruebas de herramientas individuales
    - Implementar `test_consultar_documentos_tool`
    - Implementar `test_obtener_fecha_actual_tool` verificando formato "%A, %d de %B de %Y, %H:%M"
    - Implementar `test_buscar_palabra_clave_tool`
    - Implementar `test_tool_error_handling`
    - Implementar `test_tool_return_types`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [ ]* 6.2 Escribir prueba de rendimiento de herramientas
    - Implementar `test_tool_execution_time` verificando límite de 30 segundos
    - _Requirements: 3.6_

- [ ] 7. Implementar pruebas de la interfaz CLI
  - [ ] 7.1 Escribir pruebas de inicialización y procesamiento
    - Implementar `test_cli_initialization`
    - Implementar `test_process_user_query`
    - Implementar `test_verbose_mode_reasoning`
    - Implementar `test_consecutive_queries` verificando al menos 5 queries
    - _Requirements: 4.1, 4.2, 4.3, 4.6_
  
  - [ ] 7.2 Escribir pruebas de manejo de errores CLI
    - Implementar `test_max_iterations_limit`
    - Implementar `test_parsing_error_handling`
    - _Requirements: 4.4, 4.5_

- [ ] 8. Implementar pruebas del servicio API REST
  - [ ] 8.1 Escribir pruebas de endpoints básicos
    - Implementar `test_root_endpoint` verificando status "online"
    - Implementar `test_chat_endpoint` verificando ChatResponse
    - Implementar `test_delete_session_endpoint`
    - _Requirements: 5.1, 5.2, 5.5_
  
  - [ ] 8.2 Escribir pruebas de upload de archivos
    - Implementar `test_upload_pdf_endpoint`
    - Implementar `test_upload_txt_endpoint`
    - Implementar `test_upload_unsupported_format` verificando HTTP 400
    - _Requirements: 5.3, 5.4_
  
  - [ ] 8.3 Escribir pruebas de gestión de sesiones y errores
    - Implementar `test_session_context_maintenance`
    - Implementar `test_lm_studio_unavailable_error` verificando HTTP 500
    - _Requirements: 5.6, 5.7_
  
  - [ ]* 8.4 Escribir prueba de rendimiento de API
    - Implementar `test_api_response_time` verificando límite de 5 segundos
    - _Requirements: 5.8_

- [ ] 9. Implementar pruebas de integración con LM Studio
  - [ ] 9.1 Escribir pruebas de conexión y configuración
    - Implementar `test_lm_studio_connection` verificando localhost:1234
    - Implementar `test_lm_studio_request_response` verificando timeout
    - Implementar `test_lm_studio_connection_failure`
    - Implementar `test_lm_studio_base_url` verificando "http://localhost:1234/v1"
    - Implementar `test_lm_studio_temperature` verificando temperature=0.1
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 10. Implementar pruebas de manejo de errores
  - [ ] 10.1 Escribir pruebas de errores de ChromaDB
    - Implementar `test_chromadb_not_initialized`
    - Implementar `test_chromadb_error_messages`
    - _Requirements: 7.1_
  
  - [ ] 10.2 Escribir pruebas de errores de ingesta
    - Implementar `test_invalid_file_path_handling`
    - Implementar `test_embeddings_generation_failure`
    - Implementar `test_malformed_query_handling`
    - _Requirements: 7.2, 7.3, 7.4_
  
  - [ ] 10.3 Escribir pruebas de mensajes de error y recuperación
    - Implementar `test_error_messages_descriptive` verificando información accionable
    - Implementar `test_transient_error_recovery` verificando retry logic
    - _Requirements: 7.6, 7.7_

- [ ] 11. Checkpoint - Verificar pruebas unitarias
  - Ejecutar `pytest tests/ -m "unit" --cov` y verificar que todas las pruebas pasen
  - Revisar cobertura de código y identificar áreas sin cubrir
  - Preguntar al usuario si hay dudas o ajustes necesarios

- [ ] 12. Implementar pruebas basadas en propiedades (property-based testing)
  - [ ] 12.1 Configurar Hypothesis y estrategias de generación
    - Crear estrategias en `test_properties.py`: `document_strategy`, `queries_strategy`, `session_id_strategy`, `conversation_strategy`
    - Configurar `@settings(max_examples=100)` para todas las propiedades
    - _Requirements: 10.1_
  
  - [ ]* 12.2 Implementar Property 1: Document Loading and Chunking
    - **Property 1: Document Loading and Chunking**
    - **Validates: Requirements 1.1, 1.2, 1.3**
    - Verificar que chunks tengan size=500 y overlap=50
    - Verificar que el número de chunks sea determinístico
  
  - [ ]* 12.3 Implementar Property 2: Embedding Storage Round-Trip
    - **Property 2: Embedding Storage Round-Trip**
    - **Validates: Requirements 1.4, 1.5, 8.4**
    - Verificar que embeddings recuperados tengan misma dimensionalidad
    - Verificar que metadata incluya source file path
  
  - [ ]* 12.4 Implementar Property 3: Unsupported File Format Handling
    - **Property 3: Unsupported File Format Handling**
    - **Validates: Requirements 1.6**
    - Verificar que archivos no soportados se salten sin crashear
  
  - [ ]* 12.5 Implementar Property 4: Chunk Count Invariant
    - **Property 4: Chunk Count Invariant**
    - **Validates: Requirements 8.1**
    - Verificar que total de chunks = suma de chunks individuales
  
  - [ ]* 12.6 Implementar Property 5: Retrieval Consistency
    - **Property 5: Retrieval Consistency**
    - **Validates: Requirements 2.1, 2.5, 2.7**
    - Verificar que se recuperen exactamente 4 chunks
    - Verificar idempotencia de queries
  
  - [ ]* 12.7 Implementar Property 6: RAG Data Integrity
    - **Property 6: RAG Data Integrity**
    - **Validates: Requirements 2.2, 2.6**
    - Verificar tracking de documentos fuente
    - Verificar que chunks enviados a LM Studio coincidan con recuperados
  
  - [ ]* 12.8 Implementar Property 7: Agent Tool Correctness
    - **Property 7: Agent Tool Correctness**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
    - Verificar tipos de datos retornados por herramientas
    - Verificar manejo graceful de errores
  
  - [ ]* 12.9 Implementar Property 8: CLI Query Processing
    - **Property 8: CLI Query Processing**
    - **Validates: Requirements 4.2, 4.3**
    - Verificar que queries retornen respuestas
    - Verificar display de razonamiento en verbose mode
  
  - [ ]* 12.10 Implementar Property 9: CLI Error Resilience
    - **Property 9: CLI Error Resilience**
    - **Validates: Requirements 4.5**
    - Verificar manejo graceful de parsing errors
    - Verificar que CLI continúe aceptando queries después de errores
  
  - [ ]* 12.11 Implementar Property 10: API Chat Endpoint Correctness
    - **Property 10: API Chat Endpoint Correctness**
    - **Validates: Requirements 5.2, 5.6**
    - Verificar formato de ChatResponse
    - Verificar mantenimiento de contexto por sesión
  
  - [ ]* 12.12 Implementar Property 11: API Upload Endpoint Correctness
    - **Property 11: API Upload Endpoint Correctness**
    - **Validates: Requirements 5.3, 5.4**
    - Verificar guardado e indexación de archivos válidos
    - Verificar HTTP 400 para formatos no soportados
  
  - [ ]* 12.13 Implementar Property 12: API Session Management
    - **Property 12: API Session Management**
    - **Validates: Requirements 5.5**
    - Verificar limpieza de memoria de conversación
    - Verificar que queries posteriores no tengan acceso a historial eliminado
  
  - [ ]* 12.14 Implementar Property 13: LM Studio Request Validity
    - **Property 13: LM Studio Request Validity**
    - **Validates: Requirements 6.2**
    - Verificar respuestas válidas dentro del timeout
  
  - [ ]* 12.15 Implementar Property 14: Error Handling Robustness
    - **Property 14: Error Handling Robustness**
    - **Validates: Requirements 7.2, 7.3, 7.4, 7.6**
    - Verificar manejo graceful de errores variados
    - Verificar mensajes descriptivos con información accionable
  
  - [ ]* 12.16 Implementar Property 15: Transient Error Recovery
    - **Property 15: Transient Error Recovery**
    - **Validates: Requirements 7.7**
    - Verificar retry logic para errores transitorios
  
  - [ ]* 12.17 Implementar Property 16: Indexing Idempotence
    - **Property 16: Indexing Idempotence**
    - **Validates: Requirements 8.2**
    - Verificar que indexar dos veces no duplique chunks
  
  - [ ]* 12.18 Implementar Property 17: Processing Order Confluence
    - **Property 17: Processing Order Confluence**
    - **Validates: Requirements 8.3**
    - Verificar que orden de procesamiento no afecte contenido final
  
  - [ ]* 12.19 Implementar Property 18: Conversation Memory Growth
    - **Property 18: Conversation Memory Growth**
    - **Validates: Requirements 8.5**
    - Verificar crecimiento lineal de memoria con mensajes
  
  - [ ]* 12.20 Implementar Property 19: Session Isolation
    - **Property 19: Session Isolation**
    - **Validates: Requirements 8.6**
    - Verificar aislamiento entre sesiones diferentes
  
  - [ ]* 12.21 Implementar Property 20: Storage Growth Proportionality
    - **Property 20: Storage Growth Proportionality**
    - **Validates: Requirements 9.5**
    - Verificar crecimiento proporcional de ChromaDB con documentos

- [ ] 13. Implementar pruebas de integración end-to-end
  - [ ] 13.1 Escribir prueba de flujo completo de ingesta a consulta
    - Implementar `test_full_ingestion_to_query_workflow` en `test_integration.py`
    - Verificar flujo: ingesta → indexación → consulta → respuesta
    - _Requirements: 10.5_
  
  - [ ] 13.2 Escribir prueba de flujo API completo
    - Implementar `test_api_upload_and_query_workflow`
    - Verificar flujo: upload via API → query via API
    - _Requirements: 10.5_
  
  - [ ] 13.3 Escribir pruebas de aislamiento y recuperación
    - Implementar `test_multi_session_isolation`
    - Implementar `test_error_recovery_workflow`
    - _Requirements: 10.5_

- [ ] 14. Implementar pruebas del dashboard Streamlit y de la app LM Studio
  - [ ] 14.1 Escribir pruebas de componentes del dashboard legado
    - Implementar pruebas básicas en `test_dashboard.py` (si `app_dashboard.py` se mantiene)
    - Verificar renderizado de componentes
    - Verificar interacción con session state
    - _Requirements: 10.2_
  - [ ] 14.2 Pruebas de `app_lmstudio.py` (prioridad)
    - Crear `test_app_lmstudio.py`: pruebas de import, funciones puras (`_historial_para_prompt`, `_nombre_archivo_seguro`), y flujo `indexar_carpeta_en_sistema` / `procesar_y_indexar` con `tmp_path` y Chroma temporal
    - Mockear `ejecutar_modo` para validar que el chat pasa `historial_conversacion` cuando hay mensajes previos
    - _Requirements: 11, 12, 10.2_
  - [ ] 14.3 Pruebas de `office_docs.py`
    - Crear `test_office_docs.py`: `listar_archivos_documento`, `cargar_un_archivo` (PDF/TXT en fixtures), `vectorizar_y_persistir` con `reemplazar_indice` True/False
    - _Requirements: 1 (extensiones 9–11), 11_
  - [ ] 14.4 Pruebas de `rag_modes_lm.py` y `prompts_notebooklm.py`
    - Crear `test_rag_modes_lm.py`: modo chat sin/s con historial, plantillas con variables correctas, `_extraer_json_cuestionario` con JSON válido y con texto envolvente
    - _Requirements: 12, 13_

- [ ] 15. Implementar utilidades de testing
  - [ ] 15.1 Crear aserciones personalizadas
    - Implementar funciones de aserción en `utils/assertions.py`
    - Crear helpers para verificar formatos de respuesta
    - Crear helpers para verificar metadata de chunks
    - _Requirements: 10.6_
  
  - [ ] 15.2 Crear funciones auxiliares de prueba
    - Implementar helpers en `utils/helpers.py`
    - Crear funciones para setup de datos de prueba
    - Crear funciones para limpieza de recursos
    - _Requirements: 10.9_

- [ ] 16. Checkpoint - Verificar todas las pruebas
  - Ejecutar `pytest tests/ --cov --cov-report=html --cov-report=term-missing`
  - Verificar que cobertura sea >= 80%
  - Revisar reporte HTML de coverage para identificar gaps
  - Preguntar al usuario si hay ajustes necesarios

- [ ] 17. Configurar CI/CD con GitHub Actions
  - [ ] 17.1 Crear workflow de GitHub Actions
    - Crear archivo `.github/workflows/test.yml`
    - Configurar jobs para unit tests, integration tests, y property tests
    - Configurar upload de coverage a Codecov
    - Configurar verificación de threshold de coverage (80%)
    - _Requirements: 10.10_

- [ ] 18. Crear documentación de pruebas
  - [ ] 18.1 Escribir README de testing
    - Crear `tests/README.md` con instrucciones de ejecución
    - Documentar cómo ejecutar diferentes tipos de pruebas
    - Documentar cómo interpretar reportes de coverage
    - Documentar estructura de fixtures y mocks
    - Documentar estrategias de property-based testing
    - _Requirements: 10.7, 10.8_

- [ ] 19. Checkpoint final - Validación completa
  - Ejecutar suite completa de pruebas: `pytest tests/`
  - Verificar que todas las pruebas pasen
  - Verificar cobertura >= 80%
  - Revisar reportes de ejecución y coverage
  - Validar que CI/CD funcione correctamente
  - Preguntar al usuario si el sistema de pruebas cumple con las expectativas

## Notes

- Las tareas marcadas con `*` son opcionales (property-based tests) y pueden omitirse para un MVP más rápido
- Cada tarea referencia requisitos específicos para trazabilidad
- Los checkpoints aseguran validación incremental del progreso
- Property tests validan propiedades universales de correctness con 100 ejemplos cada uno
- Unit tests validan casos específicos y ejemplos concretos
- El objetivo de 80% de cobertura se verifica en múltiples checkpoints
- La estructura modular facilita el mantenimiento y extensión futura del sistema de pruebas
- **Prioridad de cobertura:** `app_lmstudio.py`, `office_docs.py`, `rag_modes_lm.py` y `rag_chain_lm.py` reflejan el comportamiento actual del producto (Streamlit multimodo + carpeta de oficina + memoria); el dashboard `app_dashboard.py` es secundario si queda obsoleto
