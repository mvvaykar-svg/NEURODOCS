import streamlit as st
import time, random, os, requests, base64, re, sqlite3, hashlib
from io import BytesIO
from src.llm import get_llm
from src.brain import build_brain_from_docs, load_saved_brain
from src.memory import init_db, load_chat, save_chat, clear_memory
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
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
        return f"You are NeuroDocs AI RAG assistant. Answer ONLY from Context. If not found, say Not found in your document. Never stop in 1 word. Explain fully. Style: {mode}. Detail: {detail_text}. Language: {lang_text}. {extra} Context: {context} Question: {question}"
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
header[data-testid="stHeader"] { background: rgba(2, 6, 20, 0.85) !important; backdrop-filter: blur(8px); }
.stApp { background: radial-gradient(600px 300px at 15% 0%, rgba(0, 180, 255, 0.18) 0%, rgba(0,0,0,0) 60%), radial-gradient(600px 300px at 85% 10%, rgba(0, 90, 255, 0.22) 0%, rgba(0,0,0,0) 60%), rgb(2, 6, 20) !important; color: rgb(226, 236, 255) !important; font-family: 'Inter', sans-serif; }
h1,h2,h3 { color: white !important; font-weight: 800 !important; letter-spacing: -0.2px !important; }
p, span, label { color: rgb(210, 224, 255) !important; }
.block-container { padding-top: 72px !important; max-width: 1120px !important; padding-left: 14px !important; padding-right: 14px !important; }
.spacer { height: 14px !important; }
.spacer-big { height: 22px !important; }
.brand-shade { background: linear-gradient(135deg, rgb(0, 70, 200) 0%, rgb(0, 30, 90) 50%, rgb(4, 10, 30) 100%) !important; border: 1px solid rgb(0, 210, 255) !important; border-radius: 22px !important; padding: 24px 16px 20px 16px !important; text-align: center !important; margin-top: 6px !important; margin-bottom: 16px !important; box-shadow: 0 0 0 1px rgba(0,210,255,0.15), 0 18px 45px rgba(0, 140, 255, 0.28) !important; }
.main-title { font-size: 34px !important; font-weight: 900 !important; color: white !important; margin: 0px !important; line-height: 1 !important; }
.sub-title { font-size: 13px !important; color: rgb(190, 225, 255) !important; font-weight: 600 !important; margin-top: 10px !important; }
.brand-mini { display: inline-block !important; background: rgb(0, 210, 255) !important; color: rgb(0, 20, 50) !important; font-weight: 900 !important; font-size: 11px !important; letter-spacing: 2.5px !important; padding: 5px 14px !important; border-radius: 20px !important; margin-bottom: 12px !important; }
.glass { background: rgb(7, 13, 32) !important; border: 1px solid rgb(45, 95, 180) !important; border-radius: 20px !important; padding: 18px !important; margin-bottom: 16px !important; }
.glass-neon { background: linear-gradient(180deg, rgb(10, 20, 55), rgb(6, 10, 28)) !important; border: 1px solid rgb(0, 210, 255) !important; border-radius: 20px !important; padding: 18px !important; margin-bottom: 16px !important; box-shadow: 0 0 28px rgba(0, 210, 255, 0.14) !important; }
.glass-royal { background: linear-gradient(135deg, rgb(0, 45, 140), rgb(8, 12, 35)) !important; border: 1px solid rgb(90, 170, 255) !important; border-radius: 20px !important; padding: 18px !important; margin-bottom: 16px !important; box-shadow: 0 14px 32px rgba(0, 90, 255, 0.22) !important; }
.glass-cyan { background: linear-gradient(135deg, rgb(0, 120, 200), rgb(6, 12, 32)) !important; border: 1px solid rgb(120, 225, 255) !important; border-radius: 20px !important; padding: 18px !important; margin-bottom: 16px !important; }
.tip-box { background: rgb(8, 14, 35) !important; border-left: 4px solid rgb(0, 210, 255) !important; border-radius: 12px !important; padding: 12px 14px !important; margin-bottom: 16px !important; }
.voice-box { background: rgb(8, 18, 50) !important; border: 1px solid rgb(0, 180, 255) !important; border-radius: 16px !important; padding: 13px !important; text-align: center !important; margin-bottom: 14px !important; margin-top: 10px !important; }
.voice-box b, .voice-box p { color: white !important; font-size: 13px !important; }
.stButton>button { background: rgb(10, 22, 60) !important; color: white !important; font-weight: 700 !important; border-radius: 14px !important; border: 1px solid rgb(60, 130, 220) !important; padding: 11px 8px !important; font-size: 13px !important; width: 100% !important; margin-bottom: 6px !important; white-space: normal !important; line-height: 1.25 !important; min-height: 46px !important; }
.stButton>button:hover { border-color: rgb(0, 210, 255) !important; background: rgb(0, 70, 180) !important; }
.stTextInput>div>div>input, .stTextArea>div>div>textarea { background: rgb(5, 9, 25) !important; color: white !important; border-radius: 13px !important; border: 1px solid rgb(60, 110, 190) !important; }
[data-testid="stSidebar"] { background: rgb(3, 6, 20) !important; border-right: 1px solid rgb(45, 95, 180); }
div[data-testid="stTabs"] button { background: rgb(8, 14, 35) !important; color: rgb(210,225,255) !important; border: 1px solid rgb(45, 95, 180) !important; border-radius: 12px !important; font-weight: 700 !important; padding: 8px 10px !important; white-space: nowrap !important; }
div[data-testid="stTabs"] button[aria-selected="true"] { background: rgb(0, 180, 255) !important; color: rgb(0, 20, 50) !important; border: 1px solid rgb(150, 230, 255) !important; }
.chat-user { background: linear-gradient(135deg, rgb(0, 90, 210), rgb(10, 25, 75)) !important; border: 1px solid rgb(90, 180, 255) !important; border-radius: 16px !important; padding: 12px 14px !important; margin: 10px 0px 10px 10px !important; font-size: 13.5px !important; color: white !important; }
.chat-ai { background: rgb(8, 14, 35) !important; border: 1px solid rgb(45, 95, 180) !important; border-radius: 16px !important; padding: 12px 14px !important; margin: 10px 10px 10px 0px !important; font-size: 13.5px !important; color: rgb(226,236,255) !important; }
.chat-label { font-size: 10px !important; font-weight: 900 !important; color: rgb(0, 210, 255) !important; margin-bottom: 5px !important; letter-spacing: 1.2px !important; }
.login-hero { margin-top: 10px; padding: 28px 20px 22px 20px; background: linear-gradient(180deg, rgb(0, 50, 150), rgb(4, 8, 22)); border: 1px solid rgb(0, 210, 255); border-radius: 26px; text-align: center; box-shadow: 0 20px 45px rgba(0, 140, 255, 0.28); }
.login-hero h1 { font-size: 38px !important; color: white !important; margin: 0px !important; line-height: 1.05; }
.login-hero p { font-size: 15px !important; color: rgb(205, 230, 255) !important; font-weight: 600; margin-top: 10px; }
.stats-row { display: flex !important; gap: 10px !important; margin-bottom: 14px !important; }
.stat-card { flex: 1 !important; background: rgb(8, 14, 35) !important; border: 1px solid rgb(45, 95, 180) !important; border-radius: 16px !important; padding: 11px 6px !important; text-align: center !important; }
.stat-card b { display: block !important; font-size: 18px !important; color: white !important; line-height: 1.1 !important; }
.stat-card span { font-size: 11px !important; color: rgb(190, 210, 245) !important; font-weight: 600 !important; }
.stat-cyan { border-color: rgb(0, 210, 255) !important; }
.stat-cyan b { color: rgb(0, 210, 255) !important; }
.bot-box { background: rgb(8, 14, 35) !important; border: 1px solid rgb(60, 130, 220) !important; border-radius: 20px !important; padding: 18px !important; margin-bottom: 16px !important; }
.bot-box h3 { color: white !important; margin: 0px 0px 8px 0px !important; }
.bot-box p { color: rgb(210,225,255) !important; margin: 0px !important; }
.bot-active { background: rgb(10, 18, 50) !important; border: 1px solid rgb(60, 130, 220) !important; border-radius: 13px !important; padding: 11px !important; text-align: center !important; margin-top: 10px !important; font-weight: 700 !important; color: white !important; }
.bot-active-cyan { background: linear-gradient(135deg, rgb(0, 110, 210), rgb(0, 40, 110)) !important; border: 1px solid rgb(0, 210, 255) !important; border-radius: 13px !important; padding: 11px !important; text-align: center !important; margin-top: 10px !important; font-weight: 800 !important; color: white !important; }
.pdf-box { background: rgb(8, 14, 35) !important; border: 1.5px dashed rgb(0, 210, 255) !important; border-radius: 16px !important; padding: 15px !important; margin: 10px 0px 16px 0px !important; }
.qa-box { background: linear-gradient(180deg, rgb(10, 20, 55), rgb(7, 10, 28)) !important; border: 1px solid rgb(90, 170, 255) !important; border-radius: 20px !important; padding: 16px !important; margin-top: 18px !important; }
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
def auto_new_chat():
    if len(st.session_state.chat) >= 10:
        save_current_session()
        st.session_state.chat = []
        st.session_state.current_session_idx = None
        clear_memory()
        st.toast("Old chat saved in memory. New chat started.")
