from langchain.tools import tool
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub
from langchain_openai import ChatOpenAI
from rag_chain import crear_cadena_rag
from datetime import datetime
import os

# Configuración del servidor local de LM Studio
LM_STUDIO_URL = "http://localhost:1234/v1"

# --- TOOL 1: Consulta RAG sobre los documentos ---
@tool
def consultar_documentos(pregunta: str) -> str:
    """Consulta la base de conocimiento interna para responder preguntas 
    específicas sobre los documentos indexados (manuales, procedimientos, etc.)."""
    try:
        cadena = crear_cadena_rag()
        resultado = cadena.invoke({"query": pregunta})
        return resultado["result"]
    except Exception as e:
        return f"Error al consultar documentos: {e}"

# --- TOOL 2: Fecha y hora actual ---
@tool
def obtener_fecha_actual(input_text: str = "") -> str:
    """Devuelve la fecha y hora actual del sistema. Útil si el usuario pregunta 'qué día es'."""
    return datetime.now().strftime("%A, %d de %B de %Y, %H:%M")

# --- TOOL 3: (Adicional Propia) Contador de palabras clave ---
@tool
def buscar_palabra_clave_en_texto(palabra: str) -> str:
    """Busca cuántas veces aparece una palabra específica en el contexto de los documentos.
    Recibe una única palabra como argumento."""
    try:
        cadena = crear_cadena_rag()
        # Recuperamos los documentos para buscar manualmente
        docs = cadena.retriever.get_relevant_documents(palabra)
        total = sum(doc.page_content.lower().count(palabra.lower()) for doc in docs)
        return f"La palabra '{palabra}' aparece aproximadamente {total} veces en los fragmentos más relevantes."
    except Exception as e:
        return f"No se pudo realizar la búsqueda: {e}"

def crear_agente():
    """
    Configura el agente ReAct con las herramientas definidas.
    """
    # 1. Configurar el LLM local
    llm = ChatOpenAI(
        base_url=LM_STUDIO_URL,
        api_key="lm-studio",
        model="local-model",
        temperature=0.1
    )

    # 2. Definir el conjunto de herramientas
    tools = [consultar_documentos, obtener_fecha_actual, buscar_palabra_clave_en_texto]

    # 3. Obtener el prompt estándar para agentes ReAct
    # Requiere: pip install langchainhub
    try:
        prompt = hub.pull("hwchase17/react")
    except Exception:
        print("Error al descargar el prompt de LangChain Hub. Asegúrate de tener conexión a internet.")
        return None

    # 4. Construir el agente
    agente = create_react_agent(llm, tools, prompt)
    
    # 5. Crear el ejecutor (con verbose=True para ver el razonamiento)
    return AgentExecutor(
        agent=agente, 
        tools=tools, 
        verbose=True, 
        handle_parsing_errors=True,
        max_iterations=5  # Evita bucles infinitos en modelos pequeños
    )

if __name__ == "__main__":
    print("--- Asistente Inteligente Local Iniciado ---")
    print("Escribe 'salir' para finalizar.")
    
    executor = crear_agente()
    
    if executor:
        while True:
            pregunta = input("\nTú: ")
            if pregunta.lower() in ["salir", "exit", "quit"]:
                break
                
            try:
                # El agente decidirá qué tool usar basándose en la pregunta
                respuesta = executor.invoke({"input": pregunta})
                print(f"\nAsistente: {respuesta['output']}")
            except Exception as e:
                print(f"\nError en el agente: {e}")
