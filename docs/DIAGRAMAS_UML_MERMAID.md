# Diagramas UML (Mermaid) — RAG local con LM Studio

Este documento recoge vistas **componentes**, **despliegue**, **secuencia**, **clases** y **estados** del sistema descrito en el código (`app_lmstudio.py`, `office_docs.py`, `chroma_lm.py`, `rag_chain_lm.py`, `rag_modes_lm.py`, `prompts_notebooklm.py`, `reindex.py`). Incluye el flujo de **cuestionario interactivo** (JSON → opciones A–D → comprobación) y el **filtrado por documentos** en el sidebar.

Para **uso de la aplicación**, véase el [manual de usuario](./MANUAL_USUARIO.md). Para **configuración del entorno**, LM Studio, servidor y arranque de Streamlit, el [manual de desarrollo](./MANUAL_DESARROLLO.md). Para **casos de uso textuales** (CU-01–CU-12), [CASOS_DE_USO.md](./CASOS_DE_USO.md). Para **presentación del proyecto**, [README.md](../README.md). **Requisitos funcionales (RF-01–RF-14):** [.kiro/specs/rag-testing-system/requirements.md](../.kiro/specs/rag-testing-system/requirements.md).

---

## 1. Diagrama de componentes

```mermaid
flowchart TB
    subgraph Cliente
        U[Usuario]
    end

    subgraph Aplicación_Streamlit
        APP[app_lmstudio.py]
    end

    subgraph CLI_reindex
        RI[reindex.py]
    end

    subgraph Lógica_RAG
        RC[rag_chain_lm.py]
        RM[rag_modes_lm.py]
        PR[prompts_notebooklm.py]
        OD[office_docs.py]
        CL[chroma_lm.py]
    end

    subgraph Persistencia_local
        CH[(ChromaDB\n./chroma_db)]
        DOCS[(/docs/\nmanuales)]
    end

    subgraph Embeddings
        ST[sentence-transformers\nall-MiniLM-L6-v2]
    end

    subgraph Servicio_LLM
        LM[LM Studio\nAPI OpenAI-compatible\n:1234]
    end

    U --> APP
    U -.->|opcional cron| RI
    APP --> OD
    RI --> OD
    APP --> RM
    RM --> RC
    RM --> PR
    RC --> CH
    RC --> ST
    RC --> LM
    RM --> CH
    RM --> ST
    RM --> LM
    OD --> CL
    CL --> CH
    OD --> ST
    APP --> DOCS
```

---

## 2. Diagrama de despliegue (lógico)

```mermaid
flowchart LR
    subgraph Máquina_local
        subgraph Proceso_Python
            ST_APP[Streamlit]
            LC[LangChain]
            EM[Embeddings CPU/GPU]
        end
        FS[(Sistema de archivos:\ndocs/, chroma_db/)]
        ST_APP --> FS
        LC --> FS
    end

    subgraph Proceso_LMStudio
        API[Servidor local\nLM Studio]
    end

    EM -->|HTTP localhost:1234| API
    ST_APP --> LC
```

---

## 2b. Ingesta programada (nube → disco → reindex)

Flujo opcional cuando la **fuente de verdad** vive en la nube y se sincroniza a una carpeta local antes de vectorizar (sin LM Studio en la ingesta).

```mermaid
flowchart LR
    subgraph Nube
        CLD[Drive / S3 / etc.]
    end

    subgraph Sincronización
        RC[rclone o cliente\nde sync]
    end

    subgraph Máquina_local
        DOCS2[/docs o carpeta\nde mirror local/]
        RIX[reindex.py]
        CH2[(chroma_db)]
        EM2[Embeddings locales]
    end

    CLD --> RC
    RC --> DOCS2
    DOCS2 --> RIX
    RIX --> EM2
    EM2 --> CH2
```

---

## 3. Diagrama de secuencia — Chat con memoria (RAG)