if not st.session_state.user:
    st.markdown("""<div class='login-hero'><div class='brand-mini'>NEURODOCS</div><h1>🧠 NeuroDocs AI</h1><p>Learn Anything, From Anywhere<br>Your Personal AI Study Buddy<br><br>Unlimited Questions - YouTube Summary - PDF Chat - Mock Test - Flashcards - Study Plan<br>100 Percent Free, No Fees</p></div>""", unsafe_allow_html=True)
    st.markdown("<div class='spacer'></div>", unsafe_allow_html=True)
    lc1, lc2 = st.columns([1.2, 1])
    with lc1:
        st.markdown("<div class='glass-neon'><h2>Welcome Back</h2><p>Login to start your study journey with NeuroDocs AI. New here? Same form will create your account in 10 seconds. Use any password you want, long or short, your choice. Your chats, progress, XP and favourites are saved safely.</p></div>", unsafe_allow_html=True)
        name = st.text_input("Your Name", placeholder="e.g. Viraj")
        pin = st.text_input("Create Any Password - Any Length", type="password", placeholder="e.g. mysecret123")
        goal_pick = st.selectbox("Your Goal", ["Top in Exam", "Learn Coding", "Board Exam", "Competitive Exam", "Learn English"])
        if st.button("Login or Signup - It is FREE", use_container_width=True):
            if name.strip() and len(pin.strip())>=1:
                hashed = hashlib.sha256(pin.strip().encode()).hexdigest()
                row = user_db.execute("SELECT * FROM users WHERE name=?", (name.strip(),)).fetchone()
                if row:
                    if row[1]==hashed:
                        st.session_state.user = name.strip()
                        st.session_state.goal = goal_pick
                        st.rerun()
                    else:
                        st.error("Wrong Password. Enter the correct password or use a new name")
                else:
                    user_db.execute("INSERT INTO users VALUES (?,?)", (name.strip(), hashed))
                    user_db.commit()
                    st.session_state.user = name.strip()
                    st.session_state.goal = goal_pick
                    st.success("Account Created. Welcome to NeuroDocs AI")
                    st.rerun()
            else:
                st.warning("Please enter your Name and Password")
        st.caption("Your password is safe. No one else can see your chats.")
    with lc2:
        st.markdown("<div class='glass-royal'><h2>What You Get</h2><p>Unlimited Questions - Ask anything, get full answer with examples<br>YouTube Summary - Paste link, get summary, quiz and notes<br>PDF Chat with RAG - Upload PDF, ask questions only from your document<br>Mock Test + Timer - 5 MCQs in 5 minutes<br>7-Day Study Plan - Full week plan with revision<br>Flashcards - Revise fast with Q and A cards<br>Previous Chats Saved - After 10 messages, old chat auto saves<br>Daily Goal + XP Points - Track streak and progress</p><p><b>How To Use: 1. Login - 2. Ask a Question in Chat - 3. Make Quiz or Notes - 4. Top Your Exam</b></p></div>", unsafe_allow_html=True)
    st.stop()
    level = "Beginner"
