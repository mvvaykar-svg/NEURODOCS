import streamlit as st
import os
from src.llm import get_llm
from src.brain import build_brain_from_docs, load_saved_brain
from src.memory import init_db, load_chat, save_chat, clear_memory
from langchain_community.document_loaders import WebBaseLoader, PyPDFLoader
from langchain_core.documents import Document

st.set_page_config(page_title="NeuroDocs AI", page_icon="🧠", layout="wide")

# ========== PREMIUM LOOK - FOCUS HERE ==========
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
.stApp { background: linear-gradient(135deg, #050510 0%, #12123A 30%, #1E1E5E 60%, #0F0C29 100%); color: white; font-family: 'Inter', sans-serif; }
h1,h2,h3 { color: white !important; letter-spacing: -0.5px; }
p, span, label { color: #E8E8E8 !important; }

/* Glass Card */
.glass {
    background: rgba(255,255,255,0.07);
    backdrop-filter: blur(15px);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 24px; padding: 22px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.3);
}
/* Big Mode Cards */
.mode-card {
    background: linear-gradient(135deg, rgba(255,107,107,0.2), rgba(255,217,61,0.2));
    border: 2px solid rgba(255,217,61,0.4);
    border-radius: 20px; padding: 16px; text-align: center; cursor: pointer;
}
.mode-card-active {
    background: linear-gradient(135deg, #FF6B6B, #FFD93D);
    color: #111 !important; border-radius: 20px; padding: 16px; text-align: center;
    box-shadow: 0 8px 30px rgba(255,107,107,0.5);
}
.mode-card-active p, .mode-card-active span { color: #111 !important; }

/* Buttons */
.stButton>button {
    background: linear-gradient(90deg, #FF6B6B, #FFD93D);
    color: #111 !important; font-weight: 800; border-radius: 30px; border: none;
    padding: 12px 24px; width: 100%; box-shadow: 0 5px 20px rgba(255,107,107,0.4);
    transition: 0.3s;
}
.stButton>button:hover { transform: translateY(-2px) scale(1.02); box-shadow: 0 10px 30px rgba(255,217,61,0.5); }

/* Inputs */
.stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
    background: #1A1A3A !important; color: white !important; border-radius: 16px !important; border: 1px solid #44447A !important;
}
[data-testid="stSidebar"] { background: #0A0A1E !important; border-right: 1px solid #222; }
div[data-testid="stChatMessage"] { background: rgba(255,255,255,0.07); border-radius: 20px; border: 1px solid rgba(255,255,255,0.1); }
.badge { background: #FFD93D; color: #111; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 800; }
.badge-blue { background: #6BCBFF; color: #111; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

# ========== HEADER ==========
c1, c2 = st.columns([3, 1])
with c1:
    st.markdown("# 🧠 NeuroDocs AI")
    st.markdown("### Your Universal AI Assistant — Ask **Anything**")
    st.markdown("<span class='badge'>✨ LLM BOT</span> &nbsp; <span class='badge-blue'>📚 RAG BOT</span> &nbsp; <span style='opacity:0.7; font-size:13px'>Switch anytime, 1 click</span>", unsafe_allow_html=True)
with c2:
    st.markdown("<div class='glass' style='text-align:center'><h2 style='margin:0'>∞</h2><p style='font-size:12px; margin:0'>Unlimited Questions<br>Any Topic • Any Language</p></div>", unsafe_allow_html=True)

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
for k in ["quiz","flash","mind","summary"]:
    if k not in st.session_state: st.session_state[k] = False

# ========== BOT CHOICE - MAIN FEATURE ==========
st.markdown("### 🤖 Choose Your Bot")
b1, b2 = st.columns(2)
with b1:
    if st.button("🧠 LLM BOT — Answer Any Question", key="llm_btn"):
        st.session_state.bot_mode = "LLM Bot"
        st.rerun()
    if st.session_state.bot_mode == "LLM Bot":
        st.markdown("<div class='mode-card-active'><b>✅ LLM BOT ACTIVE</b><br><span style='font-size:12px'>Like ChatGPT • No file needed • Any question</span></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='mode-card'><b>🧠 LLM BOT</b><br><span style='font-size:12px'>Like ChatGPT • No file needed</span></div>", unsafe_allow_html=True)
with b2:
    if st.button("📚 RAG BOT — Answer From Your File", key="rag_btn"):
        st.session_state.bot_mode = "RAG Bot"
        st.rerun()
    if st.session_state.bot_mode == "RAG Bot":
        st.markdown("<div class='mode-card-active'><b>✅ RAG BOT ACTIVE</b><br><span style='font-size:12px'>Only from YOUR PDF / URL / Text • For Study</span></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='mode-card'><b>📚 RAG BOT</b><br><span style='font-size:12px'>Only from YOUR PDF / URL / Text</span></div>", unsafe_allow_html=True)

# Show status
if st.session_state.bot_mode == "LLM Bot":
    st.info("💡 **LLM Bot Mode:** Ask ANYTHING - Science, Coding, History, Business, Love, Life, Homework, Anything. No need to upload anything.")
else:
    st.warning(f"📚 **RAG Bot Mode:** I will answer ONLY from your document: `{st.session_state.doc_name}`. Add a document below first.")

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
    st.markdown("### 📏 Detail Level")
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

# ========== RAG ONLY - SHOW UPLOAD ONLY IF RAG BOT ==========
if st.session_state.bot_mode == "RAG Bot":
    st.markdown("### 📚 Add Your Study Material (Only for RAG Bot)")
    tab1, tab2, tab3 = st.tabs(["🌐 URLs", "📄 PDF Upload", "✍️ Paste Text"])
    with tab1:
        urls_text = st.text_area("Paste URLs - 1 per line", placeholder="https://en.wikipedia.org/wiki/...\nhttps://example.com/...", height=120, key="urls")
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
                        st.success(f"Done! {len(urls)} URLs added! Now ask questions from them.")
                        st.balloons()
            else: st.warning("Add URLs first!")
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
        pasted_text = st.text_area("Paste Any Text", placeholder="Paste PDF text, notes, anything...", height=150, key="pasted")
        if st.button("✨ Add Text", key="add_text"):
            if pasted_text.strip():
                doc = Document(page_content=pasted_text, metadata={"source": "Pasted Text"})
                st.session_state.vectorstore = build_brain_from_docs([doc])
                st.session_state.doc_name = "Pasted Text"
                st.success("Text added!")

# ========== QUICK ACTIONS ==========
st.markdown("### ⚡ Quick Actions")
c1,c2,c3,c4,c5 = st.columns(5)
if c1.button("🎯 Quiz"): st.session_state.quiz = True; st.toast("Quiz Mode ON")
if c2.button("🗂️ Flashcards"): st.session_state.flash = True; st.toast("Flashcards ON")
if c3.button("🗺️ Mind Map"): st.session_state.mind = True; st.toast("Mind Map ON")
if c4.button("📝 Summary"): st.session_state.summary = True; st.toast("Summary ON")
if c5.button("💡 Explain Simple"): st.toast("Ask simple, I will explain simple")

# ========== CHAT ==========
st.markdown(f"**Bot:** `{st.session_state.bot_mode}` | **Source:** `{st.session_state.doc_name}` | **Model:** `{model_choice}`")
for m in st.session_state.chat:
    with st.chat_message(m["role"]):
        st.write(m["content"])

if q := st.chat_input("Ask ANYTHING... Science, Coding, History, Homework, Life..."):
    st.session_state.chat.append({"role":"user","content":q})
    save_chat("user", q)
    with st.chat_message("user"): st.write(q)

    llm, name = get_llm(model_choice, user_keys)
    context = ""
    # RAG Bot = use document, LLM Bot = ignore document, use full knowledge
    if st.session_state.bot_mode == "RAG Bot" and st.session_state.vectorstore:
        try:
            docs = st.session_state.vectorstore.similarity_search(q, k=3)
            context = "\n".join([d.page_content[:2000] for d in docs])
        except: context = ""
        if not context:
            context = "No document found. Tell user to upload document first."

    detail_map = {1:"Answer in 1 line",2:"Answer in short",3:"Answer in detail",4:"Answer in very detail with example",5:"Answer like a full chapter with headings"}
    extra = ""
    if st.session_state.get("quiz"): extra = "Make 5 MCQ quiz on this topic, give answers at the end."; st.session_state.quiz=False
    if st.session_state.get("flash"): extra = "Make 5 Flashcards on this topic in Q: A: format."; st.session_state.flash=False
    if st.session_state.get("mind"): extra = "Make a Mind Map of this topic in tree structure."; st.session_state.mind=False
    if st.session_state.get("summary"): extra = "Make a short summary in 5 points."; st.session_state.summary=False

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
            st.caption(f"Bot: {st.session_state.bot_mode} | Model: {name} | Source: {st.session_state.doc_name}")
    st.session_state.chat.append({"role":"assistant","content":ans})
    save_chat("assistant", ans)

st.markdown("---")
st.markdown("<p style='text-align:center; opacity:0.6; font-size:12px'>NeuroDocs AI • LLM Bot for Anything • RAG Bot for Your Documents</p>", unsafe_allow_html=True)
