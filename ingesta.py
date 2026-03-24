from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import os

# Configuración de rutas según el documento de la práctica
DOCS_PATH = "./docs"
DB_PATH = "./chroma_db"

def cargar_documentos(ruta):
    """
    Carga archivos PDF y TXT desde la carpeta especificada.
    """
    documentos = []
    if not os.path.exists(ruta):
        print(f"Error: La carpeta {ruta} no existe.")
        return documentos

    for fichero in os.listdir(ruta):
        ruta_completa = os.path.join(ruta, fichero)
        loader = None
        
        if fichero.endswith(".pdf"):
            loader = PyPDFLoader(ruta_completa)
        elif fichero.endswith(".txt"):
            loader = TextLoader(ruta_completa, encoding="utf-8")
        else:
            print(f"Saltando archivo no compatible: {fichero}")
            continue
            
        if loader:
            print(f"Cargando: {fichero}")
            documentos.extend(loader.load())
            
    return documentos

def indexar(documentos):
    """
    Divide los documentos en trozos (chunks) y los guarda en la base de datos vectorial ChromaDB.
    """
    # 1. Configurar el splitter (Personalizado según Apartado A)
    # chunk_size=500: Equilibrio entre contexto y precisión.
    # chunk_overlap=50: Mantiene la continuidad entre fragmentos.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    
    chunks = splitter.split_documents(documentos)
    print(f"Documentos divididos en {len(chunks)} fragmentos.")

    # 2. Configurar el modelo de embeddings (Local)
    # Este modelo se descargará automáticamente la primera vez (aprox. 80MB)
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # 3. Crear y persistir la base de datos vectorial
    print("Creando base de datos vectorial en disco...")
    db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=DB_PATH
    )
    
    print(f"¡Éxito! Indexados {len(chunks)} chunks en {DB_PATH}")
    return db

if __name__ == "__main__":
    # Flujo principal
    print("Iniciando proceso de ingesta local...")
    docs = cargar_documentos(DOCS_PATH)
    
    if len(docs) > 0:
        indexar(docs)
    else:
        print("No se encontraron documentos válidos en la carpeta ./docs")