if st.session_state.analytics["xp"] >= 100:
    level = "Advanced"
elif st.session_state.analytics["xp"] >= 50:
    level = "Intermediate"
elif st.session_state.analytics["xp"] >= 20:
    level = "Learning"
st.markdown(f"""<div class='brand-shade'><div class='brand-mini'>NEURODOCS</div><div class='main-title'>🧠 NeuroDocs AI</div><div class='sub-title'>Welcome back, <b>{st.session_state.user}</b> - Level: {level} - Goal: {st.session_state.goal}<br>Ask Anything - Learn From Your Videos</div></div>""", unsafe_allow_html=True)
a_real = st.session_state.analytics
st.markdown(f"""<div class='stats-row'><div class='stat-card'><b>{a_real['questions']}</b><span>Questions</span></div><div class='stat-card'><b>{a_real['quizzes']}</b><span>Quizzes</span></div><div class='stat-card'><b>{a_real['streak']}d</b><span>Streak</span></div><div class='stat-card stat-cyan'><b>{a_real['xp']}</b><span>XP Points</span></div></div>""", unsafe_allow_html=True)
tips = ["Small daily wins make big exam results. Study 25 min, take 5 min break.", "Do not read 3 hours straight. Revise after 1 day, your brain remembers more.", "Topper secret: Learn, Test, Revise. Same topic, 3 times, 3 days.", "One topic at a time. Finish one, then start next. Do not mix."]
tip = tips[a_real['questions'] % len(tips)]
st.markdown(f"<div class='tip-box'><b>Tip of the Day:</b> {tip}</div>", unsafe_allow_html=True)
with st.sidebar:
    st.markdown(f"## Hi, {st.session_state.user}")
    st.caption(f"Level: {level} - NeuroDocs AI")
    if st.button("Logout"):
        save_current_session()
        st.session_state.user = None
        st.rerun()
    st.markdown("## Your API Key")
    groq_k = st.text_input("Groq Key (Free)", type="password", placeholder="gsk_...")
    gemini_k = st.text_input("Gemini Key", type="password", placeholder="AIza...")
    openai_k = st.text_input("OpenAI Key", type="password", placeholder="sk-...")
    st.markdown("[Get Free Groq Key](https://console.groq.com)")
    st.divider()
    st.markdown("## My Daily Goal")
    st.write(f"Goal: {st.session_state.goal}")
    daily_done = st.slider("Today Progress Percent", 0, 100, 20)
    st.progress(daily_done / 100)
    st.caption(f"{daily_done} percent done today. Keep going.")
    st.divider()
    st.markdown("## Previous Chats")
    if st.button("New Chat", use_container_width=True):
        save_current_session()
        st.session_state.chat = []
        st.session_state.current_session_idx = None
        st.rerun()
    if not st.session_state.chat_sessions and not st.session_state.chat:
        st.caption("No previous chats yet. Start a new chat in NeuroDocs AI.")
    for idx, sess in enumerate(st.session_state.chat_sessions):
        col_a, col_b = st.columns([4, 1])
        with col_a:
            if st.button(f"{sess['title'][:28]}", key=f"open_{idx}", use_container_width=True):
                save_current_session()
                st.session_state.chat = list(sess["messages"])
                st.session_state.current_session_idx = idx
                st.rerun()
        with col_b:
            if st.button("Delete", key=f"del_{idx}", help="Delete this chat"):
                del st.session_state.chat_sessions[idx]
                if st.session_state.current_session_idx == idx:
                    st.session_state.chat = []
                    st.session_state.current_session_idx = None
                st.rerun()
    if st.session_state.chat_sessions:
        if st.button("Delete All Chats", use_container_width=True):
            st.session_state.chat_sessions = []
            st.session_state.chat = []
            st.session_state.current_session_idx = None
            clear_memory()
            st.rerun()
    st.caption("Tip: After 10 messages, old chat auto saves and new chat opens.")
    st.divider()
    st.markdown("## Voice Settings")
    st.session_state.voice_on = st.toggle("AI Voice Reply ON", value=st.session_state.voice_on)
    voice_lang = st.selectbox("AI Voice Language", ["English"])
    st.divider()
    st.markdown("## Settings")
    model_choice = st.selectbox("Choose Model", ["OpenAI GPT-OSS 20B - Fast (FREE)", "OpenAI GPT-OSS 120B - Smart (FREE)", "Gemini 2.0 Flash", "OpenAI GPT-4o-mini"])
    detail = st.slider("Detail", 1, 5, 3)
    detail_labels = {1: "1 - One Line", 2: "2 - Short", 3: "3 - Detailed", 4: "4 - Full Example", 5: "5 - Full Chapter"}
    st.success(f"{detail_labels[detail]}")
    lang = st.selectbox("Language", ["English", "Simple English"])
    mode = st.radio("Style", ["Normal", "Explain Like 5 Year Old", "Exam Mode", "Simple English"], horizontal=True)
    st.divider()
    st.markdown("## Search Chat")
    search_q = st.text_input("Search old chats...", placeholder="Type keyword...")
    if search_q:
        hits = [c for c in st.session_state.chat if search_q.lower() in c["content"].lower()]
        st.write(f"Found {len(hits)} in current chat")
        for h in hits[:3]:
            st.caption(h["content"][:120])
    st.divider()
    if st.button("Clear Current Chat"):
        clear_memory()
        st.session_state.chat = []
        st.rerun()
    if st.button("Download Current Chat"):
        notes = "\n\n".join([f"{c['role']}: {c['content']}" for c in st.session_state.chat])
        st.download_button("Download", notes, file_name="NeuroDocs-Notes.txt")
    st.markdown("## Focus Timer")
    if st.button("Start 25 Min Focus"):
        st.session_state.pomo_start = time.time()
    if "pomo_start" in st.session_state:
        left = max(0, 1500 - int(time.time() - st.session_state.pomo_start))
        st.progress(left/1500)
        st.write(f"{left//60}:{left%60:02d} left")
