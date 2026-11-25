import streamlit as st
import time, random, os, requests, base64, re, sqlite3, hashlib
from io import BytesIO
from src.llm import get_llm
from src.brain import build_brain_from_docs, load_saved_brain
from src.memory import init_db, load_chat, save_chat, clear_memory
from langchain_community.document_loaders import WebBaseLoader, PyPDFLoader
from langchain_core.documents import Document
st.set_page_config(page_title="NeuroDocs AI", page_icon="🧠", layout="wide")
def get_user_db():
    conn = sqlite3.connect("users.db", check_same_thread=False)
    conn.execute("CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY, pin TEXT)")
    return conn
user_db = get_user_db()
def build_prompt(question, mode, detail, lang, extra, bot_mode, context=""):
    detail_map = {1: "Answer in 1 line", 2: "Answer in short", 3: "Answer in detail", 4: "Answer in very detail with example", 5: "Answer like a full chapter with headings"}
    lang_map = {"English": "Answer in English", "Simple English": "Answer in very simple English"}
    detail_text = detail_map.get(detail, "Answer in detail")
    lang_text = lang_map.get(lang, "Answer in English")
    if bot_mode == "LLM Bot":
        return f"You are NeuroDocs AI, a friendly tutor. Never give 1-word answer. Always explain with examples. Style: {mode}. Detail: {detail_text}. Language: {lang_text}. {extra} Question: {question}"
    else:
        return f"You are a RAG assistant. Answer ONLY from Context. If not found, say Not found in your document. Never stop in 1 word. Explain fully. Style: {mode}. Detail: {detail_text}. Language: {lang_text}. {extra} Context: {context} Question: {question}"
def transcribe_voice(audio_bytes, groq_key):
    try:
        files = {"file": ("voice.wav", audio_bytes, "audio/wav")}
        data = {"model": "whisper-large-v3", "language": "en"}
        headers = {"Authorization": f"Bearer {groq_key}"}
        r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files, data=data, timeout=30)
        return r.json().get("text", "") if r.status_code == 200 else ""
    except:
        return ""
def speak_text(text, lang_code="en"):
    try:
        from gtts import gTTS
        clean = text.replace("*", "").replace("`", "")[:1000]
        tts = gTTS(text=clean, lang=lang_code, slow=False)
        buf = BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.read()
    except:
        return None
def autoplay_audio(audio_bytes):
    b64 = base64.b64encode(audio_bytes).decode()
    st.markdown(f"""<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>""", unsafe_allow_html=True)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
