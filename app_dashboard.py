import streamlit as st
import os
import tempfile
import warnings
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# Configuración y Silenciado de avisos
warnings.filterwarnings("ignore")
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

# --- CONFIGURACIÓN ---
DB_PATH = "./chroma_db"
LM_STUDIO_URL = "http://localhost:1234/v1"

# --- ESTILOS PERSONALIZADOS ---
st.set_page_config(page_title="RAG Local Dashboard", page_icon="🤖", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #4CAF50; color: white; }
    .stChatInputContainer { padding-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE LÓGICA ---

def procesar_y_indexar(uploaded_files):
    """Procesa los archivos subidos y los guarda en ChromaDB"""
    documentos_totales = []
    
    for uploaded_file in uploaded_files:
        # Guardar temporalmente para que el cargador de LangChain lo lea
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        try:
            if uploaded_file.name.endswith(".pdf"):
                loader = PyPDFLoader(tmp_path)
            else:
                loader = TextLoader(tmp_path, encoding="utf-8")
            documentos_totales.extend(loader.load())
        finally:
            os.remove(tmp_path)

    # Chunking
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(documentos_totales)
    
    # Embeddings e Indexación
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = Chroma.from_documents(
        documents=chunks, 
        embedding=embeddings, 
        persist_directory=DB_PATH
    )
    return len(chunks)

def obtener_cadena_rag():
    """Crea la cadena de respuesta conectada a LM Studio"""
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    
    llm = ChatOpenAI(
        base_url=LM_STUDIO_URL,
        api_key="lm-studio",
        model="local-model",
        temperature=0.1
    )
    
    template = """Eres un asistente experto. Usa el contexto para responder. 
    Si no lo sabes, di que no tienes información.
    Contexto: {context}
    Pregunta: {question}
    Respuesta:"""
    
    prompt = PromptTemplate(template=template, input_variables=["context", "question"])
    
    return RetrievalQA.from_chain_type(
        llm=llm,
        retriever=db.as_retriever(search_kwargs={"k": 4}),
        chain_type_kwargs={"prompt": prompt}
    )

# --- INTERFAZ DE USUARIO (SIDEBAR) ---

with st.sidebar:
    st.title("📂 Gestión de Documentos")
    st.info("Sube tus archivos para alimentar al RAG.")
    
    archivos = st.file_uploader("Cargar PDF o TXT", accept_multiple_files=True, type=['pdf', 'txt'])
    
    if st.button("🚀 Indexar Documentos"):
        if archivos:
            with st.spinner("Procesando archivos y creando vectores..."):
                num_chunks = procesar_y_indexar(archivos)
                st.success(f"¡Hecho! Se han creado {num_chunks} fragmentos.")
        else:
            st.warning("Por favor, sube algún archivo primero.")

    if st.button("🗑️ Limpiar Base de Datos"):
        if os.path.exists(DB_PATH):
            import shutil
            shutil.rmtree(DB_PATH)
            st.success("Base de datos borrada.")
            st.rerun()

# --- INTERFAZ DE CHAT ---

st.title("💬 Chat con tu IA Local")
st.caption("Consulta tus documentos de forma privada desde cualquier dispositivo de la red.")

# Inicializar historial de chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar mensajes previos
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada de usuario
if prompt := st.chat_input("¿Qué quieres saber de tus documentos?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if not os.path.exists(DB_PATH):
            respuesta = "Primero debes indexar algún documento en el panel de la izquierda."
            st.markdown(respuesta)
        else:
            with st.spinner("Pensando..."):
                try:
                    qa = obtener_cadena_rag()
                    resultado = qa.invoke({"query": prompt})
                    respuesta = resultado["result"]
                    st.markdown(respuesta)
                except Exception as e:
                    respuesta = f"Error de conexión: ¿Está LM Studio encendido? ({e})"
                    st.error(respuesta)
        
    st.session_state.messages.append({"role": "assistant", "content": respuesta})