user_keys = {"GROQ_API_KEY": groq_k, "GOOGLE_API_KEY": gemini_k, "OPENAI_API_KEY": openai_k}
tab_chat, tab_yt, tab_study, tab_exam, tab_plan, tab_cards = st.tabs(["Chat", "YouTube Study", "Study Room", "Mock Test", "Study Planner", "Flashcards"])
with tab_yt:
    st.markdown("<div class='glass-cyan'><h2>YouTube Study Room</h2><p>Watch, Understand, Quiz, Remember. Paste any YouTube link, NeuroDocs AI will listen to the full video, make summary, quiz and notes from it.</p></div>", unsafe_allow_html=True)
    yt_url_input = st.text_input("Paste YouTube Link Here", placeholder="https://youtube.com/watch?v=...", key="yt_big_input")
    yt_url = yt_url_input
    st.markdown("<div class='spacer'></div>", unsafe_allow_html=True)
    c_yt1, c_yt2 = st.columns(2)
    with c_yt1:
        yt_summary_btn = st.button("Get Full Summary", use_container_width=True)
    with c_yt2:
        yt_quiz_btn = st.button("Make Quiz From Video", use_container_width=True)
    c_yt3, c_yt4 = st.columns(2)
    with c_yt3:
        yt_notes_btn = st.button("Make Notes", use_container_width=True)
    with c_yt4:
        load_video_btn = st.button("Load Video", use_container_width=True)
    st.markdown("<div class='spacer'></div>", unsafe_allow_html=True)
    st.markdown("<div class='glass'><h3>Popular For Students - Tap To Try</h3><p>Pick a video below to start fast. NeuroDocs AI will load the video, read subtitles, and give you summary and quiz.</p></div>", unsafe_allow_html=True)
    e1, e2 = st.columns(2)
    with e1:
        st.markdown("<div class='glass-royal'><h3>Neural Networks</h3><p>AI - 15 min - Beginner<br>Best for: Class 11-12, College</p></div>", unsafe_allow_html=True)
        if st.button("Load This Video", key="yt_ex1"):
            st.session_state.yt_big_input = "https://www.youtube.com/watch?v=aircAruvnKk"
            st.rerun()
    with e2:
        st.markdown("<div class='glass-neon'><h3>Photosynthesis</h3><p>Biology - 10 min - Class 10<br>Best for: Board Exam</p></div>", unsafe_allow_html=True)
        if st.button("Load This Video", key="yt_ex2"):
            st.session_state.yt_big_input = "https://www.youtube.com/watch?v=UPBMG5EYydo"
            st.rerun()
    st.markdown("<div class='glass-cyan'><h3>Python in 1 Video</h3><p>Coding - 20 min - Beginner<br>Best for: Coding Interview</p></div>", unsafe_allow_html=True)
    if st.button("Load This Video", key="yt_ex3"):
        st.session_state.yt_big_input = "https://www.youtube.com/watch?v=kqtD5dpn9C8"
        st.rerun()
    if yt_url and (yt_summary_btn or yt_quiz_btn or yt_notes_btn or load_video_btn):
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
                st.session_state.bot_mode = "RAG Bot"
                st.session_state.analytics["summaries"] += 1
                st.session_state.analytics["xp"] += 10
                st.success("Video loaded in NeuroDocs AI. Now choose what you want below.")
                st.markdown("<div class='glass-cyan'><h3>What This Video Says - Summary</h3></div>", unsafe_allow_html=True)
                st.write(text[:2500])
                st.markdown("Next Step: Go to Chat tab, Tap Quiz or Notes, Type the same topic, Full answer will come.")
            except Exception as e:
                st.error(f"This video has no subtitles. Try another video with CC. Error: {e}")
