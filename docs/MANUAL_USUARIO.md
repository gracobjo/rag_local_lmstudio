# Manual de usuario — RAG local con LM Studio

Aplicación web (**Streamlit**) que permite consultar documentación propia mediante **RAG** (recuperación aumentada por generación): los textos se fragmentan, se vectorizan en local y un modelo de lenguaje alojado en **LM Studio** responde **solo** con base en los fragmentos recuperados.

**Documentación relacionada**

- **Presentación e instalación rápida:** [README.md](../README.md) en la raíz del repositorio.
- **Casos de uso (actores y flujos):** [CASOS_DE_USO.md](./CASOS_DE_USO.md).
- **Requisitos funcionales (tabla RF):** [.kiro/specs/rag-testing-system/requirements.md](../.kiro/specs/rag-testing-system/requirements.md) (sección *Documentación de requisitos funcionales del producto*).
- Diagramas técnicos (componentes, despliegue, secuencias): [DIAGRAMAS_UML_MERMAID.md](./DIAGRAMAS_UML_MERMAID.md).
- Instalación del entorno, LM Studio, API y arranque para desarrollo: [MANUAL_DESARROLLO.md](./MANUAL_DESARROLLO.md) (incluye **estructura del repo**, módulos `.py`, y **reindexación** desde cron / carpeta sincronizada con `reindex.py`).
- Índice de la carpeta `docs/`: [docs/README.md](./README.md).

---

## 1. Qué puede hacer la aplicación

| Función | Descripción breve |
|--------|-------------------|
| **Indexar documentos** | Lee PDF, TXT, Markdown y DOCX desde carpetas o subidas, los trocea y guarda embeddings en **ChromaDB** (`./chroma_db`). |
| **Chat** | Preguntas en lenguaje natural con **memoria conversacional** (el modelo usa el historial para entender seguimientos; los **hechos** salen solo de los documentos recuperados). |
| **Resumen** | Informe corto estructurado (ejecutivo, ideas clave, términos) según un enfoque opcional. |
| **Cuestionario** | Test de varias preguntas con 4 opciones y explicación de la correcta (salida pensada en JSON). |
| **Guía de estudio** | Mapa del tema, autoevaluación, posibles confusiones y qué repasar. |
| **Filtrar por documentos** | Lista multiselección de **ficheros ya indexados** para limitar chat, resumen, cuestionario y guía a uno o varios archivos (o ninguno seleccionado = todo el índice). |

**Qué no hace:** no sustituye a internet ni a bases de datos externas; si algo no está en los documentos indexados (o en los fragmentos recuperados), el sistema debe indicar que no hay información suficiente.

---

## 2. Requisitos previos

1. **Python 3** con dependencias del proyecto (`requirements.txt`).
2. **LM Studio** ejecutándose con la API compatible con OpenAI (por defecto `http://localhost:1234/v1`). Comprueba en LM Studio que el servidor local esté activo y que exista al menos un modelo de chat cargado.
3. Espacio en disco para el índice (`./chroma_db`) y, la primera vez, la descarga del modelo de embeddings **sentence-transformers/all-MiniLM-L6-v2** (uso local, sin enviar tus documentos a servicios externos para vectorizar).

Variables de entorno útiles (opcionales):

- `LM_STUDIO_BASE_URL`: URL base de la API (por defecto `http://localhost:1234/v1`).
- `LM_STUDIO_MODEL`: identificador del modelo por defecto si no eliges otro en la interfaz.

---

## 3. Puesta en marcha

Desde la raíz del proyecto:

```bash
./run_streamlit_lmstudio.sh
```

El script activa `venv` si existe y lanza Streamlit sobre `app_lmstudio.py`. Abre el navegador en la URL que indique la consola (habitualmente `http://localhost:8501`).

---

## 4. Diseño general (cómo está montada)

En términos sencillos:

