"""API FastAPI con LM Studio — misma lógica que api_service.py pero modelo correcto."""
import warnings
import os
import shutil
from datetime import datetime
from typing import Dict

warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
import uvicorn

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.tools import tool

from rag_chain_lm import crear_cadena_rag, LM_STUDIO_URL, LM_STUDIO_MODEL

DOCS_PATH = "./docs"
DB_PATH = "./chroma_db"

if not os.path.exists(DOCS_PATH):
    os.makedirs(DOCS_PATH)


def cargar_documentos(ruta):
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
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(documentos)
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=DB_PATH,
    )
    return len(chunks)


class ChatRequest(BaseModel):
    session_id: str = Field(..., example="usuario_01")
    pregunta: str = Field(..., example="¿Qué dice el manual?")


class ChatResponse(BaseModel):
    session_id: str
    respuesta: str
    timestamp: str


class UploadResponse(BaseModel):
    mensaje: str
    archivo: str
    estado: str


sessions_memory: Dict[str, ConversationBufferMemory] = {}


def obtener_memoria_sesion(session_id: str) -> ConversationBufferMemory:
    if session_id not in sessions_memory:
        sessions_memory[session_id] = ConversationBufferMemory(
            memory_key="chat_history", return_messages=False
        )
    return sessions_memory[session_id]


@tool
def consultar_documentos(pregunta: str) -> str:
    try:
        cadena = crear_cadena_rag()
        resultado = cadena.invoke({"query": pregunta})
        return resultado["result"]
    except Exception as e:
        return f"Error en el sistema RAG: {e}"


@tool
def obtener_hora_servidor(dummy: str = "") -> str:
    return datetime.now().strftime("%H:%M:%S")


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

app = FastAPI(
    title="RAG Enterprise Hub",
    description="API con LM Studio (modelo desde rag_chain_lm).",
    version="3.0.1",
)


@app.get("/", tags=["Sistema"])
def estado_api():
    return {"status": "online", "server_time": datetime.now().isoformat()}


@app.post("/chat", response_model=ChatResponse, tags=["IA"])
async def chat(request: ChatRequest):
    try:
        llm = ChatOpenAI(
            base_url=LM_STUDIO_URL,
            api_key="lm-studio",
            model=LM_STUDIO_MODEL,
            temperature=0.1,
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
            max_iterations=5,
        )
        resultado = executor.invoke({"input": request.pregunta})
        return ChatResponse(
            session_id=request.session_id,
            respuesta=resultado["output"],
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error en el procesamiento del chat: {str(e)}"
        )


@app.post("/upload", response_model=UploadResponse, tags=["Documentación"])
async def subir_documento(file: UploadFile = File(...)):
    if not (file.filename.endswith(".pdf") or file.filename.endswith(".txt")):
        raise HTTPException(status_code=400, detail="Solo .pdf y .txt")
    file_path = os.path.join(DOCS_PATH, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        documentos = cargar_documentos(DOCS_PATH)
        indexar(documentos)
        return UploadResponse(
            mensaje="Archivo recibido e indexado",
            archivo=file.filename,
            estado="Procesado",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/session/{session_id}", tags=["Sistema"])
def borrar_historial(session_id: str):
    if session_id in sessions_memory:
        del sessions_memory[session_id]
        return {"msg": f"Sesión {session_id} reiniciada."}
    return {"msg": "No había historial para esta sesión."}


if __name__ == "__main__":
    print("http://localhost:8000/docs — modelo:", LM_STUDIO_MODEL)
    uvicorn.run(app, host="0.0.0.0", port=8000)