with tab_study:
    st.markdown("<div class='glass-royal'><h3>Study Room - One Place, Everything</h3><p>No need to jump tabs. In Study Room you can plan your day, track progress, save favourites and follow a simple system: Learn, Test, Revise.</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='glass-neon'><h3>Todays Focus</h3><p><b>Step 1:</b> Pick one topic, only one<br><b>Step 2:</b> Watch 10 min video in YouTube Study<br><b>Step 3:</b> Do 5 quiz in Chat tab<br><b>Step 4:</b> Revise notes next day</p></div>", unsafe_allow_html=True)
    focus_topic = st.text_input("What are you studying today?", placeholder="e.g. Photosynthesis")
    if st.button("Start My Study Session") and focus_topic:
        st.session_state.pending_action = "SUMMARY"
        st.session_state.analytics["xp"] += 5
        st.success(f"Started: {focus_topic}. Go to Chat tab and type {focus_topic}")
    st.markdown("<div class='glass'><h3>Your Study Progress</h3><p>Questions asked: " + str(st.session_state.analytics['questions']) + "<br>Quizzes done: " + str(st.session_state.analytics['quizzes']) + "<br>Notes made: " + str(st.session_state.analytics['notes']) + "<br><br><b>Smart Tip:</b> Study 25 min, 5 min break, Repeat.</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='glass-cyan'><h3>Quick Revision - 3 Steps</h3><p><b>1. Learn:</b> Watch video or read notes<br><b>2. Test:</b> Give quiz from same topic in Chat tab<br><b>3. Revise:</b> Read notes next day from Flashcards</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='glass'><h3>Save To Favourites</h3><p>Save topics you want to revise again. Example: Photosynthesis, Python Loops, History.</p></div>", unsafe_allow_html=True)
    fav_in = st.text_input("Add Favourite Topic", placeholder="e.g. Photosynthesis")
    if st.button("Add To Favourites") and fav_in:
        st.session_state.favourites.append(fav_in)
        st.success(f"Saved: {fav_in}")
    if st.session_state.favourites:
        st.write("Your Favourites: " + ", ".join(st.session_state.favourites))
