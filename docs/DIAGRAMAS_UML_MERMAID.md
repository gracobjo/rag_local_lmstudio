# Diagramas UML (Mermaid) — RAG local con LM Studio

Este documento recoge vistas **componentes**, **despliegue**, **secuencia**, **clases** y **estados** del sistema descrito en el código (`app_lmstudio.py`, `office_docs.py`, `rag_chain_lm.py`, `rag_modes_lm.py`, `prompts_notebooklm.py`).

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

    subgraph Lógica_RAG
        RC[rag_chain_lm.py]
        RM[rag_modes_lm.py]
        PR[prompts_notebooklm.py]
        OD[office_docs.py]
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
    APP --> OD
    APP --> RM
    RM --> RC
    RM --> PR
    RC --> CH
    RC --> ST
    RC --> LM
    RM --> CH
    RM --> ST
    RM --> LM
    OD --> CH
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
    Cuestionario --> ConIndice: Generar test JSON
    Guia --> ConIndice: Generar guía

    ConIndice --> SinIndice: Borrar índice
```

---

## 7. Diagrama de casos de uso (resumen)

```mermaid
flowchart LR
    subgraph Actores
        U1[Usuario / Oficina]
        U2[Administrador]
    end

    subgraph Uso
        UC1[Consultar documentos\nchat RAG]
        UC2[Indexar carpeta\nfuente única]
        UC3[Subir archivos\na docs/]
        UC4[Generar resumen]
        UC5[Generar cuestionario]
        UC6[Generar guía de estudio]
        UC7[Elegir modelo LM Studio]
    end

    U1 --> UC1
    U1 --> UC3
    U1 --> UC4
    U1 --> UC5
    U1 --> UC6
    U1 --> UC7
    U2 --> UC2
```

---

## Notas

- Los diagramas reflejan el diseño **actual** del código en este repositorio; si cambian los módulos, conviene actualizar este documento.
- Mermaid admite pequeñas variaciones según el visor (GitHub, GitLab, VS Code, etc.); si un diagrama no renderiza, comprueba la [sintaxis Mermaid](https://mermaid.js.org/).