1. **Documentos** → se cargan con `office_docs.py`, se dividen en fragmentos y se convierten en vectores con **Hugging Face embeddings** locales.
2. **Almacenamiento** → **Chroma** persiste el índice en `./chroma_db`.
3. **Consulta** → según tu pregunta o el modo (resumen, test, guía), se construye una **consulta de recuperación** y se buscan los fragmentos más similares (el número de fragmentos depende del modo; el resumen y el cuestionario recuperan más trozos que el chat).
4. **Generación** → esos fragmentos se envían al modelo en **LM Studio** junto con un **prompt** distinto por modo (`prompts_notebooklm.py`). El modelo debe ceñirse al contexto recibido.
5. **Filtro por archivos** → si eliges uno o varios documentos en **Documentos a usar**, solo se consideran fragmentos cuya ruta de origen coincida con tu selección (rutas normalizadas en disco).

La memoria del **chat** es un texto con los turnos anteriores para interpretar la pregunta actual; **no** reemplaza a los documentos como fuente de verdad.

---

## 5. Panel izquierdo (barra lateral)

### 5.1 Modelo LLM

- **Modelo:** lista de identificadores conocidos (puedes añadir o cambiar modelos en LM Studio; los ids deben coincidir con `GET /v1/models`).
- **Otro id:** si rellenas este campo, **sustituye** al modelo elegido en la lista (útil para probar modelos nuevos sin tocar el código).

### 5.2 Documentación (fuente de verdad)

- **Formatos admitidos:** PDF, TXT, MD/Markdown, DOCX (para DOCX hace falta la dependencia `docx2txt` si no está ya instalada).
- **Indexar carpeta `docs/` del proyecto:** lee la carpeta `./docs` del proyecto y **reemplaza** el índice vectorial completo por el contenido de esa carpeta. Opción **Incluir subcarpetas** para recorrer o no subdirectorios.
- **Indexar carpeta indicada:** misma lógica pero con una **ruta absoluta** que escribas; también **reemplaza** el índice.
- **Subir archivos:** los ficheros se guardan en `./docs` y al pulsar **Indexar archivos subidos** se **añaden** fragmentos al índice existente (no borran el índice previo salvo que uses las opciones de carpeta que reemplazan).
- **Borrar índice:** elimina `./chroma_db` y la selección de documentos del contexto RAG.

Tras una indexación correcta verás un mensaje de confirmación y la interfaz se actualizará para listar las nuevas fuentes.

### 5.3 Contexto RAG — Documentos a usar

- Aparece cuando existe un índice y el sistema puede listar rutas únicas (`source`) en Chroma.
- **Nada seleccionado:** se usa **todo** el corpus indexado.
- **Uno o varios archivos:** chat, resumen, cuestionario y guía solo usarán fragmentos de esos ficheros. Si la consulta no encuentra fragmentos útiles en esa selección, puede mostrarse un mensaje de error indicando que pruebes sin filtro, reindexar u otros archivos.

### 5.4 Borrar historial del chat

Vacía la conversación de la pestaña Chat (no borra el índice ni los documentos en disco).

---

## 6. Pestañas principales

### 6.1 Chat

- Escribe en el campo inferior; cada respuesta puede mostrar un desplegable **Fuentes recuperadas** con las rutas de los documentos de los que salieron los fragmentos.
- El modelo recibe varios fragmentos (configuración interna: más que un simple “k=4” genérico en la cadena clásica; el modo chat usa un número intermedio frente a resumen/cuestionario).

### 6.2 Resumen

- Opcional: **Enfoque** (por ejemplo, “solo la parte legal” o “resumen para directivos”).
- Pulsa **Generar resumen**; el texto suele venir en Markdown con secciones tipo resumen ejecutivo, ideas clave y limitaciones.
- El **último resumen** se conserva al cambiar de pestaña; usa **Guardar** (descarga `.md`) e **Imprimir** (vista previa con botón de impresión del bloque).

### 6.3 Cuestionario