with tab_exam:
    st.markdown("<div class='glass-neon'><h3>Mock Test - Exam Mode</h3><p>Enter topic, Start Test, Go to Chat, Tap Quiz, NeuroDocs AI will give 5 MCQs. Timer runs here. Real exam practice: 5 questions, 5 minutes.</p></div>", unsafe_allow_html=True)
    topic = st.text_input("Test Topic", placeholder="e.g. Photosynthesis, Python, History", key="exam_topic")
    exam_level = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
    if st.button("Start 5 MCQ Test - 5 Min") and topic:
        st.session_state.exam = {"topic": topic, "start": time.time(), "level": exam_level}
        st.info(f"Test started on {topic}, Level {exam_level}. Go to Chat tab.")
        st.balloons()
    if st.session_state.exam:
        elapsed = int(time.time() - st.session_state.exam["start"])
        left = max(0, 300 - elapsed)
        st.progress(left / 300)
        st.write(f"Time Left: {left//60}:{left%60:02d} | Topic: {st.session_state.exam['topic']}")
    else:
        st.info("Enter a topic above and start your test.")
with tab_plan:
    st.markdown("<div class='glass-royal'><h3>7-Day Study Planner</h3><p>Enter your syllabus. NeuroDocs AI will make Day 1 to Day 7 plan with revision plus quiz every day.</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='glass'><h3>Popular Plans</h3><p>Class 10 Science - 5 Chapters - 7 Days<br>Python Basics - 7 Days - Beginner<br>History - Freedom Movement - 7 Days</p></div>", unsafe_allow_html=True)
    syllabus = st.text_input("Your Syllabus or Exam", placeholder="e.g. Class 10 Science - 5 Chapters, Exam in 7 days", key="plan_input")
    if st.button("Make My Plan") and syllabus:
        llm, _ = get_llm(model_choice, user_keys)
        if llm:
            prompt = f"Make a 7-day study plan for: {syllabus}. Language: {lang}. Give Day 1 to Day 7, each day: Topic, 2 Tasks, 30 min Revision, 1 Quiz. Keep simple."
            plan = llm.invoke(prompt).content
            st.markdown(plan)
            st.download_button("Download Plan", plan, file_name="NeuroDocs-Study-Plan.txt")
        else:
            st.warning("Add Groq Key in sidebar for AI Plan")
