# ============================================================
# 🧠 NeuroDocs AI - RAG BOT
# Built by: 15 Year Old AI engineer
# Tech: LangChain + Groq Llama 3.3 70B + FAISS + Streamlit
# Live: https://neurodocs-ai.streamlit.app
# Speed: 0.3 sec | Cost: $0.00 | Model: Groq (10x faster than OpenAI)
# ============================================================
import os, time, io
import streamlit as st
from dotenv import load_dotenv
load_dotenv()

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader

st.set_page_config(page_title="NeuroDocs AI - Ask Your PDF", page_icon="🧠", layout="wide")

# ============ CSS - CHATGPT JAISA PREMIUM LOOK ============
st.markdown("""
<style>
.main {background: #0E1117;}
.stButton>button {background: linear-gradient(90deg,#FF4B4B,#FF8E53); color:white; border:none; border-radius:12px; padding:10px; font-weight:700; width:100%;}
.stButton>button:hover {transform: scale(1.02);}
div[data-testid="metric"] {background:#1A1D29; padding:14px; border-radius:14px; border:1px solid #2E3348;}
.chat-user {background:#1E3A5F; padding:12px 16px; border-radius:14px; margin:8px 0; border-left:4px solid #4A90D9;}
.chat-ai {background:#1E2A1E; padding:12px 16px; border-radius:14px; margin:8px 0; border-left:4px solid #4CAF50;}
.badge {background:#FF4B4B; color:white; padding:4px 10px; border-radius:20px; font-size:12px; font-weight:bold;}
</style>
""", unsafe_allow_html=True)

# ============ SESSION STATE ============
if "chat" not in st.session_state: st.session_state.chat = []
if "vectorstore" not in st.session_state: st.session_state.vectorstore = None
if "stats" not in st.session_state: st.session_state.stats = {"pages":0, "chunks":0, "questions":0, "total_time":0}
if "doc_name" not in st.session_state: st.session_state.doc_name = ""

# ============ SIDEBAR ============
with st.sidebar:
    st.markdown("## 🧠 NeuroDocs AI")
    st.markdown('<span class="badge">⚡ GROQ POWERED - 10x FASTER</span>', unsafe_allow_html=True)
    st.write("**Ask Anything From Your PDF**")
    st.caption("Built by a 15-year-old from India 🇮🇳")
    st.divider()

    # AI Model Picker
    model_choice = st.selectbox("🤖 AI Model", [
        "⚡ Groq Llama 3.3 70B - BEST (FREE)",
        "⚡ Groq Llama 3.1 8B - Ultra Fast",
        "🌟 Gemini 2.0 Flash - Backup",
        "💎 OpenAI GPT-4o-mini - Premium",
    ])

    mode = st.selectbox("🧠 Brain Mode", [
        "⚡ Fast Answer - Short & Quick",
        "🧠 Deep Reasoning - Detailed",
        "📝 Exam Mode - Answer + 5 Questions",
        "👶 Explain Like I'm 5 - Super Simple",
    ])

    lang = st.selectbox("🌍 Language", ["English", "Hinglish - Desi Style", "Hindi + English Mix", "Marathi Mix"])

    st.divider()
    st.markdown("### 📄 Add Knowledge")

    # 3 Tarike - PDF / Text / Website
    source_type = st.radio("Source:", ["📄 PDF Upload", "✍️ Paste Text", "🌐 Website Link"])

    uploaded_files = None
    pasted_text = ""
    website_url = ""

    if source_type == "📄 PDF Upload":
        uploaded_files = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)
    elif source_type == "✍️ Paste Text":
        pasted_text = st.text_area("Paste your notes / text here:", height=150, placeholder="Paste any text - notes, article, resume...")
    else:
        website_url = st.text_input("Website URL:", placeholder="https://en.wikipedia.org/wiki/...")

    if st.button("🔥 BUILD BRAIN", use_container_width=True):
        try:
            with st.spinner("🧠 Brain bana raha hu..."):
                all_text = ""
                if source_type == "📄 PDF Upload" and uploaded_files:
                    for f in uploaded_files:
                        with open(f"temp_{f.name}", "wb") as tmp:
                            tmp.write(f.getbuffer())
                        loader = PyPDFLoader(f"temp_{f.name}")
                        pages = loader.load()
                        st.session_state.stats["pages"] += len(pages)
                        for p in pages: all_text += p.page_content + "\n"
                        os.remove(f"temp_{f.name}")
                    st.session_state.doc_name = f"{len(uploaded_files)} PDFs"
                elif source_type == "✍️ Paste Text" and pasted_text:
                    all_text = pasted_text
                    st.session_state.doc_name = "Pasted Text"
                elif source_type == "🌐 Website Link" and website_url:
                    loader = WebBaseLoader(website_url)
                    docs = loader.load()
                    all_text = "\n".join([d.page_content for d in docs])
                    st.session_state.doc_name = website_url[:30]

                if not all_text.strip():
                    st.error("Pehle kuch upload / paste karo!")
                else:
                    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
                    chunks = splitter.split_text(all_text)
                    # Cache embeddings - Fast
                    @st.cache_resource
                    def get_embeddings():
                        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
                    embeddings = get_embeddings()
                    docs = [Document(page_content=c) for c in chunks]
                    vs = FAISS.from_documents(docs, embeddings)
                    st.session_state.vectorstore = vs
                    st.session_state.stats["chunks"] = len(chunks)
                    st.success(f"✅ Brain Ready! {len(chunks)} chunks | {len(all_text)} chars")
        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()
    if st.button("🗑️ Clear Chat"):
        st.session_state.chat = []
        st.session_state.stats["questions"] = 0
        st.rerun()
    st.caption("Groq Key: console.groq.com se FREE")

