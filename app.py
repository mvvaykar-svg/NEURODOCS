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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
.stApp { background: rgb(3, 5, 18) !important; color: rgb(203, 213, 235) !important; font-family: 'Inter', sans-serif; }
h1,h2,h3 { color: rgb(255, 255, 255) !important; font-weight: 700 !important; }
p, span, label { color: rgb(203, 213, 235) !important; }
.block-container { padding-top: 0rem !important; max-width: 100% !important; }
.spacer { height: 18px !important; }
.spacer-big { height: 26px !important; }
.brand-shade { background: linear-gradient(135deg, rgb(35, 55, 130), rgb(8, 14, 35)) !important; border: 1.5px solid rgb(0, 190, 255) !important; border-radius: 18px !important; padding: 16px 12px 14px 12px !important; text-align: center !important; margin-top: 58px !important; margin-bottom: 18px !important; box-shadow: 0 8px 30px rgba(0, 190, 255, 0.15); }
.main-title { font-size: 30px !important; font-weight: 800 !important; color: rgb(255, 255, 255) !important; margin: 0px !important; line-height: 1.1 !important; letter-spacing: 0.5px !important; }
.sub-title { font-size: 12px !important; color: rgb(190, 210, 240) !important; font-weight: 600 !important; margin-top: 6px; }
.brand-mini { display: inline-block !important; background: rgb(0, 160, 230) !important; color: white !important; font-weight: 800 !important; font-size: 11px !important; letter-spacing: 1.5px !important; padding: 4px 12px !important; border-radius: 20px !important; margin-bottom: 8px !important; }
.glass { background: rgb(8, 14, 35) !important; border: 1.5px solid rgb(55, 85, 160) !important; border-radius: 16px; padding: 16px !important; margin-bottom: 18px !important; }
.glass h3, .glass p, .glass span { color: rgb(203, 213, 235) !important; }
.glass-big { background: rgb(35, 55, 130) !important; border: 1.5px solid rgb(70, 110, 190) !important; border-radius: 16px; padding: 16px !important; margin-bottom: 18px; }
.glass-big h3, .glass-big p { color: rgb(255, 255, 255) !important; }
.voice-box { background: rgb(35, 55, 130) !important; border: 1.5px solid rgb(70, 110, 190) !important; border-radius: 14px; padding: 12px !important; text-align: center; margin-bottom: 16px; margin-top: 10px; }
.voice-box b, .voice-box p { color: rgb(255, 255, 255) !important; font-size: 13px !important; }
.stButton>button { background: rgb(35, 55, 130) !important; color: rgb(255, 255, 255) !important; font-weight: 700; border-radius: 12px; border: 1.5px solid rgb(70, 110, 190) !important; padding: 9px 10px !important; font-size: 13px !important; width: 100%; margin-bottom: 6px !important; }
.stTextInput>div>div>input, .stTextArea>div>div>textarea { background: rgb(8, 14, 35) !important; color: white !important; border-radius: 12px !important; border: 1.5px solid rgb(55, 85, 160) !important; }
[data-testid="stSidebar"] { background: rgb(3, 5, 18) !important; border-right: 1.5px solid rgb(35, 55, 130); }
div[data-testid="stTabs"] button { background: rgb(8, 14, 35) !important; color: rgb(203, 213, 235) !important; border: 1.5px solid rgb(55, 85, 160) !important; border-radius: 12px !important; font-weight: 700 !important; padding: 8px 10px !important; }
div[data-testid="stTabs"] button[aria-selected="true"] { background: rgb(0, 160, 230) !important; color: white !important; border: 1.5px solid rgb(120, 220, 255) !important; box-shadow: 0 0 16px rgba(0, 190, 255, 0.35) !important; }
div[data-testid="stChatMessage"] { background: transparent !important; border: none !important; padding: 2px 0px !important; }
.chat-user { background: rgb(35, 55, 130) !important; border: 1.5px solid rgb(70, 110, 190) !important; border-radius: 14px; padding: 10px 12px !important; margin: 10px 0px 10px 20px !important; font-size: 13.5px !important; color: rgb(255, 255, 255) !important; }
.chat-ai { background: rgb(8, 14, 35) !important; border: 1.5px solid rgb(55, 85, 160) !important; border-radius: 14px; padding: 10px 12px !important; margin: 10px 20px 10px 0px !important; font-size: 13.5px !important; color: rgb(203, 213, 235) !important; }
.chat-label { font-size: 10px !important; font-weight: 800 !important; color: rgb(120, 170, 255) !important; margin-bottom: 4px !important; letter-spacing: 1px !important; }
.login-hero { margin-top: 40px; padding: 26px 20px 22px 20px; background: linear-gradient(135deg, rgb(35, 55, 130), rgb(8, 14, 35)); border: 1.5px solid rgb(0, 190, 255); border-radius: 22px; text-align: center; }
.login-hero h1 { font-size: 40px !important; color: rgb(255, 255, 255) !important; margin: 0px !important; line-height: 1.1; }
.login-hero p { font-size: 15px !important; color: rgb(190, 210, 240) !important; font-weight: 600; margin-top: 8px; }
.stat-small { background: rgb(8, 14, 35) !important; border: 1.5px solid rgb(55, 85, 160) !important; border-radius: 20px !important; padding: 6px 8px !important; text-align: center !important; margin-bottom: 8px !important; }
.stat-small span { font-size: 11.5px !important; color: rgb(203, 213, 235) !important; font-weight: 600 !important; }
.stat-small b { font-size: 12px !important; color: rgb(120, 170, 255) !important; }
.bot-box { background: rgb(35, 55, 130) !important; border: 1.5px solid rgb(70, 110, 190) !important; border-radius: 18px !important; padding: 16px !important; margin-bottom: 20px !important; }
.bot-box h3 { color: rgb(255, 255, 255) !important; margin: 0px 0px 6px 0px !important; }
.bot-box p { color: rgb(203, 213, 235) !important; margin: 0px !important; }
.bot-active { background: rgb(8, 14, 35) !important; border: 1.5px solid rgb(55, 85, 160) !important; border-radius: 12px !important; padding: 10px !important; text-align: center !important; margin-top: 10px !important; font-weight: 700 !important; color: rgb(255, 255, 255) !important; }
.bot-active-cyan { background: rgb(8, 14, 35) !important; border: 1.5px solid rgb(0, 190, 255) !important; border-radius: 12px !important; padding: 10px !important; text-align: center !important; margin-top: 10px !important; font-weight: 700 !important; color: rgb(160, 225, 255) !important; }
.pdf-box { background: rgb(8, 14, 35) !important; border: 1.5px dashed rgb(0, 190, 255) !important; border-radius: 14px; padding: 14px !important; margin: 10px 0px 18px 0px !important; }
.qa-box { background: rgb(8, 14, 35) !important; border: 1.5px solid rgb(55, 85, 160) !important; border-radius: 18px !important; padding: 14px !important; margin-top: 20px !important; }
div[data-testid="stSegmentedControl"] { background: rgb(8, 14, 35) !important; border: 1.5px solid rgb(55, 85, 160) !important; border-radius: 16px !important; padding: 6px !important; overflow-x: auto !important; }
div[data-testid="stSegmentedControl"] button { background: rgb(8, 14, 35) !important; color: rgb(255, 255, 255) !important; border: 1px solid rgb(55, 85, 160) !important; border-radius: 20px !important; font-weight: 700 !important; white-space: nowrap !important; }
div[data-testid="stSegmentedControl"] button[aria-checked="true"] { background: rgb(0, 160, 230) !important; color: rgb(255, 255, 255) !important; border: 1.5px solid rgb(120, 220, 255) !important; }
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
if "bot_seg" not in st.session_state:
    st.session_state.bot_seg = "LLM Bot"