with tab_cards:
    st.markdown("<div class='glass-cyan'><h3>My Flashcards</h3><p>Flashcards help you remember fast. Create from Chat, Tap Create Cards, Type topic, Then revise here.</p></div>", unsafe_allow_html=True)
    if st.session_state.flash_deck:
        idx = st.session_state.get("card_idx", 0) % len(st.session_state.flash_deck)
        card = st.session_state.flash_deck[idx]
        st.markdown(f"<div class='glass-neon'><h3>{card}</h3><p>Card {idx+1} of {len(st.session_state.flash_deck)}. Try to answer in mind before checking answer, then tap Next.</p></div>", unsafe_allow_html=True)
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("Next Card"):
                st.session_state.card_idx = idx + 1
                st.rerun()
        with cc2:
            if st.button("Shuffle"):
                random.shuffle(st.session_state.flash_deck)
                st.rerun()
        if st.button("I Know This"):
            st.session_state.analytics["xp"] += 2
            st.session_state.card_idx = idx + 1
            st.rerun()
    else:
        st.info("No cards yet. Go to Chat, tap Create Cards and type a topic.")
        st.markdown("<div class='glass'><h3>Example Card</h3><p>Q: What is Photosynthesis?<br>A: Process by which plants make food using sunlight</p></div>", unsafe_allow_html=True)
    st.caption(f"Total Cards: {len(st.session_state.flash_deck)}")