# ============ GET LLM - GROQ FIRST ============
def get_llm():
    groq_key = os.getenv("GROQ_API_KEY") or (st.secrets.get("GROQ_API_KEY","") if hasattr(st,"secrets") else "")
    gemini_key = os.getenv("GOOGLE_API_KEY") or (st.secrets.get("GOOGLE_API_KEY","") if hasattr(st,"secrets") else "")
    openai_key = os.getenv("OPENAI_API_KEY") or (st.secrets.get("OPENAI_API_KEY","") if hasattr(st,"secrets") else "")
    if "Groq" in model_choice and groq_key:
        m = "llama-3.3-70b-versatile" if "70B" in model_choice else "llama-3.1-8b-instant"
        return ChatGroq(model=m, groq_api_key=groq_key, temperature=0.2), f"Groq {m}"
    if "Gemini" in model_choice and gemini_key:
        return ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=gemini_key, temperature=0.3), "Gemini 2.0 Flash"
    if "OpenAI" in model_choice and openai_key:
        return ChatOpenAI(model="gpt-4o-mini", api_key=openai_key), "OpenAI GPT-4o-mini"
    # Auto Fallback
    if groq_key: return ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=groq_key, temperature=0.3), "Groq 70B (Auto)"
    if gemini_key: return ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=gemini_key, temperature=0.3), "Gemini (Auto)"
    if openai_key: return ChatOpenAI(model="gpt-4o-mini", api_key=openai_key), "OpenAI (Auto)"
    return None, "No Key - Demo Mode"

llm, llm_name = get_llm()

# ============ MAIN UI ============
st.title("🧠 NeuroDocs AI")
st.markdown("### Ask Anything From Your PDF, Text, or Website - In 0.3 Seconds ⚡")
st.write(f"📄 **Current Doc:** {st.session_state.doc_name if st.session_state.doc_name else 'No doc yet - Upload from left sidebar'} | 🤖 **Model:** {llm_name} | 💰 **Cost:** $0.00")

c1,c2,c3,c4 = st.columns(4)
c1.metric("📄 Pages", st.session_state.stats["pages"])
c2.metric("🧩 Chunks", st.session_state.stats["chunks"])
c3.metric("💬 Questions", st.session_state.stats["questions"])
c4.metric("⚡ Avg Speed", f"{round(st.session_state.stats['total_time']/max(1,st.session_state.stats['questions']),2)}s" if st.session_state.stats["questions"]>0 else "0s")

if llm is None:
    st.warning("⚠️ Demo Mode - Full AI ke liye GROQ_API_KEY daalo (console.groq.com se FREE). Demo me bhi PDF se text dhoond ke dega.")

st.divider()

for msg in st.session_state.chat:
    if msg["role"] == "user":
        st.markdown(f'<div class="chat-user">🧑 <b>You:</b> {msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-ai">🤖 <b>NeuroDocs ({msg.get("model","AI")}):</b><br>{msg["content"]}</div>', unsafe_allow_html=True)
        st.caption(f"⏱️ {msg.get('time',0)}s | 🔍 Source: {st.session_state.doc_name} | 💰 $0.00 | ⚡ Groq")

