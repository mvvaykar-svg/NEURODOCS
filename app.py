import streamlit as st
import os
from src.llm import get_llm
from src.brain import build_brain_from_docs, load_saved_brain
from src.memory import init_db, load_chat, save_chat, clear_memory
from langchain_community.document_loaders import WebBaseLoader, PyPDFLoader
from langchain_core.documents import Document

st.set_page_config(page_title="NeuroDocs AI", page_icon="🧠", layout="wide")

# ========== NEW BACKGROUND + NEW GRAPHICS ==========
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&display=swap');
.stApp { 
    background: 
        radial-gradient(circle at 10% 10%, rgba(124,58,237,0.35) 0%, transparent 40%),
        radial-gradient(circle at 90% 20%, rgba(0,210,255,0.25) 0%, transparent 40%),
        radial-gradient(circle at 50% 100%, rgba(255,107,107,0.20) 0%, transparent 50%),
        linear-gradient(160deg, #0A0618 0%, #140B2E 35%, #1A0F3D 65%, #050510 100%);
    background-attachment: fixed;
    color: white; font-family: 'Inter', sans-serif; 
}
h1,h2,h3 { color: white !important; letter-spacing: -0.5px; }
p, span, label { color: #E8E8E8 !important; }
.block-container { padding-top: 1.2rem !important; padding-bottom: 1rem !important; }
div[data-testid="stVerticalBlock"] > div { margin-bottom: 8px; }

/* Main Title Graphic */
.main-title {
    font-size: 42px !important; font-weight: 900 !important; line-height: 1.1;
    background: linear-gradient(90deg, #FF6B6B, #FFD93D, #00D2FF, #A78BFA);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0px !important;
}
.sub-title { font-size: 15px; opacity: 0.75; margin-top: 6px; }

/* Glass */
.glass {
    background: rgba(255,255,255,0.06);
    backdrop-filter: blur(18px);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 22px; padding: 16px;
    margin-bottom: 14px;
}

/* Bot Buttons - Normal */
.stButton>button {
    background: linear-gradient(90deg, #FF6B6B, #FFD93D);
    color: #111 !important; font-weight: 800; border-radius: 30px; border: none;
    padding: 13px 18px !important; width: 100%;
    margin-bottom: 10px !important;
}

/* ===== QUICK ACTIONS - 6 COLOURED, BETTER ===== */
.quick-wrap { display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0 14px 0; }
div[data-testid="column"] .stButton>button {
    padding: 10px 6px !important;
    font-size: 12.5px !important;
    font-weight: 700 !important;
    border-radius: 16px !important;
    margin-bottom: 6px !important;
    border: none !important;
    box-shadow: 0 6px 18px rgba(0,0,0,0.3) !important;
    color: white !important;
}
/* 1 Quiz - Purple */
div[data-testid="column"]:nth-of-type(1) .stButton>button { background: linear-gradient(135deg, #7C3AED, #A78BFA) !important; }
/* 2 Cards - Blue */
div[data-testid="column"]:nth-of-type(2) .stButton>button { background: linear-gradient(135deg, #2563EB, #00D2FF) !important; }
/* 3 Map - Green */
div[data-testid="column"]:nth-of-type(3) .stButton>button { background: linear-gradient(135deg, #059669, #34D399) !important; }
/* 4 Summary - Orange */
div[data-testid="column"]:nth-of-type(4) .stButton>button { background: linear-gradient(135deg, #EA580C, #FBBF24) !important; }
/* 5 Simple - Pink */
div[data-testid="column"]:nth-of-type(5) .stButton>button { background: linear-gradient(135deg, #DB2777, #F472B6) !important; }
/* 6 Notes - Teal Dark */
div[data-testid="column"]:nth-of-type(6) .stButton>button { background: linear-gradient(135deg, #0F766E, #2DD4BF) !important; color: #06110F !important; }

div[data-testid="column"] .stButton>button:hover { transform: translateY(-2px) scale(1.03); filter: brightness(1.1); }

[data-testid="stSidebar"] .stButton>button {
    background: linear-gradient(90deg, #FF6B6B, #FFD93D) !important;
    color: #111 !important; font-size: 14px !important; padding: 12px !important;
}
.stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
    background: #171233 !important; color: white !important; border-radius: 16px !important; border: 1px solid rgba(255,255,255,0.15) !important;
}
[data-testid="stSidebar"] { background: #0A0618 !important; border-right: 1px solid rgba(255,255,255,0.08); }
div[data-testid="stChatMessage"] { 
    background: rgba(255,255,255,0.07); border-radius: 20px; 
    border: 1px solid rgba(255,255,255,0.1); 
    margin-bottom: 10px !important; padding: 14px !important;
}
.badge { background: #FFD93D; color: #111; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 800; }
.badge-blue { background: #6BCBFF; color: #111; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 800; }
.badge-purple { background: #A78BFA; color: #111; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 800; }

/* Typing Box */
[data-testid="stChatInput"] {
    background: #171233 !important;
    border-radius: 24px !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    padding: 6px 8px 6px 16px !important;
    box-shadow: 0 8px 30px rgba(0,0,0,0.45) !important;
    margin-bottom: 10px !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important; color: white !important;
    font-size: 14px !important; min-height: 42px !important; max-height: 42px !important; padding: 10px 0px !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: #9A8FBF !important; }
[data-testid="stChatInput"] button {
    background: linear-gradient(90deg, #FF6B6B, #FFD93D) !important; color: #111 !important;
    border-radius: 50% !important; width: 36px !important; height: 36px !important; min-width: 36px !important;
}
</style>
""", unsafe_allow_html=True)

# ========== HEADER - NEW GRAPHIC, UNLIMITED BOX HATA DIYA ==========
st.markdown("<div class='main-title'>🧠 NeuroDocs AI</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Your Universal AI Assistant — Ask <b>Anything</b> • Learn From <b>Your Files</b></div>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<span class='badge'>✨ LLM BOT</span> &nbsp; <span class='badge-blue'>📚 RAG BOT</span> &nbsp; <span class='badge-purple'>🎯 6 SMART TOOLS</span>", unsafe_allow_html=True)
st.markdown("<br><br>", unsafe_allow_html=True)

# ========== SESSION ==========
if "chat" not in st.session_state:
    init_db()
    st.session_state.chat = load_chat()
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = load_saved_brain()
if "doc_name" not in st.session_state:
    st.session_state.doc_name = "No Document"
if "bot_mode" not in st.session_state:
    st.session_state.bot_mode = "LLM Bot"
for k in ["quiz","flash","mind","summary","simple","notes"]:
    if k not in st.session_state: st.session_state[k] = False

# ========== BOT CHOICE ==========
st.markdown("### 🤖 Choose Your Bot")
col1, col2 = st.columns(2)
with col1:
    if st.session_state.bot_mode == "LLM Bot":
        st.markdown("<div style='background: linear-gradient(90deg,#FF6B6B,#FFD93D); color:#111; border-radius:20px; padding:16px; text-align:center; font-weight:800; margin-bottom:10px'>🧠 LLM BOT<br><span style='font-size:12px; font-weight:600'>✅ ACTIVE</span></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='background: rgba(255,255,255,0.07); border:1px solid rgba(255,255,255,0.15); border-radius:20px; padding:16px; text-align:center; margin-bottom:10px'>🧠 LLM BOT<br><span style='font-size:12px; opacity:0.7'>Ask Anything</span></div>", unsafe_allow_html=True)
    if st.button("Use LLM Bot", key="llm_btn"):
        st.session_state.bot_mode = "LLM Bot"
        st.rerun()
with col2:
    if st.session_state.bot_mode == "RAG Bot":
        st.markdown("<div style='background: linear-gradient(90deg,#FF6B6B,#FFD93D); color:#111; border-radius:20px; padding:16px; text-align:center; font-weight:800; margin-bottom:10px'>📚 RAG BOT<br><span style='font-size:12px; font-weight:600'>✅ ACTIVE</span></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='background: rgba(255,255,255,0.07); border:1px solid rgba(255,255,255,0.15); border-radius:20px; padding:16px; text-align:center; margin-bottom:10px'>📚 RAG BOT<br><span style='font-size:12px; opacity:0.7'>From Your File</span></div>", unsafe_allow_html=True)
    if st.button("Use RAG Bot", key="rag_btn"):
        st.session_state.bot_mode = "RAG Bot"
        st.rerun()

if st.session_state.bot_mode == "LLM Bot":
    st.info("💡 **LLM Bot:** Ask ANYTHING. No file needed.")
else:
    st.warning(f"📚 **RAG Bot:** Only from: `{st.session_state.doc_name}`")

# ========== SIDEBAR ==========
with st.sidebar:
    st.markdown("## 🔑 Your API Key")
    st.caption("Not saved. Only for this session.")
    groq_k = st.text_input("Groq Key (Free)", type="password", placeholder="gsk_...")
    gemini_k = st.text_input("Gemini Key", type="password", placeholder="AIza...")
    openai_k = st.text_input("OpenAI Key", type="password", placeholder="sk-...")
    st.markdown("[Get Free Groq Key →](https://console.groq.com)")
    st.divider()
    st.markdown("## ⚙️ Settings")
    model_choice = st.selectbox("Choose Model", ["OpenAI GPT-OSS 20B - Fast (FREE)", "OpenAI GPT-OSS 120B - Smart (FREE)", "Gemini 2.0 Flash", "OpenAI GPT-4o-mini"])
    detail = st.slider("Detail", 1, 5, 3)
    detail_labels = {1:"1 - One Line", 2:"2 - Short", 3:"3 - Detailed", 4:"4 - Full Example", 5:"5 - Full Chapter"}
    st.success(f"**{detail_labels[detail]}**")
    mode = st.radio("🎭 Style", ["Normal", "Explain Like 5 Year Old 👶", "Exam Mode 📝", "Simple English 🇬🇧"], horizontal=True)
    st.divider()
    if st.button("🗑️ Clear Chat"):
        clear_memory()
        st.session_state.chat = []
        st.session_state.vectorstore = None
        st.session_state.doc_name = "No Document"
        st.rerun()
    if st.button("📄 Download Chat as Notes"):
        notes = "\n\n".join([f"{c['role']}: {c['content']}" for c in st.session_state.chat])
        st.download_button("⬇️ Download", notes, file_name="NeuroDocs-Notes.txt")

user_keys = {"GROQ_API_KEY": groq_k, "GOOGLE_API_KEY": gemini_k, "OPENAI_API_KEY": openai_k}

# ========== RAG UPLOAD ==========
if st.session_state.bot_mode == "RAG Bot":
    st.markdown("### 📚 Add Your Study Material")
    tab1, tab2, tab3 = st.tabs(["🌐 URLs", "📄 PDF Upload", "✍️ Paste Text"])
    with tab1:
        urls_text = st.text_area("Paste URLs - 1 per line", placeholder="https://en.wikipedia.org/wiki/...\nhttps://example.com/...", height=110, key="urls")
        if st.button("🚀 Add URLs", key="add_urls"):
            urls = [u.strip() for u in urls_text.split("\n") if u.strip().startswith("http")]
            if urls:
                with st.spinner(f"Reading {len(urls)} URLs..."):
                    docs = []
                    for url in urls:
                        try: docs += WebBaseLoader(url).load()
                        except: pass
                    if docs:
                        st.session_state.vectorstore = build_brain_from_docs(docs)
                        st.session_state.doc_name = f"{len(urls)} URLs"
                        st.success(f"Done! {len(urls)} URLs added!")
                        st.balloons()
    with tab2:
        pdf = st.file_uploader("Choose PDF", type=["pdf"], key="pdf_upload")
        if pdf and st.button("Add PDF", key="add_pdf"):
            with open("temp.pdf","wb") as f: f.write(pdf.getbuffer())
            docs = PyPDFLoader("temp.pdf").load()
            st.session_state.vectorstore = build_brain_from_docs(docs)
            st.session_state.doc_name = pdf.name
            st.success(f"{pdf.name} added!")
            st.balloons()
    with tab3:
        pasted_text = st.text_area("Paste Any Text", placeholder="Paste PDF text, notes, anything...", height=130, key="pasted")
        if st.button("✨ Add Text", key="add_text"):
            if pasted_text.strip():
                doc = Document(page_content=pasted_text, metadata={"source": "Pasted Text"})
                st.session_state.vectorstore = build_brain_from_docs([doc])
                st.session_state.doc_name = "Pasted Text"
                st.success("Text added!")

# ========== QUICK ACTIONS - 6 COLOURED, BETTER ==========
st.markdown("### ⚡ Quick Actions")
st.markdown("<p style='font-size:12px; opacity:0.65; margin-top:-6px'>Tap any tool, then ask your question below</p>", unsafe_allow_html=True)
c1,c2,c3,c4,c5,c6 = st.columns(6)
if c1.button("🎯 Quiz"): st.session_state.quiz = True; st.toast("Quiz ON - Ab question pucho")
if c2.button("🗂️ Cards"): st.session_state.flash = True; st.toast("Flashcards ON")
if c3.button("🗺️ Mind Map"): st.session_state.mind = True; st.toast("Mind Map ON")
if c4.button("📝 Summary"): st.session_state.summary = True; st.toast("Summary ON")
if c5.button("💡 Simple"): st.session_state.simple = True; st.toast("Simple Explain ON")
if c6.button("📓 Notes"): st.session_state.notes = True; st.toast("Notes ON")

st.markdown(f"<p style='font-size:12px; opacity:0.7'>Bot: <b>{st.session_state.bot_mode}</b> | Source: <b>{st.session_state.doc_name}</b> | Model: {model_choice}</p>", unsafe_allow_html=True)

for m in st.session_state.chat:
    with st.chat_message(m["role"]):
        st.write(m["content"])

if q := st.chat_input("Ask anything..."):
    st.session_state.chat.append({"role":"user","content":q})
    save_chat("user", q)
    with st.chat_message("user"): st.write(q)
    llm, name = get_llm(model_choice, user_keys)
    context = ""
    if st.session_state.bot_mode == "RAG Bot" and st.session_state.vectorstore:
        try:
            docs = st.session_state.vectorstore.similarity_search(q, k=3)
            context = "\n".join([d.page_content[:2000] for d in docs])
        except: context = ""
    detail_map = {1:"Answer in 1 line",2:"Answer in short",3:"Answer in detail",4:"Answer in very detail with example",5:"Answer like a full chapter with headings"}
    extra = ""
    if st.session_state.get("quiz"): extra = "Make 5 MCQ quiz on this topic, give answers at the end."; st.session_state.quiz=False
    if st.session_state.get("flash"): extra = "Make 5 Flashcards on this topic in Q: A: format."; st.session_state.flash=False
    if st.session_state.get("mind"): extra = "Make a Mind Map of this topic in tree structure."; st.session_state.mind=False
    if st.session_state.get("summary"): extra = "Make a short summary in 5 points."; st.session_state.summary=False
    if st.session_state.get("simple"): extra = "Explain in very simple words like for a 10 year old, with easy example."; st.session_state.simple=False
    if st.session_state.get("notes"): extra = "Make clean exam notes on this topic with headings, definitions, points, and important formulas."; st.session_state.notes=False
    if st.session_state.bot_mode == "LLM Bot":
        prompt = f"You are a helpful universal AI assistant. Answer ANY question. Style: {mode}. Detail: {detail_map[detail]}. {extra}\nQuestion: {q}"
    else:
        prompt = f"You are a RAG assistant. Answer ONLY from the given Context. If answer is not in Context, say 'Not found in your document'. Style: {mode}. Detail: {detail_map[detail]}. {extra}\nContext: {context}\nQuestion: {q}"
    with st.chat_message("assistant"):
        if not llm:
            ans = "Demo Mode - Add your Groq Key in sidebar (Free from console.groq.com)"
            st.write(ans)
        else:
            try: ans = llm.invoke(prompt).content
            except Exception as e: ans = f"Error: {e}. Check your key."
            st.write(ans)
            st.caption(f"Bot: {st.session_state.bot_mode} | Model: {name}")
    st.session_state.chat.append({"role":"assistant","content":ans})
    save_chat("assistant", ans)
