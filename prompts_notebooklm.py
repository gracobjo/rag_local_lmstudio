"""
Sistema de prompting para la app RAG local (orientación tipo NotebookLM).

Principios:
- El modelo solo “entiende” los documentos a través del CONTEXTO recuperado (no inventa).
- Cada modo usa una consulta de recuperación y un prompt distinto.
- Los prompts están en español; ajusta tono si la documentación es en otro idioma.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

# --- Conocimiento de la aplicación (inyectable como system o preámbulo) ---

APP_CONTEXT_FOR_MODEL: Final[str] = """Eres el asistente integrado en una aplicación local de tipo RAG.

Cómo funciona la aplicación:
- El usuario sube documentos (PDF, TXT) que se dividen en fragmentos y se indexan en ChromaDB con embeddings locales.
- Las respuestas deben basarse en el CONTEXTO recuperado que recibirás; no asumas datos de internet ni de memoria.
- Si el contexto no basta, dilo con claridad y sugiere indexar más documentos o reformular la petición.

Tu rol según el modo que indique el usuario: chat abierto, resumen, cuestionario o guía de estudio."""


class ModoContenido(str, Enum):
    CHAT = "chat"
    RESUMEN = "resumen"
    CUESTIONARIO = "cuestionario"
    GUIA_ESTUDIO = "guia_estudio"


# --- Consultas auxiliares para recuperar fragmentos útiles según el modo ---

def consulta_recuperacion(modo: ModoContenido, tema_usuario: str = "") -> str:
    """
    Pregunta “sintética” al retriever para traer chunks relevantes al modo.
    """
    t = (tema_usuario or "").strip()
    base = {
        ModoContenido.CHAT: t or "información relevante para responder la consulta",
        ModoContenido.RESUMEN: t
        or "ideas principales definiciones conclusiones estructura del documento",
        ModoContenido.CUESTIONARIO: t
        or "conceptos definiciones datos fechas nombres listados tablas hechos verificables",
        ModoContenido.GUIA_ESTUDIO: t
        or "conceptos clave términos relaciones entre ideas para estudiar",
    }
    return base[modo]


# --- Plantillas: {context} = texto unido de fragmentos; {instruccion} = petición concreta ---

PROMPT_CHAT: Final[str] = """{app_context}

{context}

Pregunta del usuario: {instruccion}

Instrucciones:
- Responde usando solo el contexto anterior.
- Si algo no está en el contexto, di exactamente: "No tengo información sobre eso en los documentos indexados."
- Sé claro y estructurado."""

# Chat con turnos previos (memoria conversacional). Los hechos siguen viniendo solo del {context}.
PROMPT_CHAT_MEMORIA: Final[str] = """{app_context}

HISTORIAL DE LA CONVERSACIÓN (sirve para entender referencias, pronombres y seguimiento; no reemplaza a los documentos):
{history}

CONTEXTO RECUPERADO DE LOS DOCUMENTOS INDEXADOS:
{context}

Pregunta actual del usuario: {instruccion}

Instrucciones:
- Los datos y citas deben basarse en el CONTEXTO DOCUMENTAL anterior.
- Usa el historial solo para interpretar lo que el usuario quiere decir ahora (p. ej. "resume eso", "¿y el apartado 2?").
- Si falta información en el contexto documental, di exactamente: "No tengo información sobre eso en los documentos indexados."
- Sé claro; si hace falta, resume brevemente antes de responder."""

PROMPT_RESUMEN: Final[str] = """{app_context}

CONTEXTO (fragmentos del documento indexado):
{context}

Petición: {instruccion}

Genera un RESUMEN útil con esta estructura en Markdown:
## Resumen ejecutivo
(3–6 frases)

## Ideas clave
- Viñetas con los puntos más importantes

## Términos o definiciones (si aplican)
- Término: breve definición según el contexto

## Limitaciones
- Indica si el contexto parece parcial o si falta información para un resumen completo."""

PROMPT_CUESTIONARIO: Final[str] = """{app_context}

CONTEXTO (solo puedes basarte en esto):
{context}

Petición: {instruccion}

Genera un cuestionario tipo test en formato JSON ESTRICTO (sin markdown fuera del JSON, sin comentarios).
Esquema obligatorio:
{{
  "titulo": "string",
  "preguntas": [
    {{
      "id": 1,
      "pregunta": "texto de la pregunta",
      "opciones": ["opción A", "opción B", "opción C", "opción D"],
      "indice_correcta": 0,
      "explicacion": "por qué la opción correcta se deduce del contexto",
      "numero_fragmento": 1,
      "fuente_archivo": "ruta ABSOLUTA exactamente igual que en (archivo: ...) del fragmento de donde sale la respuesta",
      "donde_encontrarlo": "pista concreta: epígrafe, tabla, artículo, definición o idea del texto para buscar en ese PDF/documento"
    }}
  ]
}}

Reglas:
- Exactamente 4 opciones por pregunta.
- indice_correcta es 0–3 según la opción correcta.
- numero_fragmento: entero del encabezado [Fragmento N] que mejor respalda la pregunta.
- fuente_archivo: copia literal de la ruta que aparece tras «archivo:» en ese fragmento (para enlaces locales en la app).
- Si el contexto no permite preguntas suficientes, devuelve solo las posibles y añade en "titulo" una nota breve de limitación.
- No inventes hechos que no estén respaldados por el contexto.

Salida obligatoria: un único objeto JSON válido (UTF-8). No uses bloques markdown, no escribas ``` ni texto antes o después del JSON.
No escribas introducción ni despedida: el primer carácter de tu respuesta debe ser «{{» y el último «}}»."""

PROMPT_GUIA_ESTUDIO: Final[str] = """{app_context}

CONTEXTO:
{context}

Petición: {instruccion}

Crea una GUÍA DE ESTUDIO en Markdown:
## Mapa del tema
(organización lógica de lo que cubre el contexto)

## Preguntas de autoevaluación
- Lista de preguntas abiertas cortas (sin respuesta), para que el usuario practique

## Posibles confusiones
- Contrasta conceptos que podrían confundirse **solo si** el contexto lo permite

## Qué repasar
- 3–7 puntos concretos basados en el contexto"""


@dataclass(frozen=True)
class PlantillaModo:
    plantilla: str
    temperatura: float
    k_fragmentos: int


def configuracion_modo(modo: ModoContenido) -> PlantillaModo:
    """Temperatura y amplitud de recuperación por modo (ajustable)."""
    if modo == ModoContenido.CHAT:
        return PlantillaModo(PROMPT_CHAT, temperatura=0.2, k_fragmentos=6)
    if modo == ModoContenido.RESUMEN:
        return PlantillaModo(PROMPT_RESUMEN, temperatura=0.3, k_fragmentos=14)
    if modo == ModoContenido.CUESTIONARIO:
        return PlantillaModo(PROMPT_CUESTIONARIO, temperatura=0.1, k_fragmentos=16)
    if modo == ModoContenido.GUIA_ESTUDIO:
        return PlantillaModo(PROMPT_GUIA_ESTUDIO, temperatura=0.3, k_fragmentos=12)
    raise ValueError(modo)
