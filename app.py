import streamlit as st
import time
from src.llm import get_llm
from src.brain import build_brain
from src.prompts import build_prompt
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

st.set_page_config(page_title="NeuroDocs AI", page_icon="🧠", layout="wide")

if "chat" not in st.session_state: st.session_state.chat = []
if "vectorstore" not in st.session_state: st.session_state.vectorstore = None
if "stats" not in st.session_state: st.session_state.stats = {"pages":0, "chunks":0, "questions":0, "total_time":0}
if "doc_name" not in st.session_state: st.session_state.doc_name = ""

# SIDEBAR
with st.sidebar:
    st.title("🧠 NeuroDocs AI")
    st.write("Ask Anything From Your PDF")
    st.caption("Built by a 15-year-old from India")
    st.divider()
    model_choice = st.selectbox("AI Model", ["Groq Llama 3.3 70B - BEST (FREE)", "Groq Llama 3.1 8B - Ultra Fast", "Gemini 2.0 Flash - Backup", "OpenAI GPT-4o-mini - Premium"])
    mode = st.selectbox("Brain Mode", ["Fast Answer - Short & Quick", "Deep Reasoning - Detailed", "Exam Mode - Answer + 5 Questions", "Explain Like I'm 5 - Super Simple"])
    lang = st.selectbox("Language", ["English", "Hinglish - Desi Style", "Hindi + English Mix", "Marathi Mix"])
    st.divider()
    st.subheader("Add Knowledge")
    source_type = st.radio("Source:", ["PDF Upload", "Paste Text", "Website Link"])
    uploaded_files = pasted_text = website_url = None
    if source_type == "PDF Upload":
        uploaded_files = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)
    elif source_type == "Paste Text":
        pasted_text = st.text_area("Paste your notes / text here:", height=150)
    else:
        website_url = st.text_input("Website URL:")
    if st.button("BUILD BRAIN", use_container_width=True):
        result = build_brain(source_type, uploaded_files, pasted_text, website_url)
        if result: st.success(result)
    if st.button("Clear Chat"):
        st.session_state.chat = []
        st.session_state.stats["questions"] = 0
        st.rerun()

llm, llm_name = get_llm(model_choice)

# MAIN UI
st.title("🧠 NeuroDocs AI")
st.write(f"Doc: {st.session_state.doc_name or 'No doc yet'} | Model: {llm_name} | Cost: $0.00")

c1,c2,c3,c4 = st.columns(4)
c1.metric("Pages", st.session_state.stats["pages"])
c2.metric("Chunks", st.session_state.stats["chunks"])
c3.metric("Questions", st.session_state.stats["questions"])
avg = round(st.session_state.stats["total_time"]/max(1,st.session_state.stats["questions"]),2) if st.session_state.stats["questions"]>0 else 0
c4.metric("Avg Speed", f"{avg}s")

if llm is None:
    st.warning("Demo Mode - GROQ_API_KEY daalo for full AI. FREE at console.groq.com")

# CHAT HISTORY - No HTML, only Streamlit native
for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ONE CLICK QUESTIONS
st.subheader("One-Click Questions:")
q1,q2,q3,q4 = st.columns(4)
if q1.button("Summarize"): st.session_state["temp_q"] = "Summarize this in 5 simple bullet points"
if q2.button("Exam Qs"): st.session_state["temp_q"] = "Make 10 important exam questions from this with answers"
if q3.button("Explain Like 5"): st.session_state["temp_q"] = "Explain this like I'm 5 years old, super simple"
if q4.button("Interview Qs"): st.session_state["temp_q"] = "Make 8 interview questions from this with best answers"

user_q = st.text_input("Ask anything:", value=st.session_state.get("temp_q",""))

if st.button("Ask NeuroDocs", use_container_width=True) and user_q:
    if st.session_state.vectorstore is None:
        st.error("Pehle sidebar se BUILD BRAIN dabao!")
    else:
        st.session_state.chat.append({"role":"user","content":user_q})
        start = time.time()
        retriever = st.session_state.vectorstore.as_retriever(search_kwargs={"k":4})
        docs = retriever.invoke(user_q)
        context = "\n\n".join([d.page_content for d in docs])
        if llm is None:
            answer = f"Demo Mode - PDF me mila:\n\n{context[:1200]}"
            elapsed = round(time.time()-start,2)
            st.session_state.chat.append({"role":"ai","content":answer})
            st.session_state.stats["questions"]+=1; st.session_state.stats["total_time"]+=elapsed
            st.rerun()
        else:
            prompt = build_prompt(lang, mode)
            chain = ({"context": lambda x: context, "question": RunnablePassthrough()} | prompt | llm | StrOutputParser())
            try:
                answer = chain.invoke(user_q)
                elapsed = round(time.time()-start,2)
                st.session_state.chat.append({"role":"ai","content":answer})
                st.session_state.stats["questions"]+=1; st.session_state.stats["total_time"]+=elapsed
                st.session_state["temp_q"] = ""
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

if st.session_state.chat:
    chat_text = "\n\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.chat])
    st.download_button("Download Full Chat", chat_text, file_name="neurodocs_chat.txt")
st.divider()
st.write("Built by a 15-year-old from India | LangChain + Groq + FAISS | Looking for US Remote Internship")