- Indica **número de preguntas** (entre 3 y 20) y, si quieres, un **tema o área** para orientar las preguntas.
- El límite de documentos se controla con **Documentos a usar** en el panel izquierdo (no hay filtro por texto del nombre).
- Con JSON válido, cada pregunta se muestra **sin solución**: pulsas **A–D**, **Comprobar respuesta**, y aparece ✓ si acertaste o ✗ en tu elección y la **correcta resaltada**; debajo, **explicación**, **fragmento** citado (si el modelo lo rellena), **dónde buscar** en el texto y la **ruta del archivo** con enlace `file://` (a veces bloqueado por el navegador).
- Puedes abrir **JSON crudo** para exportar. Si el JSON falla, se muestra el texto del modelo; prueba otra vez o baja temperatura.
- El **último cuestionario** se mantiene al cambiar de pestaña. **Guardar** descarga el texto; si hubo JSON válido, **Guardar JSON** descarga el objeto parseado. **Imprimir** usa el bloque de vista previa.

### 6.4 Guía de estudio

- Opcional: **Ángulo** (por ejemplo, preparar un examen tipo test).
- La salida es una guía en Markdown: mapa del tema, preguntas de autoevaluación, confusiones posibles y qué repasar.
- La **última guía** generada permanece al cambiar de pestaña, con **Guardar** e **Imprimir** como en resumen.

---

## 7. Flujos de trabajo recomendados

1. **Primera vez:** coloca manuales en `docs/` o súbelos desde la interfaz → indexa → comprueba en **Documentos a usar** que aparecen los archivos esperados.
2. **Varios manuales:** si necesitas aislar un PDF para un examen, selecciónalo solo en el multiselect y genera el cuestionario o la guía.
3. **Cambio total de corpus:** usa **Indexar carpeta `docs/`** o **Indexar carpeta indicada** para reemplazar el índice; o **Borrar índice** y vuelve a cargar.
4. **Modelo que no obedece al JSON:** revisa en LM Studio temperatura baja y un modelo instruct adecuado; el cuestionario pide salida JSON estricta.

---

## 8. Limitaciones y mensajes frecuentes

- **“Indexa documentos primero”** o advertencias similares: no existe `./chroma_db` o está vacío; indexa al menos un documento.
- **Sin fragmentos en documentos seleccionados:** la consulta semántica no encontró trozos de tus archivos elegidos; prueba ampliar la selección, quitar el filtro o reformular el tema opcional.
- **DOCX no carga:** instala `docx2txt` (`pip install docx2txt`) según el mensaje de error.
- **LM Studio no responde:** comprueba que el puerto (por defecto **1234**) y la URL coincidan con `LM_STUDIO_BASE_URL`.
- **«Failed to load model» / error 400 en `model`:** el **id** del modelo en el panel no coincide con un modelo **instalado y cargado** en LM Studio. Descarga el modelo en LM Studio, cárgalo en Chat y elige en la app el mismo id que devuelve `GET /v1/models` (o escríbelo en **Otro id**). El valor por defecto `meta-llama-3.1-8b-instruct` solo funciona si ese modelo está disponible.

---

## 9. Archivos y carpetas relevantes

| Ruta | Rol |
|------|-----|
| `app_lmstudio.py` | Interfaz Streamlit y orquestación de modos. |
| `office_docs.py` | Carga de archivos, troceado y escritura en Chroma. |
| `rag_modes_lm.py` | Recuperación por modo, filtro por fuentes, llamada al LLM. |
| `prompts_notebooklm.py` | Prompts y parámetros (temperatura, cantidad de fragmentos) por modo. |
| `chroma_lm.py` | Cliente Chroma persistente y embeddings compartidos con LangChain. |
| `rag_chain_lm.py` | Configuración por defecto de URL/modelo LM Studio y cadena RAG clásica (referencia). |
| `./docs/` | Carpeta de trabajo para copias de documentos subidos y manuales del proyecto. |
| `./chroma_db/` | Índice vectorial persistente (puede borrarse con el botón correspondiente). |

---

*Última revisión alineada con el comportamiento descrito en el código de la aplicación (Streamlit + Chroma + LM Studio).*
