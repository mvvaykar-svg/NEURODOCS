import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

def get_embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def build_brain_from_docs(docs):
    if not docs:
        return None
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)
    if not chunks:
        return None
    vs = FAISS.from_documents(chunks, get_embeddings())
    try:
        vs.save_local("faiss_index")
    except Exception:
        pass
    return vs

def build_brain(docs):
    return build_brain_from_docs(docs)

def load_saved_brain():
    if os.path.exists("faiss_index"):
        try:
            return FAISS.load_local("faiss_index", get_embeddings(), allow_dangerous_deserialization=True)
        except Exception:
            return None
    return None
