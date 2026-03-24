"""Agente ReAct con LM Studio — misma configuración de modelo que rag_chain_lm."""
from langchain.tools import tool
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub
from langchain_openai import ChatOpenAI
from rag_chain_lm import crear_cadena_rag, LM_STUDIO_URL, LM_STUDIO_MODEL
from datetime import datetime
import os


@tool
def consultar_documentos(pregunta: str) -> str:
    """Consulta la base de conocimiento interna."""
    try:
        cadena = crear_cadena_rag()
        resultado = cadena.invoke({"query": pregunta})
        return resultado["result"]
    except Exception as e:
        return f"Error al consultar documentos: {e}"


@tool
def obtener_fecha_actual(input_text: str = "") -> str:
    """Fecha y hora actual."""
    return datetime.now().strftime("%A, %d de %B de %Y, %H:%M")


@tool
def buscar_palabra_clave_en_texto(palabra: str) -> str:
    """Cuenta apariciones en fragmentos relevantes."""
    try:
        cadena = crear_cadena_rag()
        docs = cadena.retriever.get_relevant_documents(palabra)
        total = sum(doc.page_content.lower().count(palabra.lower()) for doc in docs)
        return f"La palabra '{palabra}' aparece aproximadamente {total} veces en fragmentos relevantes."
    except Exception as e:
        return f"No se pudo realizar la búsqueda: {e}"


def crear_agente():
    llm = ChatOpenAI(
        base_url=LM_STUDIO_URL,
        api_key="lm-studio",
        model=LM_STUDIO_MODEL,
        temperature=0.1,
    )
    tools = [consultar_documentos, obtener_fecha_actual, buscar_palabra_clave_en_texto]
    try:
        prompt = hub.pull("hwchase17/react")
    except Exception:
        print("No se pudo descargar el prompt de LangChain Hub (¿internet?).")
        return None
    agente = create_react_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agente,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=5,
    )


if __name__ == "__main__":
    print("--- Agente local (LM Studio) ---")
    print("Escribe 'salir' para terminar.")
    executor = crear_agente()
    if executor:
        while True:
            pregunta = input("\nTú: ")
            if pregunta.lower() in ["salir", "exit", "quit"]:
                break
            try:
                respuesta = executor.invoke({"input": pregunta})
                print(f"\nAsistente: {respuesta['output']}")
            except Exception as e:
                print(f"\nError: {e}")