.stApp { background: rgb(2, 6, 23) !important; color: rgb(219, 234, 254) !important; font-family: 'Inter', sans-serif; }
h1,h2,h3 { color: rgb(255, 255, 255) !important; font-weight: 700 !important; }
p, span, label { color: rgb(219, 234, 254) !important; }
.block-container { padding-top: 0rem !important; max-width: 100% !important; }
.title-box { margin-top: 58px !important; padding: 14px 12px 12px 12px !important; background: linear-gradient(135deg, rgb(2, 6, 23) 0%, rgb(30, 64, 175) 55%, rgb(0, 150, 255) 100%) !important; border: 2px solid rgb(0, 180, 255) !important; border-radius: 16px !important; text-align: center !important; box-shadow: 0 0 18px rgba(0,180,255,0.3); }
.main-title { font-size: 28px !important; font-weight: 800 !important; color: rgb(255, 255, 255) !important; margin: 0px !important; line-height: 1.1 !important; }
.sub-title { font-size: 12px !important; color: rgb(191, 219, 254) !important; font-weight: 600 !important; margin-top: 4px; }
.glass { background: rgb(10, 25, 60) !important; border: 2px solid rgb(30, 64, 175) !important; border-radius: 12px; padding: 10px !important; margin-bottom: 8px !important; }
.glass h3, .glass p, .glass span { color: rgb(219, 234, 254) !important; }
.glass-big { background: rgb(30, 64, 175) !important; border: 2px solid rgb(0, 180, 255) !important; border-radius: 12px; padding: 10px !important; margin-bottom: 8px; }
.glass-big h3, .glass-big p { color: rgb(255, 255, 255) !important; }
.glass-amber { background: rgb(10, 25, 60) !important; border: 2px solid rgb(0, 180, 255) !important; border-radius: 12px; padding: 10px !important; margin-bottom: 8px; }
.glass-amber p, .glass-amber h3, .glass-amber span { color: rgb(219, 234, 254) !important; }
.glass-mint { background: rgb(10, 25, 60) !important; border: 2px solid rgb(0, 180, 255) !important; border-radius: 12px; padding: 10px !important; margin-bottom: 8px; }
.glass-mint p, .glass-mint h3, .glass-mint span { color: rgb(219, 234, 254) !important; }
.voice-box { background: rgb(30, 64, 175) !important; border: 2px solid rgb(0, 180, 255) !important; border-radius: 10px; padding: 8px !important; text-align: center; margin-bottom: 8px; }
.voice-box b, .voice-box p { color: rgb(255, 255, 255) !important; font-size: 12px !important; }
.stButton>button { background: rgb(0, 180, 255) !important; color: rgb(2, 6, 23) !important; font-weight: 800; border-radius: 10px; border: 2px solid rgb(147, 197, 253) !important; padding: 7px 10px !important; font-size: 13px !important; width: 100%; }
.quick-row div[data-testid="column"] .stButton>button { padding: 6px 4px !important; font-size: 12px !important; min-height: 30px !important; background: rgb(30, 64, 175) !important; color: rgb(255, 255, 255) !important; border: 2px solid rgb(0, 180, 255) !important; }
.stTextInput>div>div>input, .stTextArea>div>div>textarea { background: rgb(10, 25, 60) !important; color: white !important; border-radius: 10px !important; border: 2px solid rgb(0, 180, 255) !important; }
[data-testid="stSidebar"] { background: rgb(2, 6, 23) !important; border-right: 2px solid rgb(30, 64, 175); }
div[data-testid="stChatMessage"] { background: rgb(10, 25, 60) !important; border: 2px solid rgb(30, 64, 175) !important; border-radius: 12px; padding: 10px !important; }
div[data-testid="stChatMessage"] p { color: rgb(219, 234, 254) !important; }
.yt-big { background: linear-gradient(135deg, rgb(2, 6, 23), rgb(30, 64, 175)) !important; border: 2px solid rgb(0, 180, 255) !important; border-radius: 12px; padding: 10px !important; margin-bottom: 8px; }
.yt-big h2 { font-size: 17px !important; color: rgb(255, 255, 255) !important; margin: 0px !important; }
.yt-big p { color: rgb(191, 219, 254) !important; font-size: 12px !important; margin: 2px 0 0 0 !important; }
.yt-card { background: rgb(10, 25, 60) !important; border: 2px solid rgb(0, 180, 255) !important; border-radius: 10px; padding: 9px 10px !important; margin-bottom: 8px; }
.yt-card h3 { font-size: 13px !important; margin: 0 0 3px 0 !important; color: rgb(255, 255, 255) !important; }
.yt-card p { font-size: 11.5px !important; margin: 0px !important; color: rgb(191, 219, 254) !important; }
.login-hero { margin-top: 40px; padding: 24px 20px 20px 20px; background: linear-gradient(135deg, rgb(2, 6, 23) 0%, rgb(30, 64, 175) 55%, rgb(0, 180, 255) 100%); border: 2px solid rgb(0, 180, 255); border-radius: 20px; text-align: center; }
.login-hero h1 { font-size: 40px !important; color: rgb(255, 255, 255) !important; margin: 0px !important; line-height: 1.1; }
.login-hero p { font-size: 15px !important; color: rgb(191, 219, 254) !important; font-weight: 600; margin-top: 8px; }
.login-card { background: rgb(10, 25, 60); border: 2px solid rgb(0, 180, 255); border-radius: 16px; padding: 20px; margin-top: 12px; }
.login-card h2 { font-size: 20px !important; margin: 0 0 6px 0 !important; color: rgb(255, 255, 255) !important; }
.login-card p { color: rgb(191, 219, 254) !important; }
.stat-small { background: rgb(10, 25, 60) !important; border: 1.5px solid rgb(0, 180, 255) !important; border-radius: 20px !important; padding: 5px 8px !important; text-align: center !important; margin-bottom: 4px !important; }
.stat-small span { font-size: 11.5px !important; color: rgb(219, 234, 254) !important; font-weight: 600 !important; }
.stat-small b { font-size: 12px !important; color: rgb(0, 210, 255) !important; }
.stat-sky { background: rgb(30, 64, 175) !important; border: 2px solid rgb(0, 180, 255) !important; border-radius: 12px; padding: 10px !important; }
.stat-sky h3, .stat-sky p { color: rgb(255, 255, 255) !important; }
.stat-cyan { background: rgb(0, 150, 255) !important; border: 2px solid rgb(147, 197, 253) !important; border-radius: 12px; padding: 10px !important; }
.stat-cyan h3, .stat-cyan p { color: rgb(255, 255, 255) !important; }
.stat-blue { background: rgb(10, 25, 60) !important; border: 2px solid rgb(0, 180, 255) !important; border-radius: 12px; padding: 10px !important; }
.stat-blue h3, .stat-blue p { color: rgb(255, 255, 255) !important; }
</style>
""", unsafe_allow_html=True)
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
if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = []
if "current_session_idx" not in st.session_state:
    st.session_state.current_session_idx = None
if "flash_deck" not in st.session_state:
    st.session_state.flash_deck = []
if "exam" not in st.session_state:
    st.session_state.exam = None
if "analytics" not in st.session_state:
    st.session_state.analytics = {"questions": 0, "quizzes": 0, "notes": 0, "summaries": 0, "streak": 1, "xp": 0}
if "voice_on" not in st.session_state:
    st.session_state.voice_on = True
if "pending_action" not in st.session_state:
    st.session_state.pending_action = None
if "goal" not in st.session_state:
    st.session_state.goal = "Top in Exam"
if "favourites" not in st.session_state:
    st.session_state.favourites = []
for k in ["quiz", "flash", "mind", "summary", "simple", "notes", "quick_prompt"]:
    if k not in st.session_state:
        st.session_state[k] = False if k != "quick_prompt" else ""
def save_current_session():
    if st.session_state.chat:
        title = st.session_state.chat[0]["content"][:35] if st.session_state.chat else "New Chat"
        if st.session_state.current_session_idx is not None and st.session_state.current_session_idx < len(st.session_state.chat_sessions):
            st.session_state.chat_sessions[st.session_state.current_session_idx] = {"title": title, "messages": list(st.session_state.chat)}
        else:
            st.session_state.chat_sessions.append({"title": title, "messages": list(st.session_state.chat)})
            st.session_state.current_session_idx = len(st.session_state.chat_sessions)-1
if not st.session_state.user:
    st.markdown("""<div class='login-hero'><h1>🧠 NeuroDocs AI</h1><p>Learn Anything, From Anywhere<br>Your Personal AI Study Buddy</p></div>""", unsafe_allow_html=True)
    lc1, lc2 = st.columns([1.2, 1])
    with lc1:
        st.markdown("<div class='login-card'><h2>👋 Welcome Back</h2><p>Login to start your study. New here? The same form will create your account.</p></div>", unsafe_allow_html=True)
        name = st.text_input("👤 Your Name", placeholder="e.g. Viraj")
        pin = st.text_input("🔒 Create or Enter 4 Digit PIN", type="password", placeholder="e.g. 1234", max_chars=4)
        goal_pick = st.selectbox("🎯 Your Goal", ["Top in Exam", "Learn Coding", "Board Exam", "Competitive Exam", "Learn English"])
        if st.button("🚀 Login or Signup - It is FREE", use_container_width=True):
            if name.strip() and len(pin)==4:
                hashed = hashlib.sha256(pin.encode()).hexdigest()
                row = user_db.execute("SELECT * FROM users WHERE name=?", (name.strip(),)).fetchone()
                if row:
                    if row[1]==hashed:
                        st.session_state.user = name.strip()
                        st.session_state.goal = goal_pick
                        st.rerun()
                    else:
                        st.error("Wrong PIN. Enter the correct PIN or use a new name")
                else:
                    user_db.execute("INSERT INTO users VALUES (?,?)", (name.strip(), hashed))
                    user_db.commit()
                    st.session_state.user = name.strip()
                    st.session_state.goal = goal_pick
                    st.success("Account Created. Welcome")
                    st.rerun()
            else:
                st.warning("Please enter your Name and 4 digit PIN")
        st.caption("Your PIN is safe. No one else can see your chats.")
    with lc2:
        st.markdown("<div class='login-card'><h2>✨ What You Get</h2><p>✅ Unlimited Questions<br>✅ YouTube Summary<br>✅ Mock Test + Timer<br>✅ 7-Day Study Plan<br>✅ Flashcards<br>✅ Previous Chats Saved<br>✅ Daily Goal + XP Points</p><p><b>100 Percent Free - No Fees</b></p></div>", unsafe_allow_html=True)
    st.markdown("<div class='stat-sky'><h3>How To Use</h3><p>1. Login - 2. Ask a Question in Chat - 3. Make Quiz or Notes - 4. Top Your Exam</p></div>", unsafe_allow_html=True)
    st.stop()
st.markdown(f"""<div class='title-box'><div class='main-title'>🧠 NeuroDocs AI</div><div class='sub-title'>Welcome back, <b>{st.session_state.user}</b> - Goal: {st.session_state.goal} - Ask Anything - Learn From Your Videos</div></div>""", unsafe_allow_html=True)
a_real = st.session_state.analytics
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"<div class='stat-small'><span>❓ Questions <b>{a_real['questions']}</b></span></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='stat-small'><span>🎯 Quizzes <b>{a_real['quizzes']}</b></span></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='stat-small'><span>🔥 Streak <b>{a_real['streak']}d</b></span></div>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='stat-small'><span>⭐ XP <b>{a_real['xp']}</b></span></div>", unsafe_allow_html=True)
with st.sidebar:
    st.markdown(f"## 👋 Hi, {st.session_state.user}")
    if st.button("🚪 Logout"):
        save_current_session()
        st.session_state.user = None
        st.rerun()
    st.markdown("## 🔑 Your API Key")
    groq_k = st.text_input("Groq Key (Free)", type="password", placeholder="gsk_...")
    gemini_k = st.text_input("Gemini Key", type="password", placeholder="AIza...")
    openai_k = st.text_input("OpenAI Key", type="password", placeholder="sk-...")
    st.markdown("[Get Free Groq Key](https://console.groq.com)")
    st.divider()
    st.markdown("## 🎯 My Daily Goal")
    st.write(f"Goal: {st.session_state.goal}")
    daily_done = st.slider("Today Progress Percent", 0, 100, 20)
    st.progress(daily_done / 100)
    st.caption(f"{daily_done} percent done today. Keep going.")
    st.divider()
    st.markdown("## 💬 Previous Chats")
    if st.button("➕ New Chat", use_container_width=True):
        save_current_session()
        st.session_state.chat = []
        st.session_state.current_session_idx = None
        st.rerun()
    if not st.session_state.chat_sessions and not st.session_state.chat:
        st.caption("No previous chats yet. Start a new chat.")
    for idx, sess in enumerate(st.session_state.chat_sessions):
        col_a, col_b = st.columns([4, 1])
        with col_a:
            if st.button(f"💬 {sess['title'][:28]}", key=f"open_{idx}", use_container_width=True):
                save_current_session()
                st.session_state.chat = list(sess["messages"])
                st.session_state.current_session_idx = idx
                st.rerun()
        with col_b:
            if st.button("🗑️", key=f"del_{idx}", help="Delete this chat"):
                del st.session_state.chat_sessions[idx]
                if st.session_state.current_session_idx == idx:
                    st.session_state.chat = []
                    st.session_state.current_session_idx = None
                st.rerun()
    if st.session_state.chat_sessions:
        if st.button("🗑️ Delete All Chats", use_container_width=True):
            st.session_state.chat_sessions = []
            st.session_state.chat = []
            st.session_state.current_session_idx = None
            clear_memory()
            st.rerun()
    st.caption("Tip: Chat auto-saves when you start a new chat or logout.")
    st.divider()
    st.markdown("## 🎙️ Voice Settings")
    st.session_state.voice_on = st.toggle("🔊 AI Voice Reply ON", value=st.session_state.voice_on)
    voice_lang = st.selectbox("AI Voice Language", ["English"])
    st.divider()
    st.markdown("## ⚙️ Settings")
    model_choice = st.selectbox("Choose Model", ["OpenAI GPT-OSS 20B - Fast (FREE)", "OpenAI GPT-OSS 120B - Smart (FREE)", "Gemini 2.0 Flash", "OpenAI GPT-4o-mini"])
    detail = st.slider("Detail", 1, 5, 3)
    detail_labels = {1: "1 - One Line", 2: "2 - Short", 3: "3 - Detailed", 4: "4 - Full Example", 5: "5 - Full Chapter"}
    st.success(f"{detail_labels[detail]}")
    lang = st.selectbox("🌐 Language", ["English", "Simple English"])
    mode = st.radio("🎭 Style", ["Normal", "Explain Like 5 Year Old 👶", "Exam Mode 📝", "Simple English 🇬🇧"], horizontal=True)
    st.divider()
    st.markdown("## 🔍 Search Chat")
    search_q = st.text_input("Search old chats...", placeholder="Type keyword...")
    if search_q:
        hits = [c for c in st.session_state.chat if search_q.lower() in c["content"].lower()]
        st.write(f"Found {len(hits)} in current chat")
        for h in hits[:3]:
            st.caption(h["content"][:120])
    st.divider()
    if st.button("🗑️ Clear Current Chat"):
        clear_memory()
        st.session_state.chat = []
        st.rerun()
    if st.button("📄 Download Current Chat"):
        notes = "\n\n".join([f"{c['role']}: {c['content']}" for c in st.session_state.chat])
        st.download_button("⬇️ Download", notes, file_name="NeuroDocs-Notes.txt")
    st.markdown("## ⏰ Focus Timer")
    if st.button("▶️ Start 25 Min Focus"):
        st.session_state.pomo_start = time.time()
    if "pomo_start" in st.session_state:
        left = max(0, 1500 - int(time.time() - st.session_state.pomo_start))
        st.progress(left/1500)
        st.write(f"⏳ {left//60}:{left%60:02d} left")
user_keys = {"GROQ_API_KEY": groq_k, "GOOGLE_API_KEY": gemini_k, "OPENAI_API_KEY": openai_k}
tab_chat, tab_yt, tab_study, tab_exam, tab_plan, tab_cards = st.tabs(["💬 Chat", "🎥 YouTube Study", "📚 Study Room", "⏱️ Mock Test", "📅 Study Planner", "🗂️ Flashcards"])
with tab_yt:
    st.markdown("<div class='yt-big'><h2>🎥 YouTube Study Room</h2><p>Watch, Understand, Quiz, Remember. All in one place.</p></div>", unsafe_allow_html=True)
    yt_url = st.text_input("🔗 Paste YouTube Link Here", placeholder="https://youtube.com/watch?v=...", key="yt_big_input")
    c_yt1, c_yt2, c_yt3 = st.columns(3)
    with c_yt1:
        yt_summary_btn = st.button("📄 Get Full Summary", use_container_width=True)
    with c_yt2:
        yt_quiz_btn = st.button("🎯 Make Quiz From Video", use_container_width=True)
    with c_yt3:
        yt_notes_btn = st.button("📝 Make Notes", use_container_width=True)
    st.markdown("<div class='stat-blue'><h3>Popular For Students - Tap To Try</h3><p>Pick a video below to start fast.</p></div>", unsafe_allow_html=True)
    e1, e2, e3 = st.columns(3)
    with e1:
        st.markdown("<div class='yt-card'><h3>🧠 Neural Networks</h3><p>AI - 15 min - Beginner</p><p>Best for: Class 11-12, College</p></div>", unsafe_allow_html=True)
        if st.button("▶️ Load This Video", key="yt_ex1"):
            yt_url = "https://www.youtube.com/watch?v=aircAruvnKk"
    with e2:
        st.markdown("<div class='yt-card'><h3>🌱 Photosynthesis</h3><p>Biology - 10 min - Class 10</p><p>Best for: Board Exam</p></div>", unsafe_allow_html=True)
        if st.button("▶️ Load This Video", key="yt_ex2"):
            yt_url = "https://www.youtube.com/watch?v=UPBMG5EYydo"
    with e3:
        st.markdown("<div class='yt-card'><h3>🐍 Python in 1 Video</h3><p>Coding - 20 min - Beginner</p><p>Best for: Coding Interview</p></div>", unsafe_allow_html=True)
        if st.button("▶️ Load This Video", key="yt_ex3"):
            yt_url = "https://www.youtube.com/watch?v=kqtD5dpn9C8"
    if yt_url and (yt_summary_btn or yt_quiz_btn or yt_notes_btn or st.button("✨ Load Video", use_container_width=True)):
        with st.spinner("Listening to full video..."):
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                vid = re.search(r"(?:v=|/)([0-9A-Za-z_-]{11}).*", yt_url)
                video_id = vid.group(1) if vid else yt_url
                st.video(yt_url)
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
                text = " ".join([t['text'] for t in transcript])[:12000]
                st.session_state.vectorstore = build_brain_from_docs([Document(page_content=text, metadata={"source": yt_url})])
                st.session_state.doc_name = f"YouTube: {yt_url[:40]}"
                st.session_state.analytics["summaries"] += 1
                st.session_state.analytics["xp"] += 10
                st.success("Video loaded. Now choose what you want below.")
                st.markdown("<div class='glass-big'><h3>📖 What This Video Says</h3></div>", unsafe_allow_html=True)
                st.write(text[:2500])
                st.markdown("Next Step: Go to Chat tab, Tap Quiz or Notes, Type the same topic, Full answer will come.")
            except Exception as e:
                st.error(f"This video has no subtitles. Try another video with CC. Error: {e}")
with tab_study:
    st.markdown("<div class='glass-amber'><h3>📚 Study Room - One Place, Everything</h3><p>No need to jump tabs. Watch YouTube plus Make Quiz, all here.</p></div>", unsafe_allow_html=True)
    s1, s2 = st.columns(2)
    with s1:
        st.markdown("<div class='glass-mint'><h3>🎯 Todays Focus</h3><p><b>Step 1:</b> Pick one topic<br><b>Step 2:</b> Watch 10 min video<br><b>Step 3:</b> Do 5 quiz<br><b>Step 4:</b> Revise notes</p><p>Done equals You win today.</p></div>", unsafe_allow_html=True)
        focus_topic = st.text_input("What are you studying today?", placeholder="e.g. Photosynthesis")
        if st.button("🚀 Start My Study Session") and focus_topic:
            st.session_state.pending_action = "SUMMARY"
            st.session_state.analytics["xp"] += 5
            st.success(f"Started: {focus_topic}. Go to Chat tab and type {focus_topic}")
    with s2:
        st.markdown("<div class='glass'><h3>📊 Your Study Progress</h3><p>Questions asked: " + str(st.session_state.analytics['questions']) + "</p><p>Quizzes done: " + str(st.session_state.analytics['quizzes']) + "</p><p>Notes made: " + str(st.session_state.analytics['notes']) + "</p></div>", unsafe_allow_html=True)
        st.markdown("<div class='glass'><h3>💡 Smart Tip</h3><p>Do not study 3 hours straight. Study 25 min, 5 min break, Repeat. Your brain remembers more.</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='stat-cyan'><h3>Quick Revision - 3 Steps</h3><p>Learn, Test, Revise. Simple system for top marks.</p></div>", unsafe_allow_html=True)
    r1, r2, r3 = st.columns(3)
    with r1:
        st.markdown("<div class='yt-card'><h3>1. Learn</h3><p>Watch video or read notes</p></div>", unsafe_allow_html=True)
    with r2:
        st.markdown("<div class='yt-card'><h3>2. Test</h3><p>Give quiz from same topic</p></div>", unsafe_allow_html=True)
    with r3:
        st.markdown("<div class='yt-card'><h3>3. Revise</h3><p>Read notes next day</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='stat-blue'><h3>⭐ Save To Favourites</h3><p>Save topics you want to revise again.</p></div>", unsafe_allow_html=True)
    fav_in = st.text_input("Add Favourite Topic", placeholder="e.g. Photosynthesis")
    if st.button("⭐ Add To Favourites") and fav_in:
        st.session_state.favourites.append(fav_in)
        st.success(f"Saved: {fav_in}")
    if st.session_state.favourites:
        st.write("Your Favourites: " + ", ".join(st.session_state.favourites))
with tab_exam:
    st.markdown("<div class='stat-blue'><h3>Mock Test - Exam Mode</h3><p>Enter topic, Start Test, Go to Chat, Tap Quiz, AI will give 5 MCQs. Timer runs here.</p></div>", unsafe_allow_html=True)
    topic = st.text_input("Test Topic", placeholder="e.g. Photosynthesis, Python, History", key="exam_topic")
    exam_level = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
    if st.button("🎯 Start 5 MCQ Test - 5 Min") and topic:
        st.session_state.exam = {"topic": topic, "start": time.time(), "level": exam_level}
        st.info(f"Test started on {topic}, Level {exam_level}. Go to Chat tab.")
        st.balloons()
    if st.session_state.exam:
        elapsed = int(time.time() - st.session_state.exam["start"])
        left = max(0, 300 - elapsed)
        st.progress(left / 300)
        st.write(f"⏰ Time Left: {left//60}:{left%60:02d} | Topic: {st.session_state.exam['topic']}")
    else:
        st.info("Enter a topic above and start your test.")
with tab_plan:
    st.markdown("<div class='stat-sky'><h3>7-Day Study Planner</h3><p>Enter your syllabus. AI will make Day 1 to Day 7 plan with revision plus quiz every day.</p></div>", unsafe_allow_html=True)
    pe1, pe2, pe3 = st.columns(3)
    with pe1:
        st.markdown("<div class='yt-card'>📘 Class 10 Science<br>5 Chapters - 7 Days</div>", unsafe_allow_html=True)
    with pe2:
        st.markdown("<div class='yt-card'>💻 Python Basics<br>7 Days - Beginner</div>", unsafe_allow_html=True)
    with pe3:
        st.markdown("<div class='yt-card'>📜 History<br>Freedom Movement</div>", unsafe_allow_html=True)
    syllabus = st.text_input("Your Syllabus or Exam", placeholder="e.g. Class 10 Science - 5 Chapters, Exam in 7 days", key="plan_input")
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
    st.markdown("<div class='stat-cyan'><h3>My Flashcards</h3><p>Flashcards help you remember fast. Create from Chat, Create Cards. Then revise here.</p></div>", unsafe_allow_html=True)
    if st.session_state.flash_deck:
        idx = st.session_state.get("card_idx", 0) % len(st.session_state.flash_deck)
        card = st.session_state.flash_deck[idx]
        st.markdown(f"<div class='glass'><h3>{card}</h3><p>Card {idx+1} of {len(st.session_state.flash_deck)}</p></div>", unsafe_allow_html=True)
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            if st.button("➡️ Next Card"):
                st.session_state.card_idx = idx + 1
                st.rerun()
        with cc2:
            if st.button("🔁 Shuffle"):
                random.shuffle(st.session_state.flash_deck)
                st.rerun()
        with cc3:
            if st.button("✅ I Know This"):
                st.session_state.analytics["xp"] += 2
                st.session_state.card_idx = idx + 1
                st.rerun()
    else:
        st.info("No cards yet. Go to Chat, tap Create Cards and type a topic.")
        st.markdown("<div class='yt-card'><h3>Example Card</h3><p>Q: What is Photosynthesis?<br>A: Process by which plants make food using sunlight</p></div>", unsafe_allow_html=True)
    st.caption(f"Total Cards: {len(st.session_state.flash_deck)}")
with tab_chat:
    st.markdown("<div class='stat-blue'><h3>Choose Your Bot</h3><p>LLM Bot for anything. RAG Bot for YouTube video.</p></div>", unsafe_allow_html=True)
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
        st.info("💡 LLM Bot: Ask ANYTHING. No file needed.")
    else:
        st.info("📚 RAG Bot: Works with YouTube video. First add a video in YouTube tab, then ask a question here.")
    st.markdown("<div class='stat-sky'><h3>Quick Actions</h3><p>Tap one, then type your topic below.</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='quick-row'>", unsafe_allow_html=True)
    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        if st.button("🎯 Quiz"):
            st.session_state.pending_action = "QUIZ"
            st.session_state.quiz = True
            st.toast("Quiz selected - Now type topic")
    with r1c2:
        if st.button("🗂️ Cards"):
            st.session_state.pending_action = "CARDS"
            st.session_state.flash = True
            st.toast("Cards selected")
    with r1c3:
        if st.button("🧠 Mind Map"):
            st.session_state.pending_action = "MINDMAP"
            st.session_state.mind = True
            st.toast("Mind Map selected")
    r2c1, r2c2, r2c3 = st.columns(3)
    with r2c1:
        if st.button("📝 Notes"):
            st.session_state.pending_action = "NOTES"
            st.session_state.notes = True
            st.toast("Notes selected")
    with r2c2:
        if st.button("📄 Summary"):
            st.session_state.pending_action = "SUMMARY"
            st.session_state.summary = True
            st.toast("Summary selected")
    with r2c3:
        if st.button("👶 Simple"):
            st.session_state.pending_action = "SIMPLE"
            st.session_state.simple = True
            st.toast("Simple selected")
    st.markdown("</div>", unsafe_allow_html=True)
    if st.session_state.pending_action:
        st.success(f"Selected: {st.session_state.pending_action} - Now type topic below and press Send.")
    for msg in st.session_state.chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    st.markdown("<div class='voice-box'>🎙️ <b>Talk With Voice</b> - Tap mic, speak, AI will answer</div>", unsafe_allow_html=True)
    audio = st.audio_input("Ask by voice", key="voice_input")
    voice_text = ""
    if audio and groq_k:
        voice_text = transcribe_voice(audio.getvalue(), groq_k)
        if voice_text:
            st.success(f"You said: {voice_text}")
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
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.analytics["questions"] += 1
        st.session_state.analytics["xp"] += 5
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
                        except:
                            pass
                    extra = ""
                    if st.session_state.quiz:
                        extra = "Make 5 MCQ Quiz with full explanation. "
                        st.session_state.analytics["quizzes"] += 1
                        st.session_state.quiz = False
                    if st.session_state.flash:
                        extra += "Make 10 Flashcards in Q: A: format. "
                        st.session_state.flash = False
                    if st.session_state.notes:
                        extra += "Make detailed exam notes. "
                        st.session_state.analytics["notes"] += 1
                        st.session_state.notes = False
                    if st.session_state.summary:
                        extra += "Give detailed summary. "
                        st.session_state.analytics["summaries"] += 1
                        st.session_state.summary = False
                    final_prompt = build_prompt(full_prompt, mode, detail, lang, extra, st.session_state.bot_mode, context)
                    ans = llm.invoke(final_prompt).content
                    st.markdown(ans)
                    if "Q:" in ans:
                        st.session_state.flash_deck.extend([l for l in ans.split("\n") if "Q:" in l][:10])
                    if st.session_state.voice_on:
                        lang_code = "en"
                        audio_bytes = speak_text(ans, lang_code)
                        if audio_bytes:
                            autoplay_audio(audio_bytes)
                st.session_state.chat.append({"role": "assistant", "content": ans})
                save_chat("assistant", ans)
                st.rerun()
