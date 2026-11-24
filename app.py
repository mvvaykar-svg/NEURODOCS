import streamlit as st
import time, random, os, requests, base64
from io import BytesIO
from src.llm import get_llm
from src.brain import build_brain_from_docs, load_saved_brain
from src.memory import init_db, load_chat, save_chat, clear_memory
from langchain_community.document_loaders import WebBaseLoader, PyPDFLoader, YoutubeLoader
from langchain_core.documents import Document

st.set_page_config(page_title="NeuroDocs AI", page_icon="🧠", layout="wide")

# --- Prompt Builder ---
def build_prompt(question, mode, detail, lang, extra, bot_mode, context=""):
    detail_map = {1: "Answer in 1 line", 2: "Answer in short", 3: "Answer in detail", 4: "Answer in very detail with example", 5: "Answer like a full chapter with headings"}
    lang_map = {"English": "Answer in English", "Hinglish 🇮🇳": "Answer in Hinglish - Hindi in English letters, casual like a friend", "Hindi 🇮🇳": "Answer in Hindi (Devanagari)", "Simple English": "Answer in very simple English"}
    detail_text = detail_map.get(detail, "Answer in detail")
    lang_text = lang_map.get(lang, "Answer in English")
    if bot_mode == "LLM Bot":
        return f"You are a helpful universal AI assistant. Style: {mode}. Detail: {detail_text}. Language: {lang_text}. {extra}\nQuestion: {question}"
    else:
        return f"You are a RAG assistant. Answer ONLY from the given Context. If answer is not in Context, say 'Not found in your document'. Style: {mode}. Detail: {detail_text}. Language: {lang_text}. {extra}\nContext: {context}\nQuestion: {question}"

# --- VOICE: Speech to Text (Groq Whisper - FREE) ---
def transcribe_voice(audio_bytes, groq_key):
    try:
        files = {"file": ("voice.wav", audio_bytes, "audio/wav")}
        data = {"model": "whisper-large-v3", "language": "en"}
        headers = {"Authorization": f"Bearer {groq_key}"}
        r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files, data=data, timeout=30)
        if r.status_code == 200:
            return r.json().get("text", "")
        else:
            return ""
    except Exception as e:
        return ""

# --- VOICE: Text to Speech (gTTS) ---
def speak_text(text, lang_code="en"):
    try:
        from gtts import gTTS
        clean = text.replace("*","").replace("#","").replace("`","")[:800]
        tts = gTTS(text=clean, lang=lang_code, slow=False)
        buf = BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        return None

def autoplay_audio(audio_bytes):
    b64 = base64.b64encode(audio_bytes).decode()
    st.markdown(f"""<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>""", unsafe_allow_html=True)