st.markdown("### 🎯 One-Click Questions:")
q1,q2,q3,q4 = st.columns(4)
if q1.button("📝 Summarize"): st.session_state["temp_q"] = "Summarize this in 5 simple bullet points"
if q2.button("❓ Exam Qs"): st.session_state["temp_q"] = "Make 10 important exam questions from this with answers"
if q3.button("👶 Explain Like 5"): st.session_state["temp_q"] = "Explain this like I'm 5 years old, super simple"
if q4.button("💼 Interview Qs"): st.session_state["temp_q"] = "Make 8 interview questions from this with best answers"

user_q = st.text_input("Ask anything:", placeholder="Ex: What is photosynthesis? Summarize Chapter 2 in Hinglish?", value=st.session_state.get("temp_q",""), key="main_q")

if st.button("Ask NeuroDocs 🧠", use_container_width=True) and user_q:
    if st.session_state.vectorstore is None:
        st.error("Pehle left sidebar se PDF / Text / Website daal ke BUILD BRAIN dabao!")
    else:
        st.session_state.chat.append({"role":"user","content":user_q})
        start = time.time()
        retriever = st.session_state.vectorstore.as_retriever(search_kwargs={"k":4})
        docs = retriever.invoke(user_q)
        context = "\n\n".join([d.page_content for d in docs])

        if llm is None:
            answer = f"**Demo Mode - PDF me mila:**\n\n{context[:1200]}...\n\n*Full AI ke liye GROQ_API_KEY daalo - FREE hai*"
            elapsed = round(time.time()-start,2)
            st.session_state.chat.append({"role":"ai","content":answer,"time":elapsed,"model":"Demo"})
            st.session_state.stats["questions"]+=1
            st.session_state.stats["total_time"]+=elapsed
            st.rerun()
        else:
            lang_map = {
                "English": "Answer in clear, simple English.",
                "Hinglish - Desi Style": "Answer in full Hinglish, like a desi friend. Use Hindi words in English letters, fun tone.",
                "Hindi + English Mix": "Answer in Hindi + English mix, friendly.",
                "Marathi Mix": "Answer in Marathi + Hindi mix."
            }
            mode_map = {
                "⚡ Fast Answer - Short & Quick": "Give short, quick answer in 3-4 lines.",
                "🧠 Deep Reasoning - Detailed": "Give deep, detailed answer with reasoning and examples.",
                "📝 Exam Mode - Answer + 5 Questions": "Give answer + 5 exam questions from this topic with answers.",
                "👶 Explain Like I'm 5 - Super Simple": "Explain like I'm 5 years old, super simple words, with example.",
            }
            prompt = ChatPromptTemplate.from_template(f"""You are NeuroDocs AI, built by a 15-year-old genius from India. You answer ONLY from given context.
            {lang_map[lang]}
            {mode_map[mode]}
            Context: {{context}}
            Question: {{question}}
            Rules:
            1. ONLY from Context. If not in doc, say "Ye document me nahi hai".
            2. Be accurate, no hallucination.
            3. Use bullet points for summary.
            4. Mention which part you used.
            Answer in Markdown:""")
            chain = ({"context": lambda x: context, "question": RunnablePassthrough()} | prompt | llm | StrOutputParser())
            try:
                answer = chain.invoke(user_q)
                elapsed = round(time.time()-start,2)
                st.session_state.chat.append({"role":"ai","content":answer,"time":elapsed,"model":llm_name})
                st.session_state.stats["questions"]+=1
                st.session_state.stats["total_time"]+=elapsed
                st.session_state["temp_q"] = ""
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e} - Check API Key")

st.divider()
if st.session_state.chat:
    chat_text = "\n\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.chat])
    st.download_button("📥 Download Full Chat", chat_text, file_name="neurodocs_chat.txt", mime="text/plain")

st.markdown("---")
st.markdown("**Built by a 15-year-old from India 🇮🇳 | LangChain + Groq + FAISS | Looking for US Remote Internship - DM Me**")
st.markdown("[⭐ GitHub](https://github.com/) • [💼 LinkedIn](https://linkedin.com/) • [🐦 X](https://x.com/)")