```mermaid
sequenceDiagram
    actor Usuario
    participant ST as app_lmstudio
    participant RM as rag_modes_lm
    participant CH as ChromaDB
    participant E as Embeddings
    participant LM as LM Studio

    Usuario->>ST: Mensaje en chat
    ST->>ST: Construir historial (turnos previos)
    ST->>RM: ejecutar_modo(CHAT, instrucción, historial)
    RM->>CH: get_relevant_documents(query híbrida)
    CH->>E: embeddings de la consulta
    E-->>CH: vectores
    CH-->>RM: fragmentos + metadata
    RM->>RM: Prompt PROMPT_CHAT_MEMORIA (si hay historial)
    RM->>LM: POST /v1/chat/completions
    LM-->>RM: texto generado
    RM-->>ST: texto + fuentes
    ST-->>Usuario: Respuesta + expander fuentes
```

---

## 3b. Diagrama de secuencia — Cuestionario (RAG + JSON + UI interactiva)

Tras generar el JSON, la app **parsea** preguntas y muestra **radio A–D** y **Comprobar**; el contexto enviado al modelo en modo cuestionario incluye **ruta de archivo por fragmento** para trazabilidad (`fuente_archivo`, `numero_fragmento`, etc.).

```mermaid
sequenceDiagram
    actor Usuario
    participant ST as app_lmstudio
    participant RM as rag_modes_lm
    participant CH as ChromaDB
    participant LM as LM Studio

    Usuario->>ST: Pestaña Cuestionario + tema (y fuentes en multiselect)
    ST->>RM: ejecutar_modo(CUESTIONARIO, instrucción, model_id)
    RM->>CH: recuperación con filtro por fuentes si aplica
    CH-->>RM: fragmentos + metadata (ruta origen)
    RM->>RM: Construir contexto con (archivo: ruta) por fragmento
    RM->>LM: POST /v1/chat/completions (JSON según prompts_notebooklm)
    LM-->>RM: texto JSON
    RM-->>ST: texto + fuentes
    ST->>ST: parse JSON → lista de preguntas
    loop Por cada pregunta
        Usuario->>ST: Elige A–D y pulsa Comprobar
        ST-->>Usuario: ✓/✗, opción correcta, explicación, enlace a fuente/fragmento
    end
```

---

## 4. Diagrama de secuencia — Indexar carpeta de oficina (fuente única)

```mermaid
sequenceDiagram
    actor Usuario
    participant ST as app_lmstudio
    participant OD as office_docs
    participant FS as Sistema de archivos
    participant CH as ChromaDB

    Usuario->>ST: Indexar docs/ o ruta absoluta
    ST->>OD: cargar_carpeta(ruta, recursivo)
    OD->>FS: Leer PDF/TXT/MD/DOCX
    FS-->>OD: Documentos LangChain
    OD->>OD: vectorizar_y_persistir(reemplazar=True)
    OD->>CH: Borrar índice previo si existe
    OD->>CH: Chroma.from_documents(chunks)
    CH-->>ST: N fragmentos
    ST-->>Usuario: Confirmación
```

---

## 5. Diagrama de clases (módulos y responsabilidades)

```mermaid
classDiagram
    class app_lmstudio {
        +procesar_y_indexar(uploaded_files)
        +indexar_carpeta_en_sistema(ruta, recursivo, reemplazar)
        +_historial_para_prompt(messages)
        +_render_cuestionario_interactivo(...)
        +_render_guardar_imprimir(...)
        +multiselect fuentes indexadas
    }

    class office_docs {
        +cargar_un_archivo(ruta)
        +cargar_carpeta(carpeta, recursivo)
        +listar_archivos_documento(carpeta, recursivo)
        +vectorizar_y_persistir(docs, persist) int
    }

    class rag_chain_lm {
        +crear_cadena_rag(model_id) RetrievalQA
        LM_STUDIO_URL
        LM_STUDIO_MODEL
        MODELOS_CHAT_LM_STUDIO
    }

    class rag_modes_lm {
        +ejecutar_modo(modo, instruccion, model_id, historial)
        +_consulta_retrieval_chat()
        +contexto cuestionario con ruta por fragmento
    }

    class prompts_notebooklm {
        <<enumeration>>
        ModoContenido
        +consulta_recuperacion()
        +configuracion_modo()
    }

    app_lmstudio --> office_docs : indexa
    app_lmstudio --> rag_modes_lm : chat / modos UI
    rag_modes_lm --> rag_chain_lm : usa DB_PATH / patrón similar
    rag_modes_lm --> prompts_notebooklm : plantillas
    office_docs --> rag_chain_lm : mismo DB_PATH / embeddings
```