if "qa_seg" not in st.session_state:
    st.session_state.qa_seg = None
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
        st.markdown("<div class='glass'><div class='brand-mini'>NEURODOCS</div><h2>Welcome Back</h2><p>Login to start your study with NeuroDocs AI. New here? The same form will create your account in 10 seconds. Your chats, progress, XP and favourites are saved safely with your PIN.</p></div>", unsafe_allow_html=True)
        name = st.text_input("Your Name", placeholder="e.g. Viraj")
        pin = st.text_input("Create or Enter 4 Digit PIN", type="password", placeholder="e.g. 1234", max_chars=4)
        goal_pick = st.selectbox("Your Goal", ["Top in Exam", "Learn Coding", "Board Exam", "Competitive Exam", "Learn English"])
        if st.button("Login or Signup - It is FREE", use_container_width=True):
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
                    st.success("Account Created. Welcome to NeuroDocs AI")
                    st.rerun()
            else:
                st.warning("Please enter your Name and 4 digit PIN")
        st.caption("Your PIN is safe. No one else can see your chats.")
    with lc2:
        st.markdown("<div class='glass'><div class='brand-mini'>NEURODOCS</div><h2>What You Get in NeuroDocs AI</h2><p>Unlimited Questions - Ask anything, get full answer with examples<br>YouTube Summary - Paste link, get summary, quiz and notes<br>PDF Chat with RAG - Upload PDF, ask questions only from your document<br>Mock Test + Timer - 5 MCQs in 5 minutes, exam practice<br>7-Day Study Plan - Full week plan with revision<br>Flashcards - Revise fast with Q and A cards<br>Previous Chats Saved - After 10 messages, old chat auto saves<br>Daily Goal + XP Points - Track streak and progress</p><p><b>How To Use NeuroDocs AI: 1. Login - 2. Ask a Question in Chat - 3. Make Quiz or Notes - 4. Top Your Exam</b></p></div>", unsafe_allow_html=True)
    st.stop()
