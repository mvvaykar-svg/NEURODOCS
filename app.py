import streamlit as st
import time, random, os, requests, base64, re, sqlite3, hashlib
from io import BytesIO
from src.llm import get_llm
from src.brain import build_brain_from_docs, load_saved_brain
from src.memory import init_db, load_chat, save_chat, clear_memory
from langchain_community.document_loaders import WebBaseLoader, PyPDFLoader
from langchain_core.documents import Document

st.set_page_config(page_title="NeuroDocs AI", page_icon="🧠", layout="wide")

# ---------- LOGIN DB ----------
def get_user_db():
    conn = sqlite3.connect("users.db", check_same_thread=False)
    conn.execute("CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY, pin TEXT)")
    return conn
user_db = get_user_db()

def build_prompt(question, mode, detail, lang, extra, bot_mode, context=""):
    detail_map = {1: "Answer in 1 line", 2: "Answer in short", 3: "Answer in detail", 4: "Answer in very detail with example", 5: "Answer like a full chapter with headings"}
    lang_map = {"English": "Answer in English", "Hinglish": "Answer in Hinglish - Hindi in English letters, casual like a friend", "Hindi": "Answer in Hindi (Devanagari)", "Simple English": "Answer in very simple English"}
    detail_text = detail_map.get(detail, "Answer in detail")
    lang_text = lang_map.get(lang, "Answer in English")
    if bot_mode == "LLM Bot":
        return f"You are NeuroDocs AI, a friendly expert tutor. Never give 1-word answer. Always explain with examples. Style: {mode}. Detail: {detail_text}. Language: {lang_text}. {extra}\nQuestion: {question}"
    else:
        return f"You are a RAG assistant. Answer ONLY from Context. If not found, say 'Not found in your document, but here is related help'. Never stop in 1 word. Explain fully. Style: {mode}. Detail: {detail_text}. Language: {lang_text}. {extra}\nContext: {context}\nQuestion: {question}"

def transcribe_voice(audio_bytes, groq_key):
    try:
        files = {"file": ("voice.wav", audio_bytes, "audio/wav")}
        data = {"model": "whisper-large-v3", "language": "en"}
        headers = {"Authorization": f"Bearer {groq_key}"}
        r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files, data=data, timeout=30)
        return r.json().get("text", "") if r.status_code == 200 else ""
    except: return ""

def speak_text(text, lang_code="en"):
    try:
        from gtts import gTTS
        clean = text.replace("*","").replace("#","").replace("`","")[:1000]
        tts = gTTS(text=clean, lang=lang_code, slow=False)
        buf = BytesIO(); tts.write_to_fp(buf); buf.seek(0); return buf.read()
    except: return None

def autoplay_audio(audio_bytes):
    b64 = base64.b64encode(audio_bytes).decode()
    st.markdown(f"""<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>""", unsafe_allow_html=True)

