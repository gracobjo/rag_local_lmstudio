import warnings
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional

# Silenciar avisos para una salida limpia en producción
warnings.filterwarnings("ignore")
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
import uvicorn

# LangChain e IA
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.tools import tool

# Importamos la lógica RAG del archivo previo
from rag_chain import crear_cadena_rag

# --- CONFIGURACIÓN DE RUTAS ---
DOCS_PATH = "./docs"
DB_PATH = "./chroma_db"

# Asegurar que la carpeta de documentos existe
if not os.path.exists(DOCS_PATH):
    os.makedirs(DOCS_PATH)

# --- LÓGICA DE INGESTA INTEGRADA (Para evitar ModuleNotFoundError) ---

def cargar_documentos(ruta):
    """Carga archivos PDF y TXT desde la carpeta especificada."""
    documentos = []
    if not os.path.exists(ruta):
        return documentos

    for fichero in os.listdir(ruta):
        ruta_completa = os.path.join(ruta, fichero)
        loader = None
        if fichero.endswith(".pdf"):
            loader = PyPDFLoader(ruta_completa)
        elif fichero.endswith(".txt"):
            loader = TextLoader(ruta_completa, encoding="utf-8")
        
        if loader:
            documentos.extend(loader.load())
    return documentos

def indexar(documentos):
    """Procesa los documentos y los guarda en la base de datos vectorial."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(documentos)
    
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    # Crear y persistir la base de datos
    db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=DB_PATH
    )
    return len(chunks)

# --- MODELOS DE DATOS ---

class ChatRequest(BaseModel):
    session_id: str = Field(..., example="usuario_01", description="ID único para mantener el historial del stakeholder")
    pregunta: str = Field(..., example="¿Qué dice el manual sobre seguridad?", description="La consulta al sistema RAG")

class ChatResponse(BaseModel):
    session_id: str
    respuesta: str
    timestamp: str

class UploadResponse(BaseModel):
    mensaje: str
    archivo: str
    estado: str

# --- GESTIÓN DE MEMORIA POR SESIÓN ---

sessions_memory: Dict[str, ConversationBufferMemory] = {}

def obtener_memoria_sesion(session_id: str) -> ConversationBufferMemory:
    """Crea o recupera la memoria específica para un session_id."""
    if session_id not in sessions_memory:
        sessions_memory[session_id] = ConversationBufferMemory(
            memory_key="chat_history", 
            return_messages=False
        )
    return sessions_memory[session_id]

# --- HERRAMIENTAS DEL AGENTE (Tools) ---

@tool
def consultar_documentos(pregunta: str) -> str:
    """Consulta la base de conocimiento interna para responder dudas sobre manuales y procedimientos."""
    try:
        cadena = crear_cadena_rag()
        resultado = cadena.invoke({"query": pregunta})
        return resultado["result"]
    except Exception as e:
        return f"Error en el sistema RAG: {e}"

@tool
def obtener_hora_servidor(dummy: str = "") -> str:
    """Devuelve la hora actual del servidor central."""
    return datetime.now().strftime("%H:%M:%S")

# --- PROMPT DEL AGENTE ---

AGENT_PROMPT = """Eres un asistente de IA de nivel empresarial. Ayudas a los stakeholders con información técnica basada en documentos.

HERRAMIENTAS DISPONIBLES:
{tools}

INSTRUCCIONES DE FORMATO:
Para usar una herramienta, usa este formato exacto:
Thought: ¿Necesito una herramienta? Sí
Action: [{tool_names}]
Action Input: la entrada para la herramienta
Observation: el resultado de la herramienta

Cuando tengas la respuesta final para el stakeholder:
Thought: ¿Necesito una herramienta? No
Final Answer: [Tu respuesta profesional y detallada aquí]

HISTORIAL DE CONVERSACIÓN:
{chat_history}

CONSULTA ACTUAL:
{input}

{agent_scratchpad}"""

# --- APLICACIÓN FASTAPI ---

app = FastAPI(
    title="RAG Enterprise Hub",
    description="API de IA Local con carga de archivos, Swagger y memoria persistente por sesión.",
    version="3.0.0"
)

# --- ENDPOINTS ---

@app.get("/", tags=["Sistema"])
def estado_api():
    """Verifica si el servicio está en línea."""
    return {"status": "online", "server_time": datetime.now().isoformat()}

@app.post("/chat", response_model=ChatResponse, tags=["IA"])
async def chat(request: ChatRequest):
    """Envía una pregunta al asistente manteniendo hilos de conversación separados."""
    try:
        llm = ChatOpenAI(
            base_url="http://localhost:1234/v1",
            api_key="lm-studio",
            model="local-model",
            temperature=0.1
        )
        
        tools = [consultar_documentos, obtener_hora_servidor]
        prompt = PromptTemplate.from_template(AGENT_PROMPT)
        memory = obtener_memoria_sesion(request.session_id)
        
        agent = create_react_agent(llm, tools, prompt)
        executor = AgentExecutor(
            agent=agent, 
            tools=tools, 
            memory=memory, 
            verbose=True, 
            handle_parsing_errors=True,
            max_iterations=5
        )
        
        resultado = executor.invoke({"input": request.pregunta})
        
        return ChatResponse(
            session_id=request.session_id,
            respuesta=resultado["output"],
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el procesamiento del chat: {str(e)}")

@app.post("/upload", response_model=UploadResponse, tags=["Documentación"])
async def subir_documento(file: UploadFile = File(...)):
    """Sube e indexa automáticamente un archivo PDF o TXT."""
    if not (file.filename.endswith(".pdf") or file.filename.endswith(".txt")):
        raise HTTPException(status_code=400, detail="Solo se admiten archivos .pdf y .txt")
    
    file_path = os.path.join(DOCS_PATH, file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"Indexando nuevo archivo: {file.filename}...")
        documentos = cargar_documentos(DOCS_PATH)
        indexar(documentos)
        
        return UploadResponse(
            mensaje="Archivo recibido e indexado con éxito",
            archivo=file.filename,
            estado="Procesado"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {e}")

@app.delete("/session/{session_id}", tags=["Sistema"])
def borrar_historial(session_id: str):
    """Elimina el historial de conversación de un stakeholder específico."""
    if session_id in sessions_memory:
        del sessions_memory[session_id]
        return {"msg": f"Sesión {session_id} reiniciada correctamente."}
    return {"msg": "No existía historial para esta sesión."}

# --- EJECUCIÓN DEL SERVIDOR ---

if __name__ == "__main__":
    print("🚀 RAG Enterprise Hub activo")
    print("Documentación interactiva (Swagger): http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