---

## 6. Diagrama de estados — Modos de contenido en la UI

```mermaid
stateDiagram-v2
    [*] --> SinIndice: Arranque sin chroma_db

    SinIndice --> ConIndice: Indexar carpeta o subir archivos
    ConIndice --> Chat: Pestaña Chat
    ConIndice --> Resumen: Pestaña Resumen
    ConIndice --> Cuestionario: Pestaña Cuestionario
    ConIndice --> Guia: Pestaña Guía

    Chat --> Chat: Nuevo mensaje (memoria opcional)
    Resumen --> ConIndice: Generar resumen
    Cuestionario --> PreguntaActiva: Generar test JSON
    PreguntaActiva --> PreguntaActiva: Elegir A–D y Comprobar
    PreguntaActiva --> ConIndice: Otra pregunta / nuevo tema
    Guia --> ConIndice: Generar guía

    ConIndice --> SinIndice: Borrar índice
```

---

## 7. Diagrama de casos de uso (resumen)

Vista alineada con [CASOS_DE_USO.md](./CASOS_DE_USO.md) (identificadores **CU-xx**).

```mermaid
flowchart TB
    subgraph Actores
        U[Usuario]
        ADM[Administrador / operador]
    end

    subgraph Consulta_y_generación
        UC1[CU-01 Chat RAG\ncon memoria]
        UC4[CU-04 Filtrar por\ndocumentos]
        UC5[CU-05 Resumen]
        UC6[CU-06 Cuestionario\ninteractivo]
        UC7[CU-07 Guía de estudio]
        UC8[CU-08 Elegir modelo /\nerrores LM Studio]
        UC9[CU-09 Panel LM Studio\nopcional]
        UC10[CU-10 Guardar /\nimprimir]
    end

    subgraph Indexación
        UC2[CU-02 Indexar carpeta]
        UC3[CU-03 Subir y fusionar]
        UC11a[CU-11 Borrar índice /\nhistorial]
    end

    subgraph Automatización
        UC12[CU-12 reindex.py\ncron / post-sync]
    end

    U --> UC1
    U --> UC4
    U --> UC5
    U --> UC6
    U --> UC7
    U --> UC8
    U --> UC9
    U --> UC10
    U --> UC3
    U --> UC11a
    ADM --> UC2
    ADM --> UC12
    UC4 -.->|restringe contexto| UC1
    UC4 -.->|restringe contexto| UC5
    UC4 -.->|restringe contexto| UC6
    UC4 -.->|restringe contexto| UC7
```

---

## 8. Matriz RF ↔ vista de casos de uso

Referencia cruzada entre la tabla **RF-01–RF-14** en [requirements.md](../.kiro/specs/rag-testing-system/requirements.md) y los **CU-xx** (mismo significado que en [CASOS_DE_USO.md](./CASOS_DE_USO.md)).

| RF | Tema | Casos de uso relacionados |
|----|------|---------------------------|
| RF-01 | Ingesta multi-formato | CU-02, CU-03 |
| RF-02 | Carpeta / fusión | CU-02, CU-03 |
| RF-03 | Chat RAG | CU-01 |
| RF-04 | Filtro documentos | CU-04 |
| RF-05 | Resumen | CU-05, CU-10 |
| RF-06 / RF-08 | Cuestionario + contexto con rutas | CU-06, CU-10 |
| RF-07 | Guía | CU-07, CU-10 |
| RF-09 | Contrato LM Studio | CU-08 |
| RF-10 | Panel LM Studio | CU-09 |
| RF-11 / RF-12 | CLI reindex / nube→disco | CU-12 |
| RF-13 | Chroma estable | CU-02, CU-03, CU-12 (implícito) |
| RF-14 | Sesión / borrado | CU-11 |

---

## Notas

- Los diagramas reflejan el diseño **actual** del código en este repositorio; si cambian los módulos, conviene actualizar este documento.
- Mermaid admite pequeñas variaciones según el visor (GitHub, GitLab, VS Code, etc.); si un diagrama no renderiza, comprueba la [sintaxis Mermaid](https://mermaid.js.org/).
