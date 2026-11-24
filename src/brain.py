import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

def _get_embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def build_brain_from_docs(docs):
    """
    Takes list of Documents -> Splits into chunks -> Makes FAISS vectorstore
    Saves to brain_db folder for reuse
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)
    embeddings = _get_embeddings()
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local("brain_db")
    return vectorstore

def load_saved_brain():
    """
    Loads saved FAISS brain if brain_db exists, else returns None
    """
    if os.path.exists("brain_db"):
        try:
            embeddings = _get_embeddings()
            return FAISS.load_local("brain_db", embeddings, allow_dangerous_deserialization=True)
        except Exception:
            return None
    return None
