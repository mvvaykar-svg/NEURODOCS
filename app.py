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
        return f"You are NeuroDocs AI, a friendly tutor. Never give 1-word answer. Always explain with examples. Style: {mode}. Detail: {detail_text}. Language: {lang_text}. {extra}\nQuestion: {question}"
    else:
        return f"You are a RAG assistant. Answer ONLY from Context. If not found, say 'Not found in your document'. Never stop in 1 word. Explain fully. Style: {mode}. Detail: {detail_text}. Language: {lang_text}. {extra}\nContext: {context}\nQuestion: {question}"

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

# ---------- NEW COLOUR - MIDNIGHT + PEACH + SOFT YELLOW - SMALL BOXES ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
.stApp { background: #0F172A !important; color: #F1F5F9 !important; font-family: 'Inter', sans-serif; }
h1,h2,h3 { color: #FFFFFF !important; font-weight: 700 !important; }
p, span, label { color: #CBD5E1 !important; }
.block-container { padding-top: 0rem !important; max-width: 100% !important; }
.title-box { margin-top: 58px !important; padding: 14px 12px 12px 12px !important; background: linear-gradient(135deg, #FFC9A8 0%, #FFE66D 50%, #FFFFFF 100%) !important; border-radius: 16px !important; text-align: center !important; }
.main-title { font-size: 28px !important; font-weight: 800 !important; color: #0F172A !important; margin: 0px !important; line-height: 1.1 !important; }
.sub-title { font-size: 12.5px !important; color: #334155 !important; font-weight: 600 !important; margin-top: 4px; }
.glass { background: #1E293B !important; border: 1px solid #334155 !important; border-radius: 12px; padding: 10px 12px !important; margin-bottom: 8px !important; }
.glass h3 { font-size: 14px !important; margin-bottom: 4px !important; }
.glass p { font-size: 12.5px !important; line-height: 1.4 !important; margin: 0px !important; }
.glass-big { background: #1E293B !important; border: 1px solid #334155 !important; border-radius: 14px; padding: 12px !important; margin-bottom: 10px; }
.glass-amber { background: #FFC9A8 !important; border-radius: 12px; padding: 10px 12px !important; margin-bottom: 8px; }
.glass-amber p, .glass-amber h3, .glass-amber span { color: #0F172A !important; font-size: 13px !important; }
.glass-mint { background: #FFE66D !important; border-radius: 12px; padding: 10px 12px !important; margin-bottom: 8px; }
.glass-mint p, .glass-mint h3, .glass-mint span { color: #0F172A !important; font-size: 13px !important; }
.voice-box { background: #FFC9A8 !important; border-radius: 12px; padding: 10px !important; text-align: center; margin-bottom: 10px; }
.voice-box b, .voice-box p { color: #0F172A !important; font-size: 13px !important; }
.stButton>button { background: #FFFFFF !important; color: #0F172A !important; font-weight: 700; border-radius: 10px; border: none !important; padding: 7px 10px !important; font-size: 13px !important; width: 100%; }
.quick-row div[data-testid="column"] .stButton>button { padding: 6px 4px !important; font-size: 11.5px !important; min-height: 30px !important; background: #334155 !important; color: #FFFFFF !important; border: none !important; }
.stTextInput>div>div>input, .stTextArea>div>div>textarea { background: #1E293B !important; color: white !important; border-radius: 10px !important; border: 1px solid #334155 !important; }
[data-testid="stSidebar"] { background: #0B1220 !important; border-right: 1px solid #1E293B; }
div[data-testid="stChatMessage"] { background: #1E293B !important; border-radius: 12px; border: 1px solid #334155 !important; padding: 10px !important; }
.yt-big { background: #FFC9A8 !important; border-radius: 14px; padding: 12px !important; margin-bottom: 10px; }
.yt-big h2 { font-size: 18px !important; color: #0F172A !important; margin: 0px !important; }
.yt-big p { color: #334155 !important; font-size: 12.5px !important; margin: 2px 0 0 0 !important; }
.yt-card { background: #1E293B !important; border: 1px solid #334155 !important; border-radius: 12px; padding: 10px 12px !important; margin-bottom: 8px; }
.yt-card h3 { font-size: 14px !important; margin: 0 0 4px 0 !important; }
.yt-card p { font-size: 12px !important; margin: 0px !important; }
</style>
""", unsafe_allow_html=True)

# ---------- SESSION ----------
if "chat" not in st.session_state:
    init_db(); st.session_state.chat = load_chat()
if "vectorstore" not in st.session_state: st.session_state.vectorstore = load_saved_brain()
if "doc_name" not in st.session_state: st.session_state.doc_name = "No Document"
if "bot_mode" not in st.session_state: st.session_state.bot_mode = "LLM Bot"
if "user" not in st.session_state: st.session_state.user = None
if "chat_sessions" not in st.session_state: st.session_state.chat_sessions = []
if "current_session_idx" not in st.session_state: st.session_state.current_session_idx = None
if "flash_deck" not in st.session_state: st.session_state.flash_deck = []
if "exam" not in st.session_state: st.session_state.exam = None
if "analytics" not in st.session_state: st.session_state.analytics = {"questions": 0, "quizzes": 0, "notes": 0, "summaries": 0}
if "voice_on" not in st.session_state: st.session_state.voice_on = True
if "pending_action" not in st.session_state: st.session_state.pending_action = None
for k in ["quiz", "flash", "mind", "summary", "simple", "notes", "quick_prompt"]:
    if k not in st.session_state: st.session_state[k] = False if k != "quick_prompt" else ""

def save_current_session():
    if st.session_state.chat:
        title = st.session_state.chat[0]["content"][:35] if st.session_state.chat else "New Chat"
        if st.session_state.current_session_idx is not None and st.session_state.current_session_idx < len(st.session_state.chat_sessions):
            st.session_state.chat_sessions[st.session_state.current_session_idx] = {"title": title, "messages": list(st.session_state.chat)}
        else:
            st.session_state.chat_sessions.append({"title": title, "messages": list(st.session_state.chat)})
            st.session_state.current_session_idx = len(st.session_state.chat_sessions)-1

# ---------- LOGIN ----------
if not st.session_state.user:
    st.markdown("""<div class='title-box'><div class='main-title'>🧠 NeuroDocs AI</div><div class='sub-title'>Learn Anything, From Anywhere — Your Personal AI Study Buddy</div></div>""", unsafe_allow_html=True)
    st.markdown("<div class='glass'><h3>👋 Welcome to NeuroDocs AI</h3><p>Ask anything. Upload your PDF, YouTube link or notes. Get quiz, notes and summary from your own material.</p></div>", unsafe_allow_html=True)
    s1, s2, s3 = st.columns(3)
    with s1: st.markdown("<div class='glass-mint'><h3>1. Ask</h3><p>Ask any Q</p></div>", unsafe_allow_html=True)
    with s2: st.markdown("<div class='glass-mint'><h3>2. Upload</h3><p>PDF / YouTube</p></div>", unsafe_allow_html=True)
    with s3: st.markdown("<div class='glass-mint'><h3>3. Learn</h3><p>Quiz / Notes</p></div>", unsafe_allow_html=True)
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
        st.markdown("<div class='glass'><b>What you can do:</b><br>✅ Ask any question<br>✅ Upload PDF<br>✅ YouTube summary<br>✅ Quiz + Flashcards<br>✅ Voice chat<br>✅ Save & delete chats</div>", unsafe_allow_html=True)
    st.markdown("### 🎬 How it works")
    st.markdown("1️⃣ Login → 2️⃣ Choose Bot → 3️⃣ Type or Speak → 4️⃣ Get Quiz / Notes")
    st.stop()

st.markdown(f"""<div class='title-box'><div class='main-title'>🧠 NeuroDocs AI</div><div class='sub-title'>Welcome back, <b>{st.session_state.user}</b> 👋 — Ask Anything • Learn From Your Files</div></div>""", unsafe_allow_html=True)
a_real = st.session_state.analytics
st.caption(f"Your activity in this session — Questions: {a_real['questions']} | Quizzes: {a_real['quizzes']} | Notes: {a_real['notes']}")

with st.sidebar:
    st.markdown(f"## 👋 Hi, {st.session_state.user}")
    if st.button("🚪 Logout"):
        save_current_session(); st.session_state.user = None; st.rerun()
    st.markdown("## 🔑 Your API Key")
    groq_k = st.text_input("Groq Key (Free)", type="password", placeholder="gsk_...")
    gemini_k = st.text_input("Gemini Key", type="password", placeholder="AIza...")
    openai_k = st.text_input("OpenAI Key", type="password", placeholder="sk-...")
    st.markdown("[Get Free Groq Key →](https://console.groq.com)")
    st.divider()
    st.markdown("## 💬 Previous Chats")
    if st.button("➕ New Chat", use_container_width=True):
        save_current_session(); st.session_state.chat = []; st.session_state.current_session_idx = None; st.rerun()
    if not st.session_state.chat_sessions and not st.session_state.chat:
        st.caption("No previous chats yet. Start a new chat.")
    for idx, sess in enumerate(st.session_state.chat_sessions):
        col_a, col_b = st.columns([4, 1])
        with col_a:
            if st.button(f"💬 {sess['title'][:28]}", key=f"open_{idx}", use_container_width=True):
                save_current_session(); st.session_state.chat = list(sess["messages"]); st.session_state.current_session_idx = idx; st.rerun()
        with col_b:
            if st.button("🗑️", key=f"del_{idx}", help="Delete this chat"):
                del st.session_state.chat_sessions[idx]
                if st.session_state.current_session_idx == idx:
                    st.session_state.chat = []; st.session_state.current_session_idx = None
                st.rerun()
    if st.session_state.chat_sessions:
        if st.button("🗑️ Delete All Chats", use_container_width=True):
            st.session_state.chat_sessions = []; st.session_state.chat = []; st.session_state.current_session_idx = None; clear_memory(); st.rerun()
    st.caption("Tip: Chat auto-saves when you start a new chat or logout.")
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
    st.markdown("## 🔍 Search Chat")
    search_q = st.text_input("Search old chats...", placeholder="Type keyword...")
    if search_q:
        hits = [c for c in st.session_state.chat if search_q.lower() in c["content"].lower()]
        st.write(f"Found {len(hits)} in current chat")
        for h in hits[:3]: st.caption(h["content"][:120])
    st.divider()
    if st.button("🗑️ Clear Current Chat"):
        clear_memory(); st.session_state.chat = []; st.rerun()
    if st.button("📄 Download Current Chat"):
        notes = "\n\n".join([f"{c['role']}: {c['content']}" for c in st.session_state.chat])
        st.download_button("⬇️ Download", notes, file_name="NeuroDocs-Notes.txt")
    st.markdown("## ⏰ Focus Timer")
    if st.button("▶️ Start 25 Min Focus"):
        st.session_state.pomo_start = time.time()
    if "pomo_start" in st.session_state:
        left = max(0, 1500 - int(time.time() - st.session_state.pomo_start))
        st.progress(left/1500); st.write(f"⏳ {left//60}:{left%60:02d} left")

user_keys = {"GROQ_API_KEY": groq_k, "GOOGLE_API_KEY": gemini_k, "OPENAI_API_KEY": openai_k}
tab_chat, tab_yt, tab_study, tab_exam, tab_plan, tab_cards = st.tabs(["💬 Chat", "🎥 YouTube Study", "📚 Study Room", "⏱️ Mock Test", "📅 Study Planner", "🗂️ Flashcards"])

with tab_yt:
    st.markdown("<div class='yt-big'><h2>🎥 YouTube Study Room</h2><p>Watch → Understand → Quiz → Remember. All in one place.</p></div>", unsafe_allow_html=True)
    yt_url = st.text_input("🔗 Paste YouTube Link Here", placeholder="https://youtube.com/watch?v=...", key="yt_big_input")
    c_yt1, c_yt2, c_yt3 = st.columns(3)
    with c_yt1: yt_summary_btn = st.button("📄 Get Full Summary", use_container_width=True)
    with c_yt2: yt_quiz_btn = st.button("🎯 Make Quiz From Video", use_container_width=True)
    with c_yt3: yt_notes_btn = st.button("📝 Make Notes", use_container_width=True)
    st.markdown("### 🔥 Popular For Students - Tap To Try")
    e1, e2, e3 = st.columns(3)
    with e1:
        st.markdown("<div class='yt-card'><h3>🧠 Neural Networks</h3><p>AI • 15 min • Beginner</p><p>Best for: Class 11-12, College</p></div>", unsafe_allow_html=True)
        if st.button("▶️ Load This Video", key="yt_ex1"): yt_url = "https://www.youtube.com/watch?v=aircAruvnKk"
    with e2:
        st.markdown("<div class='yt-card'><h3>🌱 Photosynthesis</h3><p>Biology • 10 min • Class 10</p><p>Best for: Board Exam</p></div>", unsafe_allow_html=True)
        if st.button("▶️ Load This Video", key="yt_ex2"): yt_url = "https://www.youtube.com/watch?v=UPBMG5EYydo"
    with e3:
        st.markdown("<div class='yt-card'><h3>🐍 Python in 1 Video</h3><p>Coding • 20 min • Beginner</p><p>Best for: Coding Interview</p></div>", unsafe_allow_html=True)
        if st.button("▶️ Load This Video", key="yt_ex3"): yt_url = "https://www.youtube.com/watch?v=kqtD5dpn9C8"
    if yt_url and (yt_summary_btn or yt_quiz_btn or yt_notes_btn or st.button("✨ Load Video", use_container_width=True)):
        with st.spinner("Listening to full video..."):
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                vid = re.search(r"(?:v=|/)([0-9A-Za-z_-]{11}).*", yt_url)
                video_id = vid.group(1) if vid else yt_url
                st.video(yt_url)
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en','hi'])
                text = " ".join([t['text'] for t in transcript])[:12000]
                st.session_state.vectorstore = build_brain_from_docs([Document(page_content=text, metadata={"source": yt_url})])
                st.session_state.doc_name = f"YouTube: {yt_url[:40]}"
                st.session_state.analytics["summaries"] += 1
                st.success("Video loaded! Now choose what you want below.")
                st.markdown("<div class='glass-big'><h3>📖 What This Video Says</h3></div>", unsafe_allow_html=True)
                st.write(text[:2500])
                st.markdown("**Next Step:** Go to Chat tab → Tap Quiz / Notes → Type same topic → Full answer will come.")
            except Exception as e:
                st.error(f"This video has no subtitles. Try another video with CC. Error: {e}")

with tab_study:
    st.markdown("<div class='glass-amber'><h3>📚 Study Room — One Place, Everything</h3><p>No need to jump tabs. Upload PDF + Watch YouTube + Make Quiz — all here.</p></div>", unsafe_allow_html=True)
    s1, s2 = st.columns(2)
    with s1:
        st.markdown("<div class='glass-mint'><h3>🎯 Today's Focus</h3><p><b>Step 1:</b> Pick one topic<br><b>Step 2:</b> Watch 10 min video<br><b>Step 3:</b> Do 5 quiz<br><b>Step 4:</b> Revise notes</p><p>Done = You win today.</p></div>", unsafe_allow_html=True)
        focus_topic = st.text_input("What are you studying today?", placeholder="e.g. Photosynthesis")
        if st.button("🚀 Start My Study Session") and focus_topic:
            st.session_state.pending_action = "SUMMARY"
            st.success(f"Started: {focus_topic}. Go to Chat tab and type '{focus_topic}'")
    with s2:
        st.markdown("<div class='glass'><h3>📊 Your Study Progress</h3><p>Questions asked: " + str(st.session_state.analytics['questions']) + "</p><p>Quizzes done: " + str(st.session_state.analytics['quizzes']) + "</p><p>Notes made: " + str(st.session_state.analytics['notes']) + "</p></div>", unsafe_allow_html=True)
        st.markdown("<div class='glass'><h3>💡 Smart Tip</h3><p>Don't study 3 hours straight. Study 25 min → 5 min break → Repeat. Your brain remembers more.</p></div>", unsafe_allow_html=True)
    st.markdown("### 🗂️ Quick Revision - 3 Steps")
    r1, r2, r3 = st.columns(3)
    with r1: st.markdown("<div class='yt-card'><h3>1. Learn</h3><p>Watch video or read PDF</p></div>", unsafe_allow_html=True)
    with r2: st.markdown("<div class='yt-card'><h3>2. Test</h3><p>Give quiz from same topic</p></div>", unsafe_allow_html=True)
    with r3: st.markdown("<div class='yt-card'><h3>3. Revise</h3><p>Read notes next day</p></div>", unsafe_allow_html=True)

with tab_exam:
    st.markdown("### ⏱️ Mock Test - Exam Mode")
    st.markdown("<div class='glass'>Enter topic → Start Test → Go to Chat → Tap Quiz → AI will give 5 MCQs. Timer runs here.</div>", unsafe_allow_html=True)
    topic = st.text_input("Test Topic", placeholder="e.g. Photosynthesis, Python, History", key="exam_topic")
    if st.button("🎯 Start 5 MCQ Test - 5 Min") and topic:
        st.session_state.exam = {"topic": topic, "start": time.time()}; st.info(f"Test started on {topic}! Go to Chat tab."); st.balloons()
    if st.session_state.exam:
        elapsed = int(time.time() - st.session_state.exam["start"]); left = max(0, 300 - elapsed)
        st.progress(left / 300); st.write(f"⏰ Time Left: {left//60}:{left%60:02d} | Topic: {st.session_state.exam['topic']}")
    else:
        st.info("Enter a topic above and start your test.")

with tab_plan:
    st.markdown("### 📅 7-Day Study Planner")
    st.markdown("<div class='glass'>Enter your syllabus. AI will make Day 1 to Day 7 plan with revision + quiz every day.</div>", unsafe_allow_html=True)
    pe1, pe2, pe3 = st.columns(3)
    with pe1: st.markdown("<div class='yt-card'>📘 Class 10 Science<br>5 Chapters • 7 Days</div>", unsafe_allow_html=True)
    with pe2: st.markdown("<div class='yt-card'>💻 Python Basics<br>7 Days • Beginner</div>", unsafe_allow_html=True)
    with pe3: st.markdown("<div class='yt-card'>📜 History<br>Freedom Movement</div>", unsafe_allow_html=True)
    syllabus = st.text_input("Your Syllabus / Exam", placeholder="e.g. Class 10 Science - 5 Chapters, Exam in 7 days", key="plan_input")
    if st.button("🪄 Make My Plan") and syllabus:
        llm, _ = get_llm(model_choice, user_keys)
        if llm:
            prompt = f"Make a 7-day study plan for: {syllabus}. Language: {lang}. Give Day 1 to Day 7, each day: Topic, 2 Tasks, 30 min Revision, 1 Quiz. Keep simple."
            plan = llm.invoke(prompt).content; st.markdown(plan); st.download_button("⬇️ Download Plan", plan, file_name="Study-Plan.txt")
        else: st.warning("Add Groq Key in sidebar for AI Plan")

with tab_cards:
    st.markdown("### 🗂️ My Flashcards")
    st.markdown("<div class='glass'>Flashcards help you remember fast. Create from Chat -> Create Cards. Then revise here.</div>", unsafe_allow_html=True)
    if st.session_state.flash_deck:
        idx = st.session_state.get("card_idx", 0) % len(st.session_state.flash_deck)
        card = st.session_state.flash_deck[idx]
        st.markdown(f"<div class='glass'><h3>{card}</h3><p>Card {idx+1} of {len(st.session_state.flash_deck)}</p></div>", unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("➡️ Next Card"): st.session_state.card_idx = idx + 1; st.rerun()
        with cc2:
            if st.button("🔁 Shuffle"): random.shuffle(st.session_state.flash_deck); st.rerun()
    else:
        st.info("No cards yet. Go to Chat, tap Create Cards and type a topic.")
        st.markdown("<div class='yt-card'><h3>Example Card</h3><p>Q: What is Photosynthesis?<br>A: Process by which plants make food using sunlight</p></div>", unsafe_allow_html=True)
    st.caption(f"Total Cards: {len(st.session_state.flash_deck)}")

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
            if img: st.image(img, caption="Your Notes Photo"); st.info("Photo uploaded! Now ask: 'Explain what is written in this image'")

    st.markdown("### ⚡ Quick Actions")
    st.caption("Tap one, then type your topic below.")
    st.markdown("<div class='quick-row'>", unsafe_allow_html=True)
    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        if st.button("🎯 Quiz"): st.session_state.pending_action = "QUIZ"; st.session_state.quiz = True; st.toast("Quiz selected - Now type topic")
    with r1c2:
        if st.button("🗂️ Cards"): st.session_state.pending_action = "CARDS"; st.session_state.flash = True; st.toast("Cards selected")
    with r1c3:
        if st.button("🧠 Mind Map"): st.session_state.pending_action = "MINDMAP"; st.session_state.mind = True; st.toast("Mind Map selected")
    r2c1, r2c2, r2c3 = st.columns(3)
    with r2c1:
        if st.button("📝 Notes"): st.session_state.pending_action = "NOTES"; st.session_state.notes = True; st.toast("Notes selected")
    with r2c2:
        if st.button("📄 Summary"): st.session_state.pending_action = "SUMMARY"; st.session_state.summary = True; st.toast("Summary selected")
    with r2c3:
        if st.button("👶 Simple"): st.session_state.pending_action = "SIMPLE"; st.session_state.simple = True; st.toast("Simple selected")
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.pending_action:
        st.success(f"Selected: {st.session_state.pending_action} — Now type topic below and press Send.")

    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    st.markdown("<div class='voice-box'>🎙️ <b>Talk With Voice</b> — Tap mic, speak, AI will answer</div>", unsafe_allow_html=True)
    audio = st.audio_input("Ask by voice", key="voice_input")
    voice_text = ""
    if audio and groq_k:
        voice_text = transcribe_voice(audio.getvalue(), groq_k)
        if voice_text: st.success(f"You said: {voice_text}")

    user_input = st.chat_input("Type topic here... e.g. Photosynthesis")
    prompt = user_input or voice_text
    if prompt:
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
