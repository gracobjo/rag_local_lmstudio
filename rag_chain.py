from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
import os

# Configuración de rutas y servidor
DB_PATH = "./chroma_db"
LM_STUDIO_URL = "http://localhost:1234/v1"

# Definición del Prompt (Personalizado según Apartado B de la práctica)
PROMPT_TEMPLATE = """Eres un asistente experto. Usa ÚNICAMENTE el siguiente contexto para responder.
Si la respuesta no está en el contexto, di: 'No tengo información sobre eso.'

Contexto:
{context}

Pregunta: {question}

Respuesta:"""

def crear_cadena_rag():
    """
    Configura y devuelve la cadena RetrievalQA conectada a LM Studio y ChromaDB.
    """
    # 1. Cargar los mismos embeddings que en ingest.py
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # 2. Conectar con la base de datos persistida
    # Usamos la versión de community para evitar conflictos de dependencias
    db = Chroma(
        persist_directory=DB_PATH, 
        embedding_function=embeddings
    )

    # 3. Configurar el retriever (recupera los 4 fragmentos más relevantes)
    retriever = db.as_retriever(search_kwargs={"k": 4})

    # 4. Configurar la conexión con LM Studio
    llm = ChatOpenAI(
        base_url=LM_STUDIO_URL,
        api_key="lm-studio",
        model="local-model",
        temperature=0.1
    )

    # 5. Crear el objeto del Prompt
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=PROMPT_TEMPLATE
    )

    # 6. Crear la cadena final
    cadena = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt}
    )

    return cadena

if __name__ == "__main__":
    print("--- Probando Sistema RAG Local ---")
    if not os.path.exists(DB_PATH):
        print(f"Error: No existe la carpeta {DB_PATH}. Ejecuta primero ingest.py")
    else:
        try:
            qa_chain = crear_cadena_rag()
            # Haz una pregunta específica sobre tus archivos aquí:
            pregunta = "¿Cuál es el contenido principal de los documentos?" 
            
            print(f"Consultando a LM Studio...")
            respuesta = qa_chain.invoke({"query": pregunta})
            
            print(f"\nPregunta: {pregunta}")
            print("-" * 30)
            print(f"Respuesta: {respuesta['result']}")
            print("-" * 30)
            
            if respuesta['source_documents']:
                print("\nFuentes consultadas:")
                for doc in respuesta['source_documents']:
                    print(f"- {doc.metadata.get('source', 'Desconocido')}")
        except Exception as e:
            print(f"Error de conexión: {e}")
            print("Verifica que LM Studio tenga el servidor activo en http://localhost:1234")