st.markdown(f"""<div class='brand-shade'><div class='brand-mini'>NEURODOCS</div><div class='main-title'>🧠 NeuroDocs AI</div><div class='sub-title'>Welcome back, <b>{st.session_state.user}</b> - Goal: {st.session_state.goal} - Ask Anything - Learn From Your Videos - Powered by NeuroDocs AI</div></div>""", unsafe_allow_html=True)
a_real = st.session_state.analytics
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"<div class='stat-small'><span>Questions <b>{a_real['questions']}</b></span></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='stat-small'><span>Quizzes <b>{a_real['quizzes']}</b></span></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='stat-small'><span>Streak <b>{a_real['streak']}d</b></span></div>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='stat-small'><span>XP <b>{a_real['xp']}</b></span></div>", unsafe_allow_html=True)
st.markdown("<div class='spacer'></div>", unsafe_allow_html=True)
with st.sidebar:
    st.markdown(f"## Hi, {st.session_state.user}")
    st.caption("NeuroDocs AI - Your Study Buddy")
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
    st.markdown("<div class='glass-big'><div class='brand-mini'>NEURODOCS</div><h2>YouTube Study Room - Powered by NeuroDocs AI</h2><p>Watch, Understand, Quiz, Remember. All in one place in NeuroDocs AI. Paste any YouTube link, NeuroDocs AI will listen to the full video, make summary, quiz and notes from it. Best for school, college, coding and exam revision. No need to watch full video again and again.</p></div>", unsafe_allow_html=True)
    yt_url_input = st.text_input("Paste YouTube Link Here", placeholder="https://youtube.com/watch?v=...", key="yt_big_input")
    yt_url = yt_url_input
    st.markdown("<div class='spacer'></div>", unsafe_allow_html=True)
    c_yt1, c_yt2, c_yt3 = st.columns(3)
    with c_yt1:
        yt_summary_btn = st.button("Get Full Summary", use_container_width=True)
    with c_yt2:
        yt_quiz_btn = st.button("Make Quiz From Video", use_container_width=True)
    with c_yt3:
        yt_notes_btn = st.button("Make Notes", use_container_width=True)
    load_video_btn = st.button("Load Video", use_container_width=True)
    st.markdown("<div class='spacer'></div>", unsafe_allow_html=True)
    st.markdown("<div class='glass'><div class='brand-mini'>NEURODOCS</div><h3>Popular For Students - Tap To Try in NeuroDocs AI</h3><p>Pick a video below to start fast. NeuroDocs AI will load the video, read subtitles, and give you summary and quiz. Perfect if you want to test NeuroDocs AI without searching a link.</p></div>", unsafe_allow_html=True)
    e1, e2, e3 = st.columns(3)
    with e1:
        st.markdown("<div class='glass'><h3>Neural Networks</h3><p>AI - 15 min - Beginner<br>Best for: Class 11-12, College<br>Learn how AI thinks, neurons, layers and training in simple words.</p></div>", unsafe_allow_html=True)
        if st.button("Load This Video", key="yt_ex1"):
            st.session_state.yt_big_input = "https://www.youtube.com/watch?v=aircAruvnKk"
            st.rerun()
    with e2:
        st.markdown("<div class='glass'><h3>Photosynthesis</h3><p>Biology - 10 min - Class 10<br>Best for: Board Exam<br>Learn full process, equation, examples and exam questions.</p></div>", unsafe_allow_html=True)
        if st.button("Load This Video", key="yt_ex2"):
            st.session_state.yt_big_input = "https://www.youtube.com/watch?v=UPBMG5EYydo"
            st.rerun()
    with e3:
        st.markdown("<div class='glass'><h3>Python in 1 Video</h3><p>Coding - 20 min - Beginner<br>Best for: Coding Interview<br>Learn variables, loops, functions and full Python basics fast.</p></div>", unsafe_allow_html=True)
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
                st.session_state.bot_seg = "RAG Bot"
                st.session_state.analytics["summaries"] += 1
                st.session_state.analytics["xp"] += 10
                st.success("Video loaded in NeuroDocs AI. Now choose what you want below.")
                st.markdown("<div class='glass-big'><div class='brand-mini'>NEURODOCS</div><h3>What This Video Says - NeuroDocs AI Summary</h3></div>", unsafe_allow_html=True)
                st.write(text[:2500])
                st.markdown("Next Step: Go to Chat tab in NeuroDocs AI, Tap Quiz or Notes, Type the same topic, Full answer will come.")
            except Exception as e:
                st.error(f"This video has no subtitles. Try another video with CC. Error: {e}")
