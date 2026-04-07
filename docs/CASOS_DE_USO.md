# Casos de uso — RAG local con LM Studio

Este documento describe los casos de uso principales de la aplicación **`app_lmstudio.py`** y procesos relacionados (**`reindex.py`**). Complementa el [diagrama de casos de uso (Mermaid)](./DIAGRAMAS_UML_MERMAID.md#7-diagrama-de-casos-de-uso-resumen) y los [requisitos funcionales](../.kiro/specs/rag-testing-system/requirements.md#documentación-de-requisitos-funcionales-del-producto).

---

## Actores

| Actor | Descripción |
|-------|-------------|
| **Usuario** | Persona que consulta documentación vía chat, resúmenes, cuestionarios o guías. |
| **Administrador / operador** | Quien indexa carpetas completas, borra el índice o programa `reindex.py` tras sincronizar archivos. |
| **Sistema externo (opcional)** | Cron, `rclone` u otro job que deja ficheros en disco antes de reindexar. |

---

## Resumen de casos de uso

| ID | Nombre | Actor principal |
|----|--------|-----------------|
| CU-01 | Consultar documentos (chat RAG con memoria) | Usuario |
| CU-02 | Indexar carpeta `docs/` o ruta absoluta (reemplazo de índice) | Administrador |
| CU-03 | Subir archivos e indexar con fusión al índice existente | Usuario |
| CU-04 | Filtrar por documentos indexados (multiselect) | Usuario |
| CU-05 | Generar resumen temático | Usuario |
| CU-06 | Generar cuestionario interactivo y comprobar respuestas | Usuario |
| CU-07 | Generar guía de estudio | Usuario |
| CU-08 | Elegir modelo LM Studio y manejar errores de carga | Usuario |
| CU-09 | Usar panel LM Studio (abrir app, embed opcional) | Usuario |
| CU-10 | Guardar o imprimir salidas (resumen, cuestionario, guía) | Usuario |
| CU-11 | Borrar índice vectorial o historial de chat | Usuario / Administrador |
| CU-12 | Reindexar desde CLI tras sincronización (`reindex.py`) | Administrador / Sistema |

---

## CU-01: Consultar documentos (chat RAG)

- **Objetivo:** Obtener respuestas fundamentadas en fragmentos recuperados del índice.
- **Precondiciones:** Índice existente (`./chroma_db`); LM Studio sirviendo el modelo; modelo cargado en LM Studio.
- **Flujo principal:**
  1. El usuario abre la pestaña **Chat**.
  2. Opcionalmente restringe fuentes con **Documentos a usar** (CU-04).
  3. Escribe un mensaje; el sistema recupera fragmentos, construye el prompt con memoria de turnos previos y llama a LM Studio.
  4. El usuario revisa la respuesta y el desplegable **Fuentes recuperadas**.
- **Postcondiciones:** La conversación se amplía en el historial de la sesión.
- **Extensiones:** Sin índice o sin fragmentos relevantes → mensaje informativo; LM Studio no disponible o modelo no cargado → mensaje amigable (véase CU-08).

---

## CU-02: Indexar carpeta (fuente única)

- **Objetivo:** Reconstruir el índice vectorial a partir de una carpeta (proyecto `./docs` o ruta absoluta).
- **Precondiciones:** Ficheros admitidos (PDF, TXT, MD, DOCX) en la ruta elegida.
- **Flujo principal:**
  1. El administrador indica carpeta y si incluye subcarpetas.
  2. Pulsa el botón de indexación correspondiente.
  3. El sistema carga documentos, trocea, genera embeddings y persiste en Chroma (reemplazo del índice según la lógica de `office_docs`).
- **Postcondiciones:** Nuevo índice coherente con el contenido de la carpeta; lista de fuentes actualizada para el multiselect.

---

## CU-03: Subir archivos e indexar con fusión

- **Objetivo:** Añadir documentos al workspace `./docs` y fusionar nuevos fragmentos sin borrar el resto del índice (salvo que se use CU-02 sobre todo el corpus).
- **Precondiciones:** Ficheros válidos; espacio en disco.
- **Flujo principal:**
  1. El usuario sube uno o más archivos.
  2. Pulsa **Indexar archivos subidos** (o equivalente en la UI).
  3. Los archivos se guardan bajo `./docs` y se vectorizan con fusión incremental.
- **Postcondiciones:** Índice ampliado; nuevas rutas aparecen en **Documentos a usar**.

---

## CU-04: Filtrar por documentos indexados

- **Objetivo:** Limitar chat, resumen, cuestionario y guía a uno o varios ficheros cuyas rutas están en metadata `source` de Chroma.
- **Precondiciones:** Índice no vacío; multiselect poblado.
- **Flujo principal:**
  1. El usuario selecciona uno o más archivos en **Documentos a usar**, o deja vacío para usar todo el corpus.
  2. Ejecuta un modo (CU-01, CU-05, CU-06 o CU-07).
- **Postcondiciones:** La recuperación solo considera chunks cuyo `source` normalizado coincide con la selección; si no hay coincidencias semánticas, puede mostrarse un mensaje de error de filtro.

---

## CU-05: Generar resumen

- **Objetivo:** Obtener un resumen estructurado según tema/enfoque opcional.
- **Precondiciones:** Como mínimo CU-04 aplicable o corpus completo; índice listo.
- **Flujo principal:** Pestaña **Resumen** → opcionalmente enfoque → **Generar resumen** → revisar Markdown → **Guardar** / **Imprimir**.
- **Postcondiciones:** Último resumen persistido en la sesión hasta regenerar o reiniciar.

---

## CU-06: Generar cuestionario interactivo

- **Objetivo:** Crear preguntas tipo test a partir del contexto RAG y permitir comprobar respuestas con feedback y trazabilidad.
- **Precondiciones:** Índice y modelo operativos; número de preguntas y tema opcional indicados.
- **Flujo principal:**
  1. Pestaña **Cuestionario** → parámetros → generación.
  2. El backend recupera fragmentos (con rutas por fragmento en contexto para modo cuestionario), el modelo devuelve JSON.
  3. La UI parsea el JSON y muestra cada pregunta con opciones A–D y **Comprobar**.
  4. El usuario revisa explicación, referencia a fragmento y enlace a archivo si aplica.
- **Extensiones:** JSON inválido → vista de texto crudo; reintentar o ajustar modelo/temperatura.
- **Postcondiciones:** Posibilidad de **Guardar** / **Guardar JSON** / **Imprimir**.

---

## CU-07: Generar guía de estudio

- **Objetivo:** Obtener una guía en Markdown (mapa del tema, autoevaluación, confusiones, repaso).
- **Flujo principal:** Pestaña **Guía de estudio** → ángulo opcional → generar → **Guardar** / **Imprimir**.
- **Postcondiciones:** Similar a CU-05 respecto a persistencia en sesión.

---

## CU-08: Elegir modelo y gestionar errores LM Studio

- **Objetivo:** Usar el `id` correcto según `GET /v1/models` y entender fallos (modelo no cargado, URL incorrecta).
- **Flujo principal:** Selector en barra lateral o campo **Otro id** con prioridad sobre la lista fija.
- **Reglas de negocio:** El `id` debe coincidir con un modelo disponible y cargado en LM Studio para inferencia.

---

## CU-09: Panel LM Studio (opcional)

- **Objetivo:** Abrir la aplicación de escritorio LM Studio o mostrar una URL embebida si está configurada.
- **Precondiciones:** `LM_STUDIO_EXECUTABLE` y/o `LM_STUDIO_EMBED_URL` según la función deseada.
- **Nota:** La API en `:1234` no sustituye la UI completa de gestión de modelos; el embed es opcional y depende de la URL (iframes, CSP del navegador).

---

## CU-10: Guardar e imprimir salidas

- **Objetivo:** Exportar o imprimir resumen, cuestionario o guía generados.
- **Flujo principal:** Tras generar contenido válido, usar **Guardar** (descarga) o **Imprimir** (vista previa del navegador).

---

## CU-11: Borrar índice o historial de chat

- **Borrar índice:** Elimina datos vectoriales (p. ej. `./chroma_db`) y reinicia la selección de fuentes; no borra necesariamente los PDF en `./docs` salvo que el operador los elimine a mano.
- **Borrar historial:** Solo vacía mensajes del chat en la sesión Streamlit.

---

## CU-12: Reindexación programada (`reindex.py`)

- **Objetivo:** Actualizar el índice después de sincronizar una carpeta local (sin abrir Streamlit).
- **Actores:** Administrador o job `cron` / script post-`rclone`.
- **Flujo principal:** `python reindex.py --path <carpeta>` [opciones `--merge`, `--db`, `--no-recursive`].
- **Referencias:** [MANUAL_DESARROLLO.md](./MANUAL_DESARROLLO.md) sección 3, [ejemplo cron](./examples/reindex_cron_rclone.example.sh).

---

## Trazabilidad documental

| Caso | Manual de usuario | Requisitos funcionales (RF) |
|------|-------------------|-----------------------------|
| CU-01 | §6.1 | RF-03 |
| CU-02 | §5.2 | RF-02, RF-13 |
| CU-03 | §5.2 | RF-02 |
| CU-04 | §5.3, §6 | RF-04 |
| CU-05 | §6.2 | RF-05 |
| CU-06 | §6.3 | RF-06, RF-08 |
| CU-07 | §6.4 | RF-07 |
| CU-08 | §5.1, §8 | RF-09 |
| CU-09 | Manual desarrollo §5 | RF-10 |
| CU-10 | §6.2–6.4 | RF-05–RF-07 |
| CU-11 | §5.2–5.4 | RF-14 |
| CU-12 | Manual desarrollo §3 | RF-11, RF-12 |

*Última revisión alineada con la tabla RF en `.kiro/specs/rag-testing-system/requirements.md`.*