# ========== CSS ==========
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&display=swap');
.stApp { background: radial-gradient(circle at 10% 10%, rgba(124,58,237,0.35) 0%, transparent 40%), radial-gradient(circle at 90% 20%, rgba(0,210,255,0.25) 0%, transparent 40%), linear-gradient(160deg, #0A0618 0%, #140B2E 35%, #1A0F3D 65%, #050510 100%); background-attachment: fixed; color: white; font-family: 'Inter', sans-serif; }
h1,h2,h3 { color: white !important; }
p, span, label { color: #E8E8E8 !important; }
.block-container { padding-top: 0rem !important; padding-left: 1rem !important; padding-right: 1rem !important; max-width: 100% !important; overflow-x: hidden !important; }
.title-box { margin-top: 62px !important; margin-bottom: 10px !important; padding: 22px 18px 16px 18px !important; background: rgba(255,255,255,0.07) !important; border: 1px solid rgba(255,255,255,0.14) !important; border-radius: 24px !important; text-align: center !important; max-width: 100% !important; overflow: hidden !important; }
.main-title { font-size: clamp(30px, 8vw, 46px) !important; font-weight: 900 !important; line-height: 1.05 !important; background: linear-gradient(90deg, #FF6B6B, #FFD93D, #00D2FF, #A78BFA); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0px !important; padding: 0px !important; word-break: break-word !important; white-space: normal !important; overflow-wrap: break-word !important; max-width: 100% !important; display: block !important; text-align: center !important; }
.sub-title { font-size: clamp(13px, 3.5vw, 15px); opacity: 0.85; margin-top: 8px; word-break: break-word !important; white-space: normal !important; max-width: 100% !important; line-height: 1.5; text-align: center !important; }
.badge-row { display: flex; flex-wrap: wrap; gap: 6px; max-width: 100%; justify-content: center !important; margin-top: 12px !important; }
.glass { background: rgba(255,255,255,0.06); backdrop-filter: blur(18px); border: 1px solid rgba(255,255,255,0.14); border-radius: 22px; padding: 16px; margin-bottom: 14px; max-width: 100% !important; overflow-wrap: break-word !important; }
.voice-box { background: linear-gradient(135deg, #7C3AED, #DB2777) !important; border-radius: 22px; padding: 16px; text-align: center; margin-bottom: 14px; }
.stButton>button { background: linear-gradient(90deg, #FF6B6B, #FFD93D); color: #111 !important; font-weight: 800; border-radius: 30px; border: none; padding: 13px 18px !important; width: 100%; margin-bottom: 10px !important; white-space: normal !important; }
div[data-testid="column"] .stButton>button { padding: 10px 6px !important; font-size: 12.5px !important; border-radius: 16px !important; color: white !important; box-shadow: 0 6px 18px rgba(0,0,0,0.3) !important; white-space: normal !important; }
div[data-testid="column"]:nth-of-type(1) .stButton>button { background: linear-gradient(135deg, #7C3AED, #A78BFA) !important; }
div[data-testid="column"]:nth-of-type(2) .stButton>button { background: linear-gradient(135deg, #2563EB, #00D2FF) !important; }
div[data-testid="column"]:nth-of-type(3) .stButton>button { background: linear-gradient(135deg, #059669, #34D399) !important; }
div[data-testid="column"]:nth-of-type(4) .stButton>button { background: linear-gradient(135deg, #EA580C, #FBBF24) !important; }
div[data-testid="column"]:nth-of-type(5) .stButton>button { background: linear-gradient(135deg, #DB2777, #F472B6) !important; }
div[data-testid="column"]:nth-of-type(6) .stButton>button { background: linear-gradient(135deg, #0F766E, #2DD4BF) !important; color: #06110F !important; }
.stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div { background: #171233 !important; color: white !important; border-radius: 16px !important; border: 1px solid rgba(255,255,255,0.15) !important; }
[data-testid="stSidebar"] { background: #0A0618 !important; }
div[data-testid="stChatMessage"] { background: rgba(255,255,255,0.07); border-radius: 20px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 10px !important; padding: 14px !important; }
.badge { background: #FFD93D; color: #111; padding: 6px 13px; border-radius: 20px; font-size: 12px; font-weight: 800; white-space: nowrap; }
.badge-blue { background: #6BCBFF; color: #111; padding: 6px 13px; border-radius: 20px; font-size: 12px; font-weight: 800; white-space: nowrap; }
.badge-purple { background: #A78BFA; color: #111; padding: 6px 13px; border-radius: 20px; font-size: 12px; font-weight: 800; white-space: nowrap; }
[data-testid="stChatInput"] { background: #171233 !important; border-radius: 24px !important; border: 1px solid rgba(255,255,255,0.25) !important; }
</style>
""", unsafe_allow_html=True)

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
if "user" not in st.session_state:
    st.session_state.user = None
if "folders" not in st.session_state:
    st.session_state.folders = {"Physics": [], "Maths": [], "Coding": [], "General": []}
if "current_folder" not in st.session_state:
    st.session_state.current_folder = "General"
if "flash_deck" not in st.session_state:
    st.session_state.flash_deck = []
if "exam" not in st.session_state:
    st.session_state.exam = None
if "analytics" not in st.session_state:
    st.session_state.analytics = {"questions": 0, "quizzes": 0, "notes": 0, "summaries": 0}
if "voice_on" not in st.session_state:
    st.session_state.voice_on = True
if "last_voice_id" not in st.session_state:
    st.session_state.last_voice_id = None
for k in ["quiz", "flash", "mind", "summary", "simple", "notes"]:
    if k not in st.session_state:
        st.session_state[k] = False

# ========== LOGIN ==========
if not st.session_state.user:
    st.markdown("""<div class='title-box'><div class='main-title'>🧠 NeuroDocs AI</div><div class='sub-title'>Learn Anything, From Anywhere — Your Personal AI Study Buddy</div><div class='badge-row'><span class='badge'>✨ LLM BOT</span> <span class='badge-blue'>📚 RAG BOT</span> <span class='badge-purple'>🎯 6 SMART TOOLS</span></div></div>""", unsafe_allow_html=True)
    st.markdown("<div class='glass'><h3>👋 Welcome Viraj to NeuroDocs AI</h3><p>ChatGPT + Your PDF + Exam Helper — All In One App. No signup needed, just enter your name.</p></div>", unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    with c1:
        name = st.text_input("Your Name", placeholder="e.g. Viraj")
        if st.button("🚀 Start Learning - It's Free"):
            if name.strip():
                st.session_state.user = name.strip()
                st.rerun()
            else:
                st.warning("Please enter your name")
    with c2:
        st.markdown("<div class='glass'>⭐ <b>Why NeuroDocs?</b><br>✅ 100% Free<br>✅ Ask Anything<br>✅ PDF + YouTube + Notes<br>✅ Quiz + Flashcards<br>✅ 🎙️ Voice Talk</div>", unsafe_allow_html=True)
    st.markdown("### 🎬 How it works - 30 Sec Demo")
    st.markdown("1️⃣ Choose Bot → 2️⃣ Tap Mic & Speak → 3️⃣ AI Bolke Jawab Dega → 4️⃣ Get Quiz / Notes Instantly")
    st.stop()

# ========== HEADER ==========
st.markdown(f"""<div class='title-box'><div class='main-title'>🧠 NeuroDocs AI</div><div class='sub-title'>Welcome back, <b>{st.session_state.user}</b> 👋 — Ask <b>Anything</b> • Learn From <b>Your Files</b></div><div class='badge-row'><span class='badge'>✨ LLM BOT</span> <span class='badge-blue'>📚 RAG BOT</span> <span class='badge-purple'>🎯 6 SMART TOOLS</span> <span class='badge'>🎥 YOUTUBE</span></div></div>""", unsafe_allow_html=True)

# ========== SIDEBAR ==========
with st.sidebar:
    st.markdown(f"## 👋 Hi, {st.session_state.user}")
    if st.button("🚪 Logout"):
        st.session_state.user = None
        st.rerun()
    st.markdown("## 🔑 Your API Key")
    groq_k = st.text_input("Groq Key (Free)", type="password", placeholder="gsk_...")
    gemini_k = st.text_input("Gemini Key", type="password", placeholder="AIza...")
    openai_k = st.text_input("OpenAI Key", type="password", placeholder="sk-...")
    st.markdown("[Get Free Groq Key →](https://console.groq.com)")
    st.divider()
    st.markdown("## 🎙️ Voice Settings")
    st.session_state.voice_on = st.toggle("🔊 AI Voice Reply ON", value=st.session_state.voice_on)
    voice_lang = st.selectbox("AI Voice Language", ["Hinglish / Hindi 🇮🇳", "English", "Hindi"])
    voice_speed = st.selectbox("Voice Style", ["Normal", "Slow - For Learning", "Fast"])
    st.divider()
    st.markdown("## ⚙️ Settings")
    model_choice = st.selectbox("Choose Model", ["OpenAI GPT-OSS 20B - Fast (FREE)", "OpenAI GPT-OSS 120B - Smart (FREE)", "Gemini 2.0 Flash", "OpenAI GPT-4o-mini"])
    detail = st.slider("Detail", 1, 5, 3)
    detail_labels = {1: "1 - One Line", 2: "2 - Short", 3: "3 - Detailed", 4: "4 - Full Example", 5: "5 - Full Chapter"}
    st.success(f"**{detail_labels[detail]}**")
    lang = st.selectbox("🌐 Language", ["English", "Hinglish 🇮🇳", "Hindi 🇮🇳", "Simple English"])
    mode = st.radio("🎭 Style", ["Normal", "Explain Like 5 Year Old 👶", "Exam Mode 📝", "Simple English 🇬🇧"], horizontal=True)
    st.divider()
    st.markdown("## 📁 Folders")
    st.session_state.current_folder = st.selectbox("Current Folder", list(st.session_state.folders.keys()))
    new_folder = st.text_input("New Folder Name")
    if st.button("➕ Create Folder") and new_folder.strip():
        st.session_state.folders[new_folder.strip()] = []
        st.rerun()
    search_q = st.text_input("🔍 Search Chat", placeholder="Search old chats...")
    if search_q:
        hits = [c for c in st.session_state.chat if search_q.lower() in c["content"].lower()]
        st.write(f"Found {len(hits)} chats")
        for h in hits[:3]:
            st.caption(h["content"][:120])
    st.divider()
    st.markdown("## 📊 Your Analytics")
    a = st.session_state.analytics
    st.metric("Questions Asked", a["questions"])
    st.metric("Quizzes Made", a["quizzes"])
    st.metric("Notes Made", a["notes"])
    st.metric("Summaries", a["summaries"])
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

# ========== MAIN TABS ==========
tab_chat, tab_yt, tab_exam, tab_plan, tab_cards = st.tabs(["💬 Chat", "🎥 YouTube", "⏱️ Mock Test", "📅 Study Planner", "🗂️ Flashcards"])

with tab_yt:
    st.markdown("### 🎥 YouTube Video Summarizer")
    yt_url = st.text_input("YouTube Link", placeholder="https://youtube.com/watch?v=...")
    if st.button("✨ Summarize Video") and yt_url:
        with st.spinner("Listening to video..."):
            try:
                loader = YoutubeLoader.from_youtube_url(yt_url, add_video_info=True)
                docs = loader.load()
                text = docs[0].page_content[:8000] if docs else ""
                st.session_state.vectorstore = build_brain_from_docs([Document(page_content=text, metadata={"source": yt_url})])
                st.session_state.doc_name = f"YouTube: {yt_url[:40]}"
                st.success("Video loaded! Now ask in Chat tab")
                st.write(text[:1500])
            except Exception as e:
                st.error(f"Try another video. Error: {e}")

with tab_exam:
    st.markdown("### ⏱️ Mock Test - Exam Mode")
    topic = st.text_input("Test Topic", placeholder="e.g. Photosynthesis, Python, History", key="exam_topic")
    if st.button("🎯 Start 5 MCQ Test - 5 Min") and topic:
        st.session_state.exam = {"topic": topic, "start": time.time()}
        st.info("Test started! Go to Chat tab, tap 🎯 Quiz and ask your topic.")
        st.balloons()
    if st.session_state.exam:
        elapsed = int(time.time() - st.session_state.exam["start"])
        left = max(0, 300 - elapsed)
        st.progress(left / 300)
        st.write(f"⏰ Time Left: {left//60}:{left%60:02d} | Topic: {st.session_state.exam['topic']}")

with tab_plan:
    st.markdown("### 📅 7-Day Study Planner")
    syllabus = st.text_input("Your Syllabus / Exam", placeholder="e.g. Class 10 Science - 5 Chapters, Exam in 7 days", key="plan_input")
    if st.button("🪄 Make My Plan") and syllabus:
        llm, _ = get_llm(model_choice, user_keys)
        if llm:
            prompt = f"Make a 7-day study plan for: {syllabus}. Language: {lang}. Give Day 1 to Day 7, each day: Topic, 2 Tasks, 30 min Revision, 1 Quiz. Keep simple."
            plan = llm.invoke(prompt).content
            st.markdown(plan)
            st.download_button("⬇️ Download Plan", plan, file_name="Study-Plan.txt")
        else:
            st.warning("Add Groq Key in sidebar for AI Plan")

with tab_cards:
    st.markdown("### 🗂️ My Flashcards")
    if st.session_state.flash_deck:
        idx = st.session_state.get("card_idx", 0) % len(st.session_state.flash_deck)
        card = st.session_state.flash_deck[idx]
        st.markdown(f"<div class='glass'><h3>{card}</h3></div>", unsafe_allow_html=True)
        if st.button("➡️ Next Card"):
            st.session_state.card_idx = idx + 1
            st.rerun()
        if st.button("🔁 Shuffle"):
            random.shuffle(st.session_state.flash_deck)
            st.rerun()
    else:
        st.info("No cards yet. Go to Chat -> Tap 🗂️ Cards -> Ask any topic.")
    st.caption(f"Total Cards: {len(st.session_state.flash_deck)}")

with tab_chat:
    st.markdown("### 🤖 Choose Your Bot")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Use LLM Bot", key="llm_btn"):
            st.session_state.bot_mode = "LLM Bot"
            st.rerun()
        st.markdown(f"<div style='text-align:center; font-weight:700'>🧠 LLM BOT {'✅ ACTIVE' if st.session_state.bot_mode == 'LLM Bot' else ''}</div>", unsafe_allow_html=True)
    with col2:
        if st.button("Use RAG Bot", key="rag_btn"):
            st.session_state.bot_mode = "RAG Bot"
            st.rerun()
        st.markdown(f"<div style='text-align:center; font-weight:700'>📚 RAG BOT {'✅ ACTIVE' if st.session_state.bot_mode == 'RAG Bot' else ''}</div>", unsafe_allow_html=True)
    if st.session_state.bot_mode == "LLM Bot":
        st.info("💡 **LLM Bot:** Ask ANYTHING. No file needed.")
    else:
        st.warning(f"📚 **RAG Bot:** Only from: `{st.session_state.doc_name}`")

    if st.session_state.bot_mode == "RAG Bot":
        st.markdown("### 📚 Add Your Study Material")
        t1, t2, t3, t4 = st.tabs(["🌐 URLs", "📄 PDFs", "✍️ Text", "🖼️ Image Notes"])
        with t1:
            urls_text = st.text_area("Paste URLs - 1 per line", placeholder="https://en.wikipedia.org/wiki/...", height=110, key="urls")
            if st.button("🚀 Add URLs", key="add_urls"):
                urls = [u.strip() for u in urls_text.split("\n") if u.strip().startswith("http")]
                if urls:
                    docs = []
                    for url in urls:
                        try:
                            docs += WebBaseLoader(url).load()
                        except:
                            pass
                    if docs:
                        st.session_state.vectorstore = build_brain_from_docs(docs)
                        st.session_state.doc_name = f"{len(urls)} URLs"
                        st.success("Done!")
                        st.balloons()
        with t2:
            pdfs = st.file_uploader("Choose PDFs - Multiple Allowed", type=["pdf"], accept_multiple_files=True, key="pdf_upload")
            if pdfs and st.button("Add PDFs", key="add_pdf"):
                all_docs = []
                for pdf in pdfs:
                    with open("temp.pdf", "wb") as f:
                        f.write(pdf.getbuffer())
                    all_docs += PyPDFLoader("temp.pdf").load()
                st.session_state.vectorstore = build_brain_from_docs(all_docs)
                st.session_state.doc_name = f"{len(pdfs)} PDFs"
                st.success(f"{len(pdfs)} PDFs added!")
                st.balloons()
        with t3:
            pasted = st.text_area("Paste Any Text", placeholder="Paste PDF text, notes...", height=130, key="pasted")
            if st.button("✨ Add Text", key="add_text") and pasted.strip():
                st.session_state.vectorstore = build_brain_from_docs([Document(page_content=pasted, metadata={"source": "Pasted"})])
                st.session_state.doc_name = "Pasted Text"
                st.success("Text added!")
        with t4:
            img = st.file_uploader("Upload Photo of Handwritten Notes", type=["png", "jpg", "jpeg"], key="img_upload")
            if img:
                st.image(img, caption="Your Notes Photo")
                st.info("📸 Photo uploaded! Now ask in chat: 'Explain what is written in this image'")

    st.markdown("### ⚡ Quick Actions")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    if c1.button("🎯 Quiz"):
        st.session_state.quiz = True
        st.toast("Quiz ON")
    if c2.button("🗂️ Cards"):
        st.session_state.flash = True
        st.toast("Flashcards ON")
    if c3.button("🗺️ Mind Map"):
        st.session_state.mind = True
        st.toast("Mind Map ON")
    if c4.button("📝 Summary"):
        st.session_state.summary = True
        st.toast("Summary ON")
    if c5.button("💡 Simple"):
        st.session_state.simple = True
        st.toast("Simple ON")
    if c6.button("📓 Notes"):
        st.session_state.notes = True
        st.toast("Notes ON")
    st.markdown(f"<p style='font-size:12px; opacity:0.7'>Bot: <b>{st.session_state.bot_mode}</b> | Source: <b>{st.session_state.doc_name}</b> | Folder: <b>{st.session_state.current_folder}</b></p>", unsafe_allow_html=True)

    # ========== 🎙️ VOICE TALK MODE - DIRECT BAAT ==========
    st.markdown("""<div class='voice-box'><h3 style='margin:0'>🎙️ Voice Talk Mode</h3><p style='margin:4px 0 0 0; font-size:13px;'>Mic dabao → Bolo → AI sunega + bolke jawab dega</p></div>""", unsafe_allow_html=True)
    voice_col1, voice_col2 = st.columns([1, 1])
    with voice_col1:
        if st.button("🎙️ Start Voice Talk", key="voice_start"):
            st.session_state.voice_on = True
            st.toast("Voice Talk ON - Ab bolo!")
    with voice_col2:
        if st.button("🔇 Voice OFF", key="voice_stop"):
            st.session_state.voice_on = False
            st.toast("Voice OFF")
    st.markdown(f"**Voice Status:** {'🟢 ON - AI bolega' if st.session_state.voice_on else '🔴 OFF - Sirf text'}")

    audio = st.audio_input("🎤 Yaha bolo - Tap to speak")
    voice_question = None
    if audio is not None:
        audio_bytes = audio.read()
        # Same audio dubara process na ho isliye check
        audio_id = hash(audio_bytes[:5000]) if len(audio_bytes) > 5000 else hash(audio_bytes)
        if st.session_state.last_voice_id != audio_id:
            st.session_state.last_voice_id = audio_id
            if not groq_k:
                st.warning("⚠️ Voice ke liye Groq Key chahiye - Sidebar me daalo (Free)")
            else:
                with st.spinner("🎧 Sun raha hu..."):
                    voice_question = transcribe_voice(audio_bytes, groq_k)
                if voice_question:
                    st.success(f"🎤 Tumne bola: **{voice_question}**")
                else:
                    st.error("Aawaz samajh nahi aayi, dobara bolo")

    for m in st.session_state.chat:
        with st.chat_message(m["role"]):
            st.write(m["content"])

    # Voice ya Text - dono se question aayega
    q = voice_question
    text_q = st.chat_input("Ask anything... ya mic se bolo 👆")
    if text_q:
        q = text_q

    if q:
        st.session_state.chat.append({"role": "user", "content": q})
        save_chat("user", q)
        st.session_state.analytics["questions"] += 1
        with st.chat_message("user"):
            st.write(q)
        llm, name = get_llm(model_choice, user_keys)
        context = ""
        if st.session_state.bot_mode == "RAG Bot" and st.session_state.vectorstore:
            try:
                docs = st.session_state.vectorstore.similarity_search(q, k=3)
                context = "\n".join([d.page_content[:2000] for d in docs])
            except:
                context = ""
        extra = ""
        if st.session_state.get("quiz"):
            extra = "Make 5 MCQ quiz, give answers at end."
            st.session_state.quiz = False
            st.session_state.analytics["quizzes"] += 1
        if st.session_state.get("flash"):
            extra = "Make 5 Flashcards in Q: A: format."
            st.session_state.flash = False
        if st.session_state.get("mind"):
            extra = "Make a Mind Map in tree structure."
            st.session_state.mind = False
        if st.session_state.get("summary"):
            extra = "Make short summary in 5 points."
            st.session_state.summary = False
            st.session_state.analytics["summaries"] += 1
        if st.session_state.get("simple"):
            extra = "Explain in very simple words like for 10 year old, easy example."
            st.session_state.simple = False
        if st.session_state.get("notes"):
            extra = "Make clean exam notes with headings, definitions, points, formulas."
            st.session_state.notes = False
            st.session_state.analytics["notes"] += 1
        # Voice ke liye short jawab - taaki bolne me fast ho
        if voice_question:
            extra += " Keep answer SHORT, 4-5 lines only, speaking style, like talking to friend."
        prompt = build_prompt(q, mode, detail, lang, extra, st.session_state.bot_mode, context)
        with st.chat_message("assistant"):
            if not llm:
                ans = "Demo Mode - Add Groq Key in sidebar (Free from console.groq.com)"
                st.write(ans)
            else:
                try:
                    ans = llm.invoke(prompt).content
                except Exception as e:
                    ans = f"Error: {e}. Check key."
                st.write(ans)
                st.caption(f"Bot: {st.session_state.bot_mode} | Model: {name} | Lang: {lang}")
                # 🔊 AI BOLEGA - AUTO PLAY
                if st.session_state.voice_on and voice_question:
                    with st.spinner("🔊 AI bol raha hai..."):
                        tts_lang = "hi" if "Hindi" in voice_lang or "Hinglish" in voice_lang else "en"
                        audio_out = speak_text(ans, lang_code=tts_lang)
                        if audio_out:
                            st.audio(audio_out, format="audio/mp3")
                            autoplay_audio(audio_out)
                            st.success("🔊 AI ne bolke jawab diya - Volume ON karo!")
                if "Q:" in ans and "A:" in ans:
                    lines = [l for l in ans.split("\n") if l.strip().startswith("Q:") or l.strip().startswith("A:")]
                    st.session_state.flash_deck.extend(lines[:10])
                st.markdown("---")
                st.markdown("**📤 Share / Export This Answer**")
                st.code(f"https://neurodocs.streamlit.app/share/{abs(hash(q)) % 100000}", language="text")
                st.download_button("⬇️ Export This Answer as Notes", ans, file_name=f"NeuroDocs-{q[:20].replace(' ', '_')}.txt", key=f"dl_{len(st.session_state.chat)}")
        st.session_state.chat.append({"role": "assistant", "content": ans})
        save_chat("assistant", ans)
        st.session_state.folders[st.session_state.current_folder].append(q)
        st.rerun()