with tab_study:
    st.markdown("<div class='glass-big'><div class='brand-mini'>NEURODOCS</div><h3>Study Room - One Place, Everything in NeuroDocs AI</h3><p>No need to jump tabs. In NeuroDocs AI Study Room you can plan your day, track progress, save favourites and follow a simple system: Learn, Test, Revise. Study 25 minutes, take 5 minutes break, repeat. This is the best method to remember for long time and score high in exams.</p></div>", unsafe_allow_html=True)
    s1, s2 = st.columns(2)
    with s1:
        st.markdown("<div class='glass'><div class='brand-mini'>NEURODOCS</div><h3>Todays Focus - NeuroDocs AI</h3><p><b>Step 1:</b> Pick one topic, only one, do not mix 3 topics<br><b>Step 2:</b> Watch 10 min video in YouTube Study<br><b>Step 3:</b> Do 5 quiz in Chat tab<br><b>Step 4:</b> Revise notes next day<br><br>Done equals You win today. Small daily wins make big result in exam.</p></div>", unsafe_allow_html=True)
        focus_topic = st.text_input("What are you studying today?", placeholder="e.g. Photosynthesis")
        if st.button("Start My Study Session") and focus_topic:
            st.session_state.pending_action = "SUMMARY"
            st.session_state.analytics["xp"] += 5
            st.success(f"Started: {focus_topic}. Go to Chat tab and type {focus_topic}")
    with s2:
        st.markdown("<div class='glass'><div class='brand-mini'>NEURODOCS</div><h3>Your Study Progress - NeuroDocs AI</h3><p>Questions asked: " + str(st.session_state.analytics['questions']) + "<br>Quizzes done: " + str(st.session_state.analytics['quizzes']) + "<br>Notes made: " + str(st.session_state.analytics['notes']) + "<br><br><b>Smart Tip from NeuroDocs AI:</b> Do not study 3 hours straight. Study 25 min, 5 min break, Repeat. Your brain remembers more when you revise after 1 day.</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='glass'><div class='brand-mini'>NEURODOCS</div><h3>Quick Revision - 3 Steps in NeuroDocs AI</h3><p><b>1. Learn:</b> Watch video or read notes in NeuroDocs AI<br><b>2. Test:</b> Give quiz from same topic in Chat tab<br><b>3. Revise:</b> Read notes next day from Flashcards or Chat history<br><br>Learn, Test, Revise. Simple system for top marks.</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='glass'><div class='brand-mini'>NEURODOCS</div><h3>Save To Favourites - NeuroDocs AI</h3><p>Save topics you want to revise again in NeuroDocs AI. Favourites help you come back fast, without searching again. Example: Photosynthesis, Python Loops, History.</p></div>", unsafe_allow_html=True)
    fav_in = st.text_input("Add Favourite Topic", placeholder="e.g. Photosynthesis")
    if st.button("Add To Favourites") and fav_in:
        st.session_state.favourites.append(fav_in)
        st.success(f"Saved: {fav_in}")
    if st.session_state.favourites:
        st.write("Your Favourites: " + ", ".join(st.session_state.favourites))