with tab_chat:
    auto_new_chat()
    st.markdown("<div class='glass-neon'><h3>Choose Your Bot</h3><p><b>LLM Bot:</b> Ask anything, no file needed. Best for learning new topics, quiz, notes, summary.<br><b>RAG Bot:</b> Ask only from your PDF or YouTube video. Best for exam, document questions, exact answers from your file.</p></div>", unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    with b1:
        if st.button("LLM Bot - Ask Anything", use_container_width=True):
            st.session_state.bot_mode = "LLM Bot"
            st.rerun()
    with b2:
        if st.button("RAG Bot - From PDF / Video", use_container_width=True):
            st.session_state.bot_mode = "RAG Bot"
            st.rerun()
    if st.session_state.bot_mode == "LLM Bot":
        st.markdown("<div class='bot-active-cyan'>LLM BOT ACTIVE - NeuroDocs AI<br>Ask ANYTHING. No file needed. Type topic below and press Send.</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='bot-active-cyan'>RAG BOT ACTIVE - NeuroDocs AI<br>Works with PDF or YouTube video. Upload PDF below, then ask question from your document.</div>", unsafe_allow_html=True)
    st.markdown("<div class='spacer-big'></div>", unsafe_allow_html=True)
    st.markdown("<div class='glass-royal'><h3>Quick Actions</h3><p>Tap one, then type your topic below. Chat auto saves after 10 messages.<br><b>Quiz:</b> 5 MCQs with answers + explanation<br><b>Cards:</b> 10 Flashcards for fast revision<br><b>Mind Map:</b> Main topic + 5 branches<br><b>Notes:</b> Exam notes with headings<br><b>Summary:</b> 8 to 10 points<br><b>Simple:</b> Easy story style</p></div>", unsafe_allow_html=True)
    q1, q2, q3 = st.columns(3)
    with q1:
        if st.button("Quiz", use_container_width=True):
            st.session_state.pending_action = "QUIZ"
            st.session_state.quiz = True
            st.rerun()
    with q2:
        if st.button("Cards", use_container_width=True):
            st.session_state.pending_action = "CARDS"
            st.session_state.flash = True
            st.rerun()
    with q3:
        if st.button("Mind Map", use_container_width=True):
            st.session_state.pending_action = "MINDMAP"
            st.rerun()
    q4, q5, q6 = st.columns(3)
    with q4:
        if st.button("Notes", use_container_width=True):
            st.session_state.pending_action = "NOTES"
            st.session_state.notes = True
            st.rerun()
    with q5:
        if st.button("Summary", use_container_width=True):
            st.session_state.pending_action = "SUMMARY"
            st.session_state.summary = True
            st.rerun()
    with q6:
        if st.button("Simple", use_container_width=True):
            st.session_state.pending_action = "SIMPLE"
            st.session_state.simple = True
            st.rerun()
    qa_info = {"QUIZ": "Quiz - 5 MCQs with 4 options + answers + full explanation", "CARDS": "Cards - 10 Flashcards in Q and A format, revise fast", "MINDMAP": "Mind Map - Main topic + 5 branches + 3 sub points each", "NOTES": "Notes - Point wise exam notes with headings + examples", "SUMMARY": "Summary - 8 to 10 points, short and full revision", "SIMPLE": "Simple - 5 year old style, story + easy examples"}
    if st.session_state.pending_action:
        st.markdown(f"<div class='bot-active'>Selected: {qa_info.get(st.session_state.pending_action, '')}<br>Now type topic below and press Send.</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='bot-active'>Tap one option above, then type topic below.</div>", unsafe_allow_html=True)
    st.markdown("<div class='spacer-big'></div>", unsafe_allow_html=True)
    if st.session_state.bot_mode == "RAG Bot":
        st.markdown("<div class='pdf-box'><b>RAG Document</b><br>Upload PDF for RAG Bot, or paste YouTube link in YouTube Study tab. NeuroDocs AI will read full PDF, make it searchable, and answer only from your document.<br>Current doc: " + st.session_state.doc_name + "</div>", unsafe_allow_html=True)
        pdf_file = st.file_uploader("Upload PDF for RAG Chat", type=["pdf"], key="rag_pdf")
        if pdf_file is not None:
            if st.button("Load This PDF for RAG"):
                with st.spinner("Reading PDF..."):
                    try:
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            tmp.write(pdf_file.getvalue())
                            tmp_path = tmp.name
                        loader = PyPDFLoader(tmp_path)
                        docs = loader.load()
                        full_text = "\n".join([d.page_content for d in docs])
                        st.session_state.vectorstore = build_brain_from_docs([Document(page_content=full_text, metadata={"source": pdf_file.name})])
                        st.session_state.doc_name = pdf_file.name
                        st.session_state.bot_mode = "RAG Bot"
                        st.success(f"PDF Loaded: {pdf_file.name}. Now RAG Bot is ON. Ask question from PDF.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"PDF could not load. Error: {e}")
        if st.session_state.doc_name != "No Document":
            if st.button("Remove Document, Back to LLM"):
                st.session_state.vectorstore = load_saved_brain()
                st.session_state.doc_name = "No Document"
                st.session_state.bot_mode = "LLM Bot"
                st.rerun()
    st.markdown("<div class='spacer-big'></div>", unsafe_allow_html=True)
    st.markdown("<h3>Chat History</h3><p>Your questions and answers appear here. After 10 messages, old chat auto saves in sidebar.</p>", unsafe_allow_html=True)
    st.markdown("<div class='spacer'></div>", unsafe_allow_html=True)
    for msg in st.session_state.chat:
        if msg["role"] == "user":
            safe = msg["content"].replace("<", "").replace(">", "")[:2000]
            st.markdown(f"<div class='chat-user'><div class='chat-label'>YOU</div>{safe}</div>", unsafe_allow_html=True)
        else:
            safe = msg["content"].replace("<", "").replace(">", "")[:4000]
            st.markdown(f"<div class='chat-ai'><div class='chat-label'>NEURODOCS AI</div>{safe}</div>", unsafe_allow_html=True)
        st.markdown("<div class='spacer'></div>", unsafe_allow_html=True)
    st.markdown("<div class='spacer-big'></div>", unsafe_allow_html=True)
    st.markdown("<div class='qa-box'><h3>Ask Question</h3><p>Type or speak below. You can type topic like Photosynthesis, Python, History, or speak with voice. NeuroDocs AI will give full answer with examples.</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='voice-box'><b>Talk With Voice</b> - Tap mic, speak, NeuroDocs AI will answer</div>", unsafe_allow_html=True)
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
        st.markdown(f"<div class='chat-user'><div class='chat-label'>YOU</div>{prompt}</div>", unsafe_allow_html=True)
        st.session_state.analytics["questions"] += 1
        st.session_state.analytics["xp"] += 5
        ans = "Please add Groq Key in sidebar (Free) - then I will answer."
        with st.spinner("NeuroDocs AI Thinking... Creating full answer..."):
            llm, _ = get_llm(model_choice, user_keys)
            if llm:
                try:
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
                    st.markdown(f"<div class='chat-ai'><div class='chat-label'>NEURODOCS AI</div>{ans[:4000]}</div>", unsafe_allow_html=True)
                    if "Q:" in ans:
                        st.session_state.flash_deck.extend([l for l in ans.split("\n") if "Q:" in l][:10])
                    if st.session_state.voice_on:
                        lang_code = "en"
                        audio_bytes = speak_text(ans, lang_code)
                        if audio_bytes:
                            autoplay_audio(audio_bytes)
                except Exception as e:
                    ans = f"NeuroDocs AI could not answer. Error: {e}"
                    st.error(ans)
            else:
                st.warning(ans)
            st.session_state.chat.append({"role": "assistant", "content": ans})
            save_chat("assistant", ans)
            auto_new_chat()
            st.rerun()
