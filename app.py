import streamlit as st
import os
from src.llm import get_llm
from src.brain import build_brain_from_docs, load_saved_brain
from src.memory import init_db, load_chat, save_chat, clear_memory
from langchain_community.document_loaders import WebBaseLoader, PyPDFLoader
from langchain_core.documents import Document

st.set_page_config(page_title="NeuroDocs AI", page_icon="🧠", layout="wide")

# --- COOL GRAPHIC ---
st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); color: white; }
h1,h2,h3 { color: white !important; }
.stButton>button { background: linear-gradient(90deg, #FF6B6B, #FFD93D); color: black; font-weight: bold; border-radius: 20px; border: none; }
.stTextInput>div>div>input, .stTextArea>div>div>textarea { background: #1e1e3f; color: white; border-radius: 15px; }
[data-testid="stSidebar"] { background: #1a1a2e; }
div[data-testid="stChatMessage"] { background: rgba(255,255,255,0.08); border-radius: 15px; }
.small-mode label { font-size: 12px !important; }
</style>
""", unsafe_allow_html=True)

st.title("🧠 NeuroDocs AI")
st.caption("PDF + 100 URLs + Memory + Apni API Key | Learn Anything")

# --- SESSION ---
if "chat" not in st.session_state:
    init_db()
    st.session_state.chat = load_chat()
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = load_saved_brain()
if "doc_name" not in st.session_state:
    st.session_state.doc_name = "General"

# --- SIDEBAR: API KEY + SETTINGS ---
with st.sidebar:
    st.header("🔑 Apni API Key")
    st.caption("Teri key save nahi hoti, sirf is session ke liye")
    groq_k = st.text_input("Groq Key", type="password", placeholder="gsk_...")
    gemini_k = st.text_input("Gemini Key", type="password", placeholder="AIza...")
    openai_k = st.text_input("OpenAI Key", type="password", placeholder="sk-...")
    st.divider()
    st.header("⚙️ Settings")
    model_choice = st.selectbox("Model", ["OpenAI GPT-OSS 20B - Fast (FREE)", "OpenAI GPT-OSS 120B - Smart (FREE)", "Gemini 2.0 Flash", "OpenAI GPT-4o-mini"])
    # DETAIL BADA
    detail = st.slider("📏 Kitna Detail Chahiye?", 1, 5, 3)
    st.caption(f"{'1=1 Line' if detail==1 else '2=Short' if detail==2 else '3=Detail' if detail==3 else '4=Full Example' if detail==4 else '5=Full Chapter'}")
    # MODE CHHOTA
    st.markdown('<div class="small-mode">', unsafe_allow_html=True)
    mode = st.radio("🎭 Style", ["Normal", "5 Year Old 👶", "Exam Mode 📝", "Hinglish 🇮🇳"], horizontal=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.divider()
    if st.button("🗑️ Memory Clear"):
        clear_memory()
        st.session_state.chat = []
        st.rerun()
    if st.button("📄 Chat ko Notes Banao"):
        notes = "\n\n".join([f"{c['role']}: {c['content']}" for c in st.session_state.chat])
        st.download_button("⬇️ Notes Download Karo", notes, file_name="NeuroDocs-Notes.txt")

user_keys = {"GROQ_API_KEY": groq_k, "GOOGLE_API_KEY": gemini_k, "OPENAI_API_KEY": openai_k}

# --- AUTO URL + PDF ---
col1, col2 = st.columns([2,1])
with col1:
    st.subheader("🌐 URLs Automatic - 100 Ek Saath")
    urls_text = st.text_area("Har line me 1 URL", placeholder="https://en.wikipedia.org/wiki/Photosynthesis\nhttps://example.com/blog", height=100)
    if st.button("🚀 Saare URL Add Karo"):
        urls = [u.strip() for u in urls_text.split("\n") if u.strip().startswith("http")]
        if urls:
            with st.spinner(f"{len(urls)} URLs padh raha hu..."):
                docs = []
                for url in urls:
                    try: docs += WebBaseLoader(url).load()
                    except: pass
                st.session_state.vectorstore = build_brain_from_docs(docs)
                st.session_state.doc_name = f"{len(urls)} URLs"
                st.success(f"Ho gaya! {len(urls)} URLs, {len(docs)} pages add ho gaye!")
        else:
            st.warning("Pehle URL daalo!")
with col2:
    st.subheader("📄 PDF Daalo")
    pdf = st.file_uploader("PDF", type=["pdf"])
    if pdf and st.button("PDF Add Karo"):
        with open("temp.pdf","wb") as f: f.write(pdf.getbuffer())
        docs = PyPDFLoader("temp.pdf").load()
        st.session_state.vectorstore = build_brain_from_docs(docs)
        st.session_state.doc_name = pdf.name
        st.success(f"{pdf.name} add ho gaya!")

# --- 5 IDEAS BUTTONS ---
c1,c2,c3,c4,c5 = st.columns(5)
if c1.button("🎯 Quiz Banao"): st.session_state.quiz = True
if c2.button("🗂️ Flashcards"): st.session_state.flash = True
if c3.button("🗺️ Mind Map"): st.session_state.mind = True
if c4.button("📝 Summary"): st.session_state.summary = True
if c5.button("🎙️ Voice (Jald)"): st.info("Voice wala next update me ayega!")

# --- CHAT ---
for m in st.session_state.chat:
    with st.chat_message(m["role"]): st.write(m["content"])

if q := st.chat_input("Kuch bhi puch..."):
    st.session_state.chat.append({"role":"user","content":q})
    save_chat("user", q)
    with st.chat_message("user"): st.write(q)

    llm, name = get_llm(model_choice, user_keys)
    # Memory + Context
    context = ""
    if st.session_state.vectorstore:
        docs = st.session_state.vectorstore.similarity_search(q, k=3)
        context = "\n".join([d.page_content[:2000] for d in docs])

    detail_map = {1:"1 line me jawab de",2:"short me",3:"detail me",4:"bahut detail me example ke saath",5:"full chapter jaisa heading ke saath"}
    extra = ""
    if st.session_state.get("quiz"): extra = "Is topic pe 5 MCQ quiz bana, answer last me de."; st.session_state.quiz=False
    if st.session_state.get("flash"): extra = "Is topic ke 5 Flashcards bana Q: A: format me."; st.session_state.flash=False
    if st.session_state.get("mind"): extra = "Is topic ka Mind Map bana, tree structure me."; st.session_state.mind=False
    if st.session_state.get("summary"): extra = "Iska short summary bana, 5 points me."; st.session_state.summary=False

    prompt = f"Style: {mode}. Detail: {detail_map[detail]}. {extra}\nContext: {context}\nSawal: {q}\nAgar context me nahi hai toh apne knowledge se jawab de."

    with st.chat_message("assistant"):
        if not llm:
            ans = "Demo Mode - Sidebar me apni Groq Key daalo (Free hai - console.groq.com se milegi)"
            st.write(ans)
        else:
            ans = llm.invoke(prompt).content
            st.write(ans)
            st.caption(f"Model: {name} | Source: {st.session_state.doc_name}")
    st.session_state.chat.append({"role":"assistant","content":ans})
    save_chat("assistant", ans)