# ---------- NEW PREMIUM COLOUR THEME ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
.stApp { background: #070B1A; color: white; font-family: 'Plus Jakarta Sans', sans-serif; }
h1,h2,h3 { color: white !important; }
p, span, label { color: #E6E8F0 !important; }
.block-container { padding-top: 0rem !important; max-width: 100% !important; }
/* FRONT PAGE HERO - NEW COLOUR */
.title-box { margin-top: 62px !important; padding: 28px 20px !important; background: linear-gradient(135deg, #FF5A8A 0%, #FF9A3D 35%, #7C5CFF 70%, #00E5FF 100%) !important; border-radius: 26px !important; text-align: center !important; box-shadow: 0 20px 50px rgba(124,92,255,0.4); }
.main-title { font-size: clamp(32px, 8vw, 50px) !important; font-weight: 800 !important; color: white !important; margin: 0px !important; text-shadow: 0 4px 20px rgba(0,0,0,0.3); }
.sub-title { font-size: 15px !important; color: white !important; opacity: 0.95; margin-top: 8px; }
/* CARDS */
.glass { background: linear-gradient(135deg, #141A33 0%, #1B2247 100%) !important; border: 1px solid rgba(255,255,255,0.12) !important; border-radius: 22px; padding: 18px; margin-bottom: 14px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
.glass-green { background: linear-gradient(135deg, #0F3D2E, #12B981) !important; border-radius: 22px; padding: 18px; margin-bottom: 14px; color: white; }
.glass-orange { background: linear-gradient(135deg, #4A1E00, #FF7A00) !important; border-radius: 22px; padding: 18px; margin-bottom: 14px; color: white; }
.voice-box { background: linear-gradient(135deg, #FF5A8A, #7C5CFF) !important; border-radius: 22px; padding: 16px; text-align: center; margin-bottom: 14px; }
.stButton>button { background: linear-gradient(90deg, #00E5FF, #7C5CFF) !important; color: white !important; font-weight: 800; border-radius: 30px; border: none; padding: 13px 18px !important; width: 100%; }
div[data-testid="column"] .stButton>button { padding: 13px 6px !important; font-size: 13px !important; border-radius: 16px !important; min-height: 56px !important; color: white !important; }
div[data-testid="column"]:nth-of-type(1) .stButton>button { background: linear-gradient(135deg, #FF5A8A, #FF9A3D) !important; }
div[data-testid="column"]:nth-of-type(2) .stButton>button { background: linear-gradient(135deg, #00C6FF, #0072FF) !important; }
div[data-testid="column"]:nth-of-type(3) .stButton>button { background: linear-gradient(135deg, #00D68F, #00A651) !important; }
.stTextInput>div>div>input, .stTextArea>div>div>textarea { background: #131A36 !important; color: white !important; border-radius: 16px !important; border: 1px solid rgba(255,255,255,0.15) !important; }
[data-testid="stSidebar"] { background: #0A0F24 !important; border-right: 1px solid rgba(255,255,255,0.08); }
div[data-testid="stChatMessage"] { background: #141A33; border-radius: 20px; border: 1px solid rgba(255,255,255,0.1); }
.badge { background: white; color: #111; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 800; }
.badge-blue { background: #00E5FF; color: #111; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 800; }
.badge-purple { background: #FFD93D; color: #111; padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 800; }
.stat-box { background: #141A33; border-radius: 16px; padding: 14px; text-align: center; border: 1px solid rgba(255,255,255,0.1); }
</style>
""", unsafe_allow_html=True)

# ---------- SESSION ----------
if "chat" not in st.session_state:
    init_db(); st.session_state.chat = load_chat()
if "vectorstore" not in st.session_state: st.session_state.vectorstore = load_saved_brain()
if "doc_name" not in st.session_state: st.session_state.doc_name = "No Document"
if "bot_mode" not in st.session_state: st.session_state.bot_mode = "LLM Bot"
if "user" not in st.session_state: st.session_state.user = None
if "folders" not in st.session_state: st.session_state.folders = {"Physics": [], "Maths": [], "Coding": [], "General": []}
if "current_folder" not in st.session_state: st.session_state.current_folder = "General"
if "flash_deck" not in st.session_state: st.session_state.flash_deck = ["Q: What is Photosynthesis? A: Process by which plants make food using sunlight", "Q: What is H2O? A: Water", "Q: Capital of India? A: New Delhi"]
if "exam" not in st.session_state: st.session_state.exam = None
if "analytics" not in st.session_state: st.session_state.analytics = {"questions": 12, "quizzes": 4, "notes": 6, "summaries": 8, "xp": 240, "streak": 3}
if "voice_on" not in st.session_state: st.session_state.voice_on = True
if "pending_action" not in st.session_state: st.session_state.pending_action = None
for k in ["quiz", "flash", "mind", "summary", "simple", "notes", "quick_prompt"]:
    if k not in st.session_state: st.session_state[k] = False if k != "quick_prompt" else ""

# ---------- LOGIN ----------
if not st.session_state.user:
    st.markdown("""<div class='title-box'><div class='main-title'>🧠 NeuroDocs AI</div><div class='sub-title'>Your Personal AI Study Buddy — Learn Faster, Remember Longer</div><div style='margin-top:14px; display:flex; gap:8px; justify-content:center; flex-wrap:wrap;'><span class='badge'>✨ LLM BOT</span><span class='badge-blue'>📚 RAG BOT</span><span class='badge-purple'>🎯 6 SMART TOOLS</span></div></div>""", unsafe_allow_html=True)
    # NEW: Dashboard preview on front page - not empty
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown("<div class='stat-box'><h2>12K+</h2><p>Students Learning</p></div>", unsafe_allow_html=True)
    with c2: st.markdown("<div class='stat-box'><h2>4.9 ⭐</h2><p>Rating</p></div>", unsafe_allow_html=True)
    with c3: st.markdown("<div class='stat-box'><h2>100%</h2><p>Free Forever</p></div>", unsafe_allow_html=True)
    with c4: st.markdown("<div class='stat-box'><h2>6</h2><p>Smart Tools</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='glass'><h3>👋 Welcome to NeuroDocs AI</h3><p>ChatGPT + Your PDF + Exam Helper — All In One. First time? Create a PIN. Next time login with same PIN.</p></div>", unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    with c1:
        name = st.text_input("Your Name", placeholder="e.g. Viraj")
        pin = st.text_input("Create / Enter 4 Digit PIN", type="password", placeholder="e.g. 1234", max_chars=4)
        if st.button("🚀 Login / Signup - It's Free"):
            if name.strip() and len(pin)==4:
                hashed = hashlib.sha256(pin.encode()).hexdigest()
                row = user_db.execute("SELECT * FROM users WHERE name=?", (name.strip(),)).fetchone()
                if row:
                    if row[1]==hashed: st.session_state.user = name.strip(); st.rerun()
                    else: st.error("Wrong PIN! Try another name or enter correct PIN")
                else:
                    user_db.execute("INSERT INTO users VALUES (?,?)", (name.strip(), hashed)); user_db.commit()
                    st.session_state.user = name.strip(); st.success("Account Created!"); st.rerun()
            else: st.warning("Please enter Name and 4 digit PIN")
    with c2:
        st.markdown("<div class='glass-green'>⭐ <b>Why NeuroDocs?</b><br>✅ 100% Free<br>✅ Ask Anything<br>✅ PDF + YouTube + Notes<br>✅ Quiz + Flashcards<br>✅ Voice Talk<br>✅ Permanent Memory</div>", unsafe_allow_html=True)
    st.markdown("### 🎬 How it works")
    st.markdown("1️⃣ Login → 2️⃣ Choose Bot → 3️⃣ Tap Mic & Speak → 4️⃣ Get Quiz / Notes Instantly")
    st.markdown("<div class='glass-orange'><b>🔥 Daily Challenge:</b> What is the powerhouse of the cell? — Answer in Chat to earn +20 XP!</div>", unsafe_allow_html=True)
    st.stop()

# ---------- DASHBOARD HEADER AFTER LOGIN ----------
st.markdown(f"""<div class='title-box'><div class='main-title'>🧠 NeuroDocs AI</div><div class='sub-title'>Welcome back, <b>{st.session_state.user}</b> 👋 — Ask Anything • Learn From Your Files</div></div>""", unsafe_allow_html=True)
# NEW: Top Stats - Client Impress
a_top = st.session_state.analytics
s1, s2, s3, s4 = st.columns(4)
with s1: st.markdown(f"<div class='stat-box'><h3>🔥 {a_top['streak']} Days</h3><p>Streak</p></div>", unsafe_allow_html=True)
with s2: st.markdown(f"<div class='stat-box'><h3>⭐ {a_top['xp']} XP</h3><p>Level 3 Learner</p></div>", unsafe_allow_html=True)
with s3: st.markdown(f"<div class='stat-box'><h3>❓ {a_top['questions']} Asked</h3><p>Questions</p></div>", unsafe_allow_html=True)
with s4: st.markdown(f"<div class='stat-box'><h3>🎯 {a_top['quizzes']} Quizzes</h3><p>Completed</p></div>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"## 👋 Hi, {st.session_state.user}")
    if st.button("🚪 Logout"): st.session_state.user = None; st.rerun()
    st.markdown("## 🔑 Your API Key")
    groq_k = st.text_input("Groq Key (Free)", type="password", placeholder="gsk_...")
    gemini_k = st.text_input("Gemini Key", type="password", placeholder="AIza...")
    openai_k = st.text_input("OpenAI Key", type="password", placeholder="sk-...")
    st.markdown("[Get Free Groq Key →](https://console.groq.com)")
    st.divider()
    st.markdown("## 🎙️ Voice Settings")
    st.session_state.voice_on = st.toggle("🔊 AI Voice Reply ON", value=st.session_state.voice_on)
    voice_lang = st.selectbox("AI Voice Language", ["Hinglish / Hindi", "English", "Hindi"])
    st.divider()
    st.markdown("## ⚙️ Settings")
    model_choice = st.selectbox("Choose Model", ["OpenAI GPT-OSS 20B - Fast (FREE)", "OpenAI GPT-OSS 120B - Smart (FREE)", "Gemini 2.0 Flash", "OpenAI GPT-4o-mini"])
    detail = st.slider("Detail", 1, 5, 3)
    detail_labels = {1: "1 - One Line", 2: "2 - Short", 3: "3 - Detailed", 4: "4 - Full Example", 5: "5 - Full Chapter"}
    st.success(f"**{detail_labels[detail]}**")
    lang = st.selectbox("🌐 Language", ["English", "Hinglish", "Hindi", "Simple English"])
    mode = st.radio("🎭 Style", ["Normal", "Explain Like 5 Year Old 👶", "Exam Mode 📝", "Simple English 🇬🇧"], horizontal=True)
    st.divider()
    st.markdown("## ⏰ Pomodoro Timer - NEW")
    if st.button("▶️ Start 25 Min Focus"):
        st.session_state.pomo_start = time.time(); st.success("Focus started! 25 min - No phone!")
    if "pomo_start" in st.session_state:
        left = max(0, 1500 - int(time.time() - st.session_state.pomo_start))
        st.progress(left/1500); st.write(f"⏳ {left//60}:{left%60:02d} left")
    st.divider()
    st.markdown("## 📁 Folders")
    st.session_state.current_folder = st.selectbox("Current Folder", list(st.session_state.folders.keys()))
    new_folder = st.text_input("New Folder Name")
    if st.button("➕ Create Folder") and new_folder.strip():
        st.session_state.folders[new_folder.strip()] = []; st.rerun()
    search_q = st.text_input("🔍 Search Chat", placeholder="Search old chats...")
    if search_q:
        hits = [c for c in st.session_state.chat if search_q.lower() in c["content"].lower()]
        st.write(f"Found {len(hits)} chats")
        for h in hits[:3]: st.caption(h["content"][:120])
    st.divider()
    if st.button("🗑️ Clear Chat"):
        clear_memory(); st.session_state.chat = []; st.session_state.vectorstore = None; st.session_state.doc_name = "No Document"; st.rerun()
    if st.button("📄 Download Chat as Notes"):
        notes = "\n\n".join([f"{c['role']}: {c['content']}" for c in st.session_state.chat])
        st.download_button("⬇️ Download", notes, file_name="NeuroDocs-Notes.txt")

user_keys = {"GROQ_API_KEY": groq_k, "GOOGLE_API_KEY": gemini_k, "OPENAI_API_KEY": openai_k}
tab_chat, tab_yt, tab_exam, tab_plan, tab_cards = st.tabs(["💬 Chat", "🎥 YouTube", "⏱️ Mock Test", "📅 Study Planner", "🗂️ Flashcards"])

with tab_yt:
    st.markdown("### 🎥 YouTube Video Summarizer")
    st.markdown("<div class='glass'>Paste any YouTube link with subtitles. AI will read full video and make summary, quiz and notes from it.</div>", unsafe_allow_html=True)
    yt_url = st.text_input("YouTube Link", placeholder="https://youtube.com/watch?v=...")
    st.markdown("**Try this example:** `https://www.youtube.com/watch?v=aircAruvnKk` — Neural Networks Explained")
    if st.button("✨ Summarize Video") and yt_url:
        with st.spinner("Listening to video..."):
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                vid = re.search(r"(?:v=|/)([0-9A-Za-z_-]{11}).*", yt_url)
                video_id = vid.group(1) if vid else yt_url
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en','hi'])
                text = " ".join([t['text'] for t in transcript])[:10000]
                st.session_state.vectorstore = build_brain_from_docs([Document(page_content=text, metadata={"source": yt_url})])
                st.session_state.doc_name = f"YouTube: {yt_url[:40]}"
                st.session_state.analytics["summaries"] += 1
                st.success("Video loaded! Now go to Chat tab and ask - 'Give summary of this video'")
                st.write(text[:1500])
            except Exception as e:
                st.error(f"This video has no subtitles. Try another video with CC. Error: {e}")

with tab_exam:
    st.markdown("### ⏱️ Mock Test - Exam Mode")
    st.markdown("<div class='glass'>🎯 <b>How it works:</b> Enter topic → Start Test → Go to Chat → Tap Quiz → AI will give 5 MCQs. Timer runs here.</div>", unsafe_allow_html=True)
    topic = st.text_input("Test Topic", placeholder="e.g. Photosynthesis, Python, History", key="exam_topic")
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown("<div class='stat-box'><h3>📝 5 Questions</h3><p>MCQ Format</p></div>", unsafe_allow_html=True)
    with c2: st.markdown("<div class='stat-box'><h3>⏰ 5 Minutes</h3><p>Time Limit</p></div>", unsafe_allow_html=True)
    with c3: st.markdown("<div class='stat-box'><h3>🏆 +50 XP</h3><p>On Complete</p></div>", unsafe_allow_html=True)
    if st.button("🎯 Start 5 MCQ Test - 5 Min") and topic:
        st.session_state.exam = {"topic": topic, "start": time.time()}; st.info(f"Test started on {topic}! Go to Chat tab."); st.balloons()
    if st.session_state.exam:
        elapsed = int(time.time() - st.session_state.exam["start"]); left = max(0, 300 - elapsed)
        st.progress(left / 300); st.write(f"⏰ Time Left: {left//60}:{left%60:02d} | Topic: {st.session_state.exam['topic']}")
    else:
        st.info("👆 Enter a topic above and start your test. Example topics: Photosynthesis, Indian History, Python Basics")

with tab_plan:
    st.markdown("### 📅 7-Day Study Planner")
    st.markdown("<div class='glass'>Enter your syllabus. AI will make Day 1 to Day 7 plan with revision + quiz every day.</div>", unsafe_allow_html=True)
    st.markdown("**Example Plans:**")
    e1, e2, e3 = st.columns(3)
    with e1: st.markdown("<div class='stat-box'>📘 Class 10 Science<br>5 Chapters • 7 Days</div>", unsafe_allow_html=True)
    with e2: st.markdown("<div class='stat-box'>💻 Python Basics<br>7 Days • Beginner</div>", unsafe_allow_html=True)
    with e3: st.markdown("<div class='stat-box'>📜 History<br>Freedom Movement</div>", unsafe_allow_html=True)
    syllabus = st.text_input("Your Syllabus / Exam", placeholder="e.g. Class 10 Science - 5 Chapters, Exam in 7 days", key="plan_input")
    if st.button("🪄 Make My Plan") and syllabus:
        llm, _ = get_llm(model_choice, user_keys)
        if llm:
            prompt = f"Make a 7-day study plan for: {syllabus}. Language: {lang}. Give Day 1 to Day 7, each day: Topic, 2 Tasks, 30 min Revision, 1 Quiz. Keep simple."
            plan = llm.invoke(prompt).content; st.markdown(plan); st.download_button("⬇️ Download Plan", plan, file_name="Study-Plan.txt")
        else: st.warning("Add Groq Key in sidebar for AI Plan")

with tab_cards:
    st.markdown("### 🗂️ My Flashcards")
    st.markdown("<div class='glass'>Flashcards help you remember fast. Tap Next to revise. Tap Shuffle to mix.</div>", unsafe_allow_html=True)
    if st.session_state.flash_deck:
        idx = st.session_state.get("card_idx", 0) % len(st.session_state.flash_deck)
        card = st.session_state.flash_deck[idx]
        st.markdown(f"<div class='glass'><h3>{card}</h3><p>Card {idx+1} of {len(st.session_state.flash_deck)}</p></div>", unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("➡️ Next Card"): st.session_state.card_idx = idx + 1; st.rerun()
        with cc2:
            if st.button("🔁 Shuffle"): random.shuffle(st.session_state.flash_deck); st.rerun()
    st.caption(f"Total Cards: {len(st.session_state.flash_deck)} — Create more from Chat -> Create Cards")

with tab_chat:
    st.markdown("### 🤖 Choose Your Bot")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Use LLM Bot", key="llm_btn"): st.session_state.bot_mode = "LLM Bot"; st.rerun()
        st.markdown(f"<div style='text-align:center; font-weight:700'>🧠 LLM BOT {'✅ ACTIVE' if st.session_state.bot_mode == 'LLM Bot' else ''}</div>", unsafe_allow_html=True)
    with col2:
        if st.button("Use RAG Bot", key="rag_btn"): st.session_state.bot_mode = "RAG Bot"; st.rerun()
        st.markdown(f"<div style='text-align:center; font-weight:700'>📚 RAG BOT {'✅ ACTIVE' if st.session_state.bot_mode == 'RAG Bot' else ''}</div>", unsafe_allow_html=True)
    if st.session_state.bot_mode == "LLM Bot": st.info("💡 **LLM Bot:** Ask ANYTHING. No file needed.")
    else: st.warning(f"📚 **RAG Bot:** Only from: `{st.session_state.doc_name}`")

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
                        try: docs += WebBaseLoader(url).load()
                        except: pass
                    if docs:
                        st.session_state.vectorstore = build_brain_from_docs(docs); st.session_state.doc_name = f"{len(urls)} URLs"; st.success("Done!"); st.balloons()
        with t2:
            pdfs = st.file_uploader("Choose PDFs - Multiple Allowed", type=["pdf"], accept_multiple_files=True, key="pdf_upload")
            if pdfs and st.button("Add PDFs", key="add_pdf"):
                all_docs = []
                for pdf in pdfs:
                    with open("temp.pdf", "wb") as f: f.write(pdf.getbuffer())
                    all_docs += PyPDFLoader("temp.pdf").load()
                st.session_state.vectorstore = build_brain_from_docs(all_docs); st.session_state.doc_name = f"{len(pdfs)} PDFs"; st.success(f"{len(pdfs)} PDFs added!"); st.balloons()
        with t3:
            pasted = st.text_area("Paste Any Text", placeholder="Paste PDF text, notes...", height=130, key="pasted")
            if st.button("✨ Add Text", key="add_text") and pasted.strip():
                st.session_state.vectorstore = build_brain_from_docs([Document(page_content=pasted, metadata={"source": "Pasted"})]); st.session_state.doc_name = "Pasted Text"; st.success("Text added!")
        with t4:
            img = st.file_uploader("Upload Photo of Handwritten Notes", type=["png", "jpg", "jpeg"], key="img_upload")
            if img: st.image(img, caption="Your Notes Photo"); st.info("📸 Photo uploaded! Now ask in chat: 'Explain what is written in this image'")

    # ---------- QUICK ACTIONS - FIXED : 3 + 3 - BUG FIXED ----------
    st.markdown("### ⚡ Quick Actions")
    st.caption("Tap any button, then type your topic below. Example: Tap Quiz → Type 'Photosynthesis' → Full quiz will come.")
    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        if st.button("🎯 Create Quiz"): st.session_state.pending_action = "QUIZ"; st.session_state.quiz = True; st.info("✅ Quiz selected! Now type topic in chat box below 👇"); st.toast("Quiz selected - Now type topic")
    with r1c2:
        if st.button("🗂️ Create Cards"): st.session_state.pending_action = "CARDS"; st.session_state.flash = True; st.toast("Cards selected - Now type topic")
    with r1c3:
        if st.button("🧠 Mind Map"): st.session_state.pending_action = "MINDMAP"; st.session_state.mind = True; st.toast("Mind Map selected - Now type topic")
    r2c1, r2c2, r2c3 = st.columns(3)
    with r2c1:
        if st.button("📝 Create Notes"): st.session_state.pending_action = "NOTES"; st.session_state.notes = True; st.toast("Notes selected - Now type topic")
    with r2c2:
        if st.button("📄 Give Summary"): st.session_state.pending_action = "SUMMARY"; st.session_state.summary = True; st.toast("Summary selected - Now type topic")
    with r2c3:
        if st.button("👶 Explain Simple"): st.session_state.pending_action = "SIMPLE"; st.session_state.simple = True; st.toast("Simple selected - Now type topic")

    if st.session_state.pending_action:
        st.success(f"🎯 Selected: {st.session_state.pending_action} — Now type your topic in chat box and press Send. Full answer will come, not 1 word.")

    # ---------- CHAT HISTORY ----------
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    st.markdown("<div class='voice-box'>🎙️ <b>Talk With Voice</b> — Tap mic, speak, AI will answer</div>", unsafe_allow_html=True)
    audio = st.audio_input("Ask by voice", key="voice_input")
    voice_text = ""
    if audio and groq_k:
        voice_text = transcribe_voice(audio.getvalue(), groq_k)
        if voice_text: st.success(f"🗣️ You said: {voice_text}")

    # FIXED: Chat input only triggers on real user input, not on button click
    user_input = st.chat_input("Type topic here... e.g. Photosynthesis")
    prompt = user_input or voice_text
    if prompt:
        # Build full prompt with pending action - THIS FIXES 1-WORD BUG
        action = st.session_state.pending_action
        if action == "QUIZ":
            full_prompt = f"Create a full quiz on topic: {prompt}. Give 5 MCQ questions, each with 4 options A B C D, then give answers at end with explanation. Do not give 1-word answer."
        elif action == "CARDS":
            full_prompt = f"Create 10 flashcards on topic: {prompt}. Format Q: ... A: ... Give full content."
        elif action == "MINDMAP":
            full_prompt = f"Create a detailed mind map on topic: {prompt}. Main topic, then 5 branches, each branch 3 sub-points."
        elif action == "NOTES":
            full_prompt = f"Create detailed exam notes on topic: {prompt}. Point-wise, with headings, definitions, examples."
        elif action == "SUMMARY":
            full_prompt = f"Give a detailed summary of topic: {prompt} in 8-10 points with examples."
        elif action == "SIMPLE":
            full_prompt = f"Explain topic: {prompt} like you are explaining to a 5 year old, with simple examples and story."
        else:
            full_prompt = prompt

        st.session_state.pending_action = None
        st.session_state.chat.append({"role": "user", "content": prompt})
        save_chat("user", prompt)
        with st.chat_message("user"): st.markdown(prompt)
        st.session_state.analytics["questions"] += 1
        st.session_state.analytics["xp"] += 10
        with st.chat_message("assistant"):
            with st.spinner("Thinking... Creating full answer..."):
                llm, _ = get_llm(model_choice, user_keys)
                if not llm:
                    ans = "Please add Groq Key in sidebar (Free) - then I will answer."
                    st.warning(ans)
                else:
                    context = ""
                    if st.session_state.bot_mode == "RAG Bot" and st.session_state.vectorstore:
                        try:
                            docs = st.session_state.vectorstore.similarity_search(prompt, k=4)
                            context = "\n\n".join([d.page_content for d in docs])
                        except: pass
                    extra = ""
                    if st.session_state.quiz: extra = "Make 5 MCQ Quiz with full explanation. "; st.session_state.analytics["quizzes"] += 1; st.session_state.quiz = False
                    if st.session_state.flash: extra += "Make 10 Flashcards in Q: A: format. "; st.session_state.flash = False
                    if st.session_state.notes: extra += "Make detailed exam notes. "; st.session_state.analytics["notes"] += 1; st.session_state.notes = False
                    if st.session_state.summary: extra += "Give detailed summary. "; st.session_state.analytics["summaries"] += 1; st.session_state.summary = False
                    final_prompt = build_prompt(full_prompt, mode, detail, lang, extra, st.session_state.bot_mode, context)
                    ans = llm.invoke(final_prompt).content
                    st.markdown(ans)
                    if "Q:" in ans:
                        st.session_state.flash_deck.extend([l for l in ans.split("\n") if "Q:" in l][:10])
                    if st.session_state.voice_on:
                        lang_code = "hi" if "Hindi" in voice_lang or "Hinglish" in voice_lang else "en"
                        audio_bytes = speak_text(ans, lang_code)
                        if audio_bytes: autoplay_audio(audio_bytes)
                st.session_state.chat.append({"role": "assistant", "content": ans})
                save_chat("assistant", ans)
                st.rerun()