with tab_exam:
    st.markdown("<div class='glass-big'><div class='brand-mini'>NEURODOCS</div><h3>Mock Test - Exam Mode in NeuroDocs AI</h3><p>Enter topic, Start Test, Go to Chat, Tap Quiz, NeuroDocs AI will give 5 MCQs. Timer runs here. This is real exam practice: 5 questions, 5 minutes, no cheating. After test, check answers with explanation in Chat, then revise weak topics. Repeat daily to increase speed and confidence.</p></div>", unsafe_allow_html=True)
    topic = st.text_input("Test Topic", placeholder="e.g. Photosynthesis, Python, History", key="exam_topic")
    exam_level = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
    if st.button("Start 5 MCQ Test - 5 Min") and topic:
        st.session_state.exam = {"topic": topic, "start": time.time(), "level": exam_level}
        st.info(f"Test started on {topic}, Level {exam_level}. Go to Chat tab in NeuroDocs AI.")
        st.balloons()
    if st.session_state.exam:
        elapsed = int(time.time() - st.session_state.exam["start"])
        left = max(0, 300 - elapsed)
        st.progress(left / 300)
        st.write(f"Time Left: {left//60}:{left%60:02d} | Topic: {st.session_state.exam['topic']}")
    else:
        st.info("Enter a topic above and start your test in NeuroDocs AI.")
with tab_plan:
    st.markdown("<div class='glass-big'><div class='brand-mini'>NEURODOCS</div><h3>7-Day Study Planner - NeuroDocs AI</h3><p>Enter your syllabus. NeuroDocs AI will make Day 1 to Day 7 plan with revision plus quiz every day. Each day has Topic, 2 Tasks, 30 min Revision and 1 Quiz. Perfect for Class 10 Science, Python Basics, History and any exam in 7 days. Download plan and follow daily.</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='glass'><div class='brand-mini'>NEURODOCS</div><h3>Popular Plans in NeuroDocs AI</h3><p>Class 10 Science - 5 Chapters - 7 Days<br>Python Basics - 7 Days - Beginner<br>History - Freedom Movement - 7 Days<br><br>Pick one idea above, type it below, NeuroDocs AI will make full plan.</p></div>", unsafe_allow_html=True)
    syllabus = st.text_input("Your Syllabus or Exam", placeholder="e.g. Class 10 Science - 5 Chapters, Exam in 7 days", key="plan_input")
    if st.button("Make My Plan") and syllabus:
        llm, _ = get_llm(model_choice, user_keys)
        if llm:
            prompt = f"Make a 7-day study plan for: {syllabus}. Language: {lang}. Give Day 1 to Day 7, each day: Topic, 2 Tasks, 30 min Revision, 1 Quiz. Keep simple."
            plan = llm.invoke(prompt).content
            st.markdown(plan)
            st.download_button("Download Plan", plan, file_name="NeuroDocs-Study-Plan.txt")
        else:
            st.warning("Add Groq Key in sidebar for AI Plan in NeuroDocs AI")
with tab_cards:
    st.markdown("<div class='glass-big'><div class='brand-mini'>NEURODOCS</div><h3>My Flashcards - NeuroDocs AI</h3><p>Flashcards help you remember fast. Create from Chat in NeuroDocs AI, Tap Create Cards, Type topic, Then revise here. Each card has Question and Answer. Tap Next Card, Shuffle, or I Know This. Daily 10 cards revision is enough to remember full chapter for exam.</p></div>", unsafe_allow_html=True)
    if st.session_state.flash_deck:
        idx = st.session_state.get("card_idx", 0) % len(st.session_state.flash_deck)
        card = st.session_state.flash_deck[idx]
        st.markdown(f"<div class='glass'><div class='brand-mini'>NEURODOCS</div><h3>{card}</h3><p>Card {idx+1} of {len(st.session_state.flash_deck)} in NeuroDocs AI. Try to answer in mind before checking answer, then tap Next.</p></div>", unsafe_allow_html=True)
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            if st.button("Next Card"):
                st.session_state.card_idx = idx + 1
                st.rerun()
        with cc2:
            if st.button("Shuffle"):
                random.shuffle(st.session_state.flash_deck)
                st.rerun()
        with cc3:
            if st.button("I Know This"):
                st.session_state.analytics["xp"] += 2
                st.session_state.card_idx = idx + 1
                st.rerun()
    else:
        st.info("No cards yet in NeuroDocs AI. Go to Chat, tap Create Cards and type a topic.")
        st.markdown("<div class='glass'><div class='brand-mini'>NEURODOCS</div><h3>Example Card - NeuroDocs AI</h3><p>Q: What is Photosynthesis?<br>A: Process by which plants make food using sunlight<br><br>This is how NeuroDocs AI flashcards look. Simple, short, easy to remember.</p></div>", unsafe_allow_html=True)
    st.caption(f"Total Cards in NeuroDocs AI: {len(st.session_state.flash_deck)}")
