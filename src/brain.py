import os
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

@st.cache_resource
def get_embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def build_brain(source_type, uploaded_files, pasted_text, website_url):
    try:
        with st.spinner("Brain bana raha hu..."):
            all_text = ""
            if source_type == "PDF Upload" and uploaded_files:
                for f in uploaded_files:
                    with open(f"temp_{f.name}", "wb") as tmp:
                        tmp.write(f.getbuffer())
                    loader = PyPDFLoader(f"temp_{f.name}")
                    pages = loader.load()
                    st.session_state.stats["pages"] += len(pages)
                    for p in pages: all_text += p.page_content + "\n"
                    os.remove(f"temp_{f.name}")
                st.session_state.doc_name = f"{len(uploaded_files)} PDFs"
            elif source_type == "Paste Text" and pasted_text:
                all_text = pasted_text
                st.session_state.doc_name = "Pasted Text"
            elif source_type == "Website Link" and website_url:
                loader = WebBaseLoader(website_url)
                docs = loader.load()
                all_text = "\n".join([d.page_content for d in docs])
                st.session_state.doc_name = website_url[:30]
            if not all_text.strip():
                st.error("Pehle kuch upload / paste karo!")
                return None
            splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
            chunks = splitter.split_text(all_text)
            embeddings = get_embeddings()
            docs = [Document(page_content=c) for c in chunks]
            vs = FAISS.from_documents(docs, embeddings)
            st.session_state.vectorstore = vs
            st.session_state.stats["chunks"] = len(chunks)
            return f"Brain Ready! {len(chunks)} chunks | {len(all_text)} chars"
    except Exception as e:
        st.error(f"Error: {e}")
        return None