with tab_chat:
    auto_new_chat()
    st.markdown("<div class='bot-box'><div class='brand-mini'>NEURODOCS</div><h3>Choose Your Bot in NeuroDocs AI</h3><p><b>LLM Bot:</b> Ask anything, no file needed. Best for learning new topics, quiz, notes, summary.<br><b>RAG Bot:</b> Ask only from your PDF or YouTube video. Best for exam, document questions, exact answers from your file.<br>Tap one below, NeuroDocs AI will switch instantly.</p></div>", unsafe_allow_html=True)
    bot_choice = st.segmented_control("Bot", ["LLM Bot", "RAG Bot"], selection_mode="single", default=st.session_state.bot_seg, key="bot_seg")
    if bot_choice:
        st.session_state.bot_mode = bot_choice
        st.session_state.bot_seg = bot_choice
    if st.session_state.bot_mode == "LLM Bot":
        st.markdown("<div class='bot-active-cyan'>LLM BOT ACTIVE - NeuroDocs AI<br>Ask ANYTHING. No file needed. Type topic below and press Send.</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='bot-active-cyan'>RAG BOT ACTIVE - NeuroDocs AI<br>Works with PDF or YouTube video. Upload PDF below, then ask question from your document.</div>", unsafe_allow_html=True)
    st.markdown("<div class='spacer-big'></div>", unsafe_allow_html=True)
    st.markdown("<div class='bot-box'><div class='brand-mini'>NEURODOCS</div><h3>Quick Actions - NeuroDocs AI</h3><p>Tap one, then type your topic below. Chat auto saves after 10 messages in NeuroDocs AI.<br><b>Quiz:</b> 5 MCQs with answers + explanation<br><b>Cards:</b> 10 Flashcards for fast revision<br><b>Mind Map:</b> Main topic + 5 branches<br><b>Notes:</b> Exam notes with headings<br><b>Summary:</b> 8 to 10 points<br><b>Simple:</b> Easy story style</p></div>", unsafe_allow_html=True)
    qa_choice = st.segmented_control("Choose What You Want", ["Quiz", "Cards", "Mind Map", "Notes", "Summary", "Simple"], selection_mode="single", default=st.session_state.qa_seg, key="qa_seg")
    qa_map = {"Quiz": "QUIZ", "Cards": "CARDS", "Mind Map": "MINDMAP", "Notes": "NOTES", "Summary": "SUMMARY", "Simple": "SIMPLE"}
    qa_info = {
        "Quiz": "Quiz - 5 MCQs with 4 options + answers + full explanation",
        "Cards": "Cards - 10 Flashcards in Q and A format, revise fast",
        "Mind Map": "Mind Map - Main topic + 5 branches + 3 sub points each",
        "Notes": "Notes - Point wise exam notes with headings + examples",
        "Summary": "Summary - 8 to 10 points, short and full revision",
        "Simple": "Simple - 5 year old style, story + easy examples"
    }
    if qa_choice:
        st.session_state.pending_action = qa_map[qa_choice]
        if qa_choice == "Quiz":
            st.session_state.quiz = True
        if qa_choice == "Cards":
            st.session_state.flash = True
        if qa_choice == "Notes":
            st.session_state.notes = True
        if qa_choice == "Summary":
            st.session_state.summary = True
        if qa_choice == "Simple":
            st.session_state.simple = True
        st.markdown(f"<div class='bot-active'>Selected in NeuroDocs AI: {qa_info[qa_choice]}<br>Now type topic below and press Send.</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='bot-active'>Tap one option above in NeuroDocs AI, then type topic below.</div>", unsafe_allow_html=True)
    st.markdown("<div class='spacer-big'></div>", unsafe_allow_html=True)
    if st.session_state.pending_action:
        st.success(f"Selected in NeuroDocs AI: {st.session_state.pending_action} - Now type topic below and press Send.")
    if st.session_state.bot_mode == "RAG Bot":
        st.markdown("<div class='pdf-box'><b>NeuroDocs AI - RAG Document</b><br>Upload PDF for RAG Bot in NeuroDocs AI, or paste YouTube link in YouTube Study tab. NeuroDocs AI will read full PDF, make it searchable, and answer only from your document. Perfect for exam and notes.<br>Current doc: " + st.session_state.doc_name + "</div>", unsafe_allow_html=True)
        pdf_file = st.file_uploader("Upload PDF for RAG Chat in NeuroDocs AI", type=["pdf"], key="rag_pdf")
        if pdf_file is not None:
            if st.button("Load This PDF for RAG"):
                with st.spinner("Reading PDF in NeuroDocs AI..."):
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
                        st.session_state.bot_seg = "RAG Bot"
                        st.success(f"PDF Loaded in NeuroDocs AI: {pdf_file.name}. Now RAG Bot is ON. Ask question from PDF.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"PDF could not load in NeuroDocs AI. Error: {e}")
        if st.session_state.doc_name != "No Document":
            if st.button("Remove Document, Back to LLM"):
                st.session_state.vectorstore = load_saved_brain()
                st.session_state.doc_name = "No Document"
                st.session_state.bot_mode = "LLM Bot"
                st.session_state.bot_seg = "LLM Bot"
                st.rerun()
    st.markdown("<div class='spacer-big'></div>", unsafe_allow_html=True)
    st.markdown("<h3>Chat History - NeuroDocs AI</h3><p>Your questions and answers appear here in NeuroDocs AI. After 10 messages, old chat auto saves in sidebar.</p>", unsafe_allow_html=True)
    st.markdown("<div class='spacer'></div>", unsafe_allow_html=True)
    for msg in st.session_state.chat:
        if msg["role"] == "user":
            safe = msg["content"].replace("<", "").replace(">", "")[:2000]
            st.markdown(f"<div class='chat-user'><div class='chat-label'>YOU - NEURODOCS AI</div>{safe}</div>", unsafe_allow_html=True)
        else:
            safe = msg["content"].replace("<", "").replace(">", "")[:4000]
            st.markdown(f"<div class='chat-ai'><div class='chat-label'>NEURODOCS AI</div>{safe}</div>", unsafe_allow_html=True)
        st.markdown("<div class='spacer'></div>", unsafe_allow_html=True)
    st.markdown("<div class='spacer-big'></div>", unsafe_allow_html=True)
    st.markdown("<div class='qa-box'><div class='brand-mini'>NEURODOCS</div><h3>Ask Question - NeuroDocs AI</h3><p>Type or speak below in NeuroDocs AI. Only question answer here. You can type topic like Photosynthesis, Python, History, or speak with voice. NeuroDocs AI will give full answer with examples.</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='voice-box'><b>Talk With Voice - NeuroDocs AI</b> - Tap mic, speak, NeuroDocs AI will answer</div>", unsafe_allow_html=True)
    audio = st.audio_input("Ask by voice in NeuroDocs AI", key="voice_input")
    voice_text = ""
    if audio and groq_k:
        voice_text = transcribe_voice(audio.getvalue(), groq_k)
        if voice_text:
            st.success(f"You said in NeuroDocs AI: {voice_text}")
    user_input = st.chat_input("Type topic here in NeuroDocs AI... e.g. Photosynthesis")
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
        st.session_state.qa_seg = None
        st.session_state.chat.append({"role": "user", "content": prompt})
        save_chat("user", prompt)
        st.markdown(f"<div class='chat-user'><div class='chat-label'>YOU - NEURODOCS AI</div>{prompt}</div>", unsafe_allow_html=True)
        st.session_state.analytics["questions"] += 1
        st.session_state.analytics["xp"] += 5
        ans = "Please add Groq Key in sidebar (Free) in NeuroDocs AI - then I will answer."
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
            st.session
