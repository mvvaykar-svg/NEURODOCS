# NeuroDocs AI
import streamlit as st
import time, random, os, requests, base64, re, sqlite3, hashlib
from io import BytesIO
from src.llm import get_llm
from src.brain import build_brain_from_docs, load_saved_brain
from src.memory import init_db, load_chat, save_chat, clear_memory
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader

st.set_page_config(page_title="NeuroDocs AI", page_icon="🧠", layout="wide")

# ---------- API KEYS FROM SECRETS - AUTO ACTIVE ----------
GROQ_KEY = st.secrets.get("GROQ_API_KEY", "") if hasattr(st, "secrets") else ""
GEMINI_KEY = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else ""
if not GROQ_KEY:
    GROQ_KEY = os.environ.get("GROQ_API_KEY", "")

# ---------- USER DATABASE ----------
def get_user_db():
    conn = sqlite3.connect("users.db", check_same_thread=False)
    conn.execute("CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY, pin TEXT)")
    return conn
user_db = get_user_db()

# ---------- HELPER FUNCTIONS ----------
def build_prompt(question, mode, detail, lang, extra, bot_mode, context=""):
    detail_map = {1: "Answer in 1 line", 2: "Answer in short", 3: "Answer in detail", 4: "Answer in very detail with example", 5: "Answer like a full chapter with headings"}
    lang_map = {"English": "Answer in English", "Simple English": "Answer in very simple English"}
    detail_text = detail_map.get(detail, "Answer in detail")
    lang_text = lang_map.get(lang, "Answer in English")
    if bot_mode == "LLM Bot":
        return "You are NeuroDocs AI, a friendly tutor. Never give 1-word answer. Always explain with examples. Style: " + mode + ". Detail: " + detail_text + ". Language: " + lang_text + ". " + extra + " Question: " + question
    else:
        return "You are NeuroDocs AI RAG assistant. Answer ONLY from Context. If not found, say Not found in your document. Never stop in 1 word. Explain fully. Style: " + mode + ". Detail: " + detail_text + ". Language: " + lang_text + ". " + extra + " Context: " + context + " Question: " + question

def transcribe_voice(audio_bytes, groq_key):
    try:
        if not groq_key:
            return ""
        files = {"file": ("voice.wav", audio_bytes, "audio/wav")}
        data = {"model": "whisper-large-v3", "language": "en"}
        headers = {"Authorization": f"Bearer {groq_key}"}
        r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files, data=data, timeout=30)
        if r.status_code == 200:
            return r.json().get("text", "")
        return ""
    except:
        return ""

def call_groq_llm(prompt, groq_key):
    try:
        if not groq_key:
            return "API Key not found in Secrets. Please add GROQ_API_KEY in Streamlit Cloud > Settings > Secrets."
        headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 1500
        }
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data, timeout=60)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        else:
            return f"Groq Error: {r.text[:200]}"
    except Exception as e:
        return f"Error: {str(e)[:200]}"

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
    st.markdown("<audio autoplay='true'><source src='data:audio/mp3;base64," + b64 + "' type='audio/mp3'></audio>", unsafe_allow_html=True)

# ---------- CSS----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
header[data-testid="stHeader"] { background: rgba(2, 6, 20, 0.90) !important; }
.stApp { background: radial-gradient(600px 300px at 50% 0%, rgba(0, 210, 255, 0.16), transparent), rgb(2, 6, 20) !important; color: rgb(226, 236, 255) !important; font-family: 'Inter', sans-serif; }
h1,h2,h3 { color: white !important; font-weight: 800 !important; }
p, span, label { color: rgb(210, 224, 255) !important; }
.block-container { padding-top: 72px !important; max-width: 1120px !important; padding-left: 14px !important; padding-right: 14px !important; }
.spacer { height: 14px !important; }
.spacer-big { height: 22px !important; }
.brand-shade { background: radial-gradient(120px 40px at 20% 20%, rgba(0, 210, 255, 0.35) 0%, rgba(0,0,0,0) 70%), radial-gradient(140px 50px at 80% 30%, rgba(0, 90, 255, 0.40) 0%, rgba(0,0,0,0) 70%), radial-gradient(80px 30px at 50% 90%, rgba(0, 210, 255, 0.22) 0%, rgba(0,0,0,0) 70%), linear-gradient(135deg, rgb(0, 60, 180) 0%, rgb(0, 25, 80) 55%, rgb(4, 10, 30) 100%) !important; border: 1px solid rgb(0, 210, 255) !important; border-radius: 22px !important; padding: 24px 16px 20px 16px !important; text-align: center !important; margin-top: 6px !important; margin-bottom: 16px !important; box-shadow: 0 0 35px rgba(0, 210, 255, 0.18), 0 18px 45px rgba(0, 90, 255, 0.25) !important; }
.main-title { font-size: 34px !important; font-weight: 900 !important; color: white !important; margin: 0px !important; line-height: 1 !important; }
.sub-title { font-size: 13px !important; color: rgb(190, 225, 255) !important; font-weight: 600 !important; margin-top: 10px !important; line-height: 1.5 !important; }
.brand-mini { display: inline-block !important; background: rgb(0, 210, 255) !important; color: rgb(0, 20, 50) !important; font-weight: 900 !important; font-size: 11px !important; letter-spacing: 2.5px !important; padding: 5px 14px !important; border-radius: 20px !important; margin-bottom: 12px !important; }
.glass { background: linear-gradient(180deg, rgb(10, 22, 60), rgb(6, 10, 28)) !important; border: 1px solid rgb(0, 210, 255) !important; border-radius: 20px !important; padding: 18px !important; margin-bottom: 16px !important; box-shadow: 0 0 25px rgba(0, 210, 255, 0.12) !important; }
.glass-neon { background: radial-gradient(100px 35px at 20% 0%, rgba(0, 210, 255, 0.22) 0%, rgba(0,0,0,0) 70%), linear-gradient(180deg, rgb(10, 20, 55), rgb(6, 10, 28)) !important; border: 1px solid rgb(0, 210, 255) !important; border-radius: 20px !important; padding: 18px !important; margin-bottom: 16px !important; box-shadow: 0 0 28px rgba(0, 210, 255, 0.12) !important; }
.glass-royal { background: linear-gradient(135deg, rgb(0, 45, 140), rgb(8, 12, 35)) !important; border: 1px solid rgb(90, 170, 255) !important; border-radius: 20px !important; padding: 18px !important; margin-bottom: 16px !important; box-shadow: 0 14px 32px rgba(0, 90, 255, 0.20) !important; }
.glass-cyan { background: linear-gradient(135deg, rgb(0, 110, 190), rgb(6, 12, 32)) !important; border: 1px solid rgb(120, 225, 255) !important; border-radius: 20px !important; padding: 18px !important; margin-bottom: 16px !important; }
.tip-box { background: rgb(8, 14, 35) !important; border-left: 4px solid rgb(0, 210, 255) !important; border-radius: 12px !important; padding: 12px 14px !important; margin-bottom: 16px !important; }
.voice-box { background: rgb(8, 18, 50) !important; border: 1px solid rgb(0, 180, 255) !important; border-radius: 16px !important; padding: 13px !important; text-align: center !important; margin-bottom: 14px !important; margin-top: 10px !important; }
.voice-box b, .voice-box p { color: white !important; font-size: 13px !important; }
.stButton>button { background: linear-gradient(135deg, rgb(0, 90, 210), rgb(0, 180, 255)) !important; color: white !important; font-weight: 700 !important; border-radius: 14px !important; border: none !important; padding: 11px 8px !important; font-size: 13px !important; width: 100% !important; margin-bottom: 6px !important; white-space: normal !important; line-height: 1.25 !important; min-height: 46px !important; box-shadow: 0 8px 20px rgba(0, 180, 255, 0.30) !important; }
.stButton>button:hover { transform: scale(1.02) !important; border: 1px solid rgb(0, 210, 255) !important; background: rgb(0, 70, 180) !important; }
.stTextInput>div>div>input, .stTextArea>div>div>textarea { background: rgb(5, 9, 25) !important; color: white !important; border-radius: 13px !important; border: 1px solid rgb(60, 110, 190) !important; }
[data-testid="stSidebar"] { background: rgb(3, 6, 20) !important; border-right: 1px solid rgb(45, 95, 180); }
div[data-testid="stTabs"] button { background: rgb(8, 14, 35) !important; color: rgb(210,225,255) !important; border: 1px solid rgb(45, 95, 180) !important; border-radius: 12px !important; font-weight: 700 !important; padding: 8px 10px !important; white-space: nowrap !important; }
div[data-testid="stTabs"] button[aria-selected="true"] { background: rgb(0, 180, 255) !important; color: rgb(0, 20, 50) !important; border: 1px solid rgb(150, 230, 255) !important; }
.chat-user { background: linear-gradient(135deg, rgb(0, 90, 210), rgb(10, 25, 75)) !important; border: 1px solid rgb(90, 180, 255) !important; border-radius: 16px !important; padding: 12px 14px !important; margin: 10px 0px 10px 10px !important; font-size: 13.5px !important; color: white !important; }
.chat-ai { background: rgb(8, 14, 35) !important; border: 1px solid rgb(45, 95, 180) !important; border-left: 4px solid rgb(0, 210, 255) !important; border-radius: 16px !important; padding: 12px 14px !important; margin: 10px 10px 10px 0px !important; font-size: 13.5px !important; color: rgb(226,236,255) !important; }
.chat-label { font-size: 10px !important; font-weight: 900 !important; color: rgb(0, 210, 255) !important; margin-bottom: 5px !important; letter-spacing: 1.2px !important; }
.login-hero { margin-top: 10px; padding: 28px 20px 22px 20px; background: radial-gradient(150px 50px at 20% 10%, rgba(0,210,255,0.30) 0%, rgba(0,0,0,0) 70%), linear-gradient(180deg, rgb(0, 50, 150), rgb(4, 8, 22)); border: 1px solid rgb(0, 210, 255); border-radius: 26px; text-align: center; box-shadow: 0 20px 45px rgba(0, 140, 255, 0.25); }
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

# ---------- SESSION STATE ----------
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
if "mic_text" not in st.session_state:
    st.session_state.mic_text = ""
if "yt_link" not in st.session_state:
    st.session_state.yt_link = ""
if "selected_video" not in st.session_state:
    st.session_state.selected_video = ""

def save_current_session():
    if st.session_state.chat:
        title = st.session_state.chat[0]["content"][:35] if st.session_state.chat else "New Chat"
        if st.session_state.current_session_idx is not None and st.session_state.current_session_idx < len(st.session_state.chat_sessions):
            st.session_state.chat_sessions[st.session_state.current_session_idx] = {"title": title, "messages": list(st.session_state.chat)}
        else:
            st.session_state.chat_sessions.append({"title": title, "messages": list(st.session_state.chat)})
            st.session_state.current_session_idx = len(st.session_state.chat_sessions)-1

def ask_ai(question, mode="Simple Explain", detail=3, lang="Simple English", extra="", bot_mode="LLM Bot", context=""):
    prompt = build_prompt(question, mode, detail, lang, extra, bot_mode, context)
    return call_groq_llm(prompt, GROQ_KEY)

def auto_new_chat():
    if len(st.session_state.chat) >= 10:
        save_current_session()
        st.session_state.chat = []
        st.session_state.current_session_idx = None
        clear_memory()
        st.toast("Old chat saved in memory. New chat started.")

# ---------- LOGIN SCREEN ----------
if not st.session_state.user:
    st.markdown("<div class='login-hero'><div class='brand-mini'>NEURODOCS</div><h1>NeuroDocs AI</h1><p>Learn Anything, From Anywhere<br>Your Personal AI Study Buddy<br><br>Unlimited Questions - YouTube Summary - PDF Chat - Mock Test - Flashcards - Study Plan<br>100 Percent Free, No Fees</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='spacer'></div>", unsafe_allow_html=True)
    if st.button("🚀 One Click Login - Direct Entry (No Password Needed)", key="direct_login_btn_main", use_container_width=True):
        st.session_state.user = "Viraj"
        st.session_state.goal = "Top in Exam"
        st.success("Welcome Viraj! API Key Active from Secrets")
        time.sleep(0.5)
        st.rerun()
    st.markdown("<p style='text-align:center;opacity:0.7'>— OR —</p>", unsafe_allow_html=True)
    lc1, lc2 = st.columns([1.2, 1])
    with lc1:
        st.markdown("<div class='glass-neon'><h2>Welcome Back</h2><p>Login to start your study journey with NeuroDocs AI. New here? Same form will create your account in 10 seconds. Use any password you want, long or short, your choice. Your chats, progress, XP and favourites are saved safely.</p></div>", unsafe_allow_html=True)
        name = st.text_input("Your Name", placeholder="e.g. Viraj", key="login_name_input")
        pin = st.text_input("Create Any Password - Any Length", type="password", placeholder="e.g. mysecret123", key="login_pin_input")
        goal_pick = st.selectbox("Your Goal", ["Top in Exam", "Learn Coding", "Board Exam", "Competitive Exam", "Learn English"], key="login_goal_select")
        if st.button("Login or Signup - It is FREE", key="login_signup_btn_main", use_container_width=True):
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
        if GROQ_KEY:
            st.success("API Key Active from Secrets - Ready to Use")
        else:
            st.warning("API Key not found in Secrets. Add GROQ_API_KEY in Secrets.")
    with lc2:
        st.markdown("<div class='glass-royal'><h2>What You Get</h2><p>Unlimited Questions - Ask anything, get full answer with examples<br>YouTube Summary - Paste link, get summary, quiz and notes<br>PDF Chat with RAG - Upload PDF, ask questions only from your document<br>Mock Test + Timer - 5 MCQs in 5 minutes<br>7-Day Study Plan - Full week plan with revision<br>Flashcards - Revise fast with Q and A cards<br>Previous Chats Saved - After 10 messages, old chat auto saves<br>Daily Goal + XP Points - Track streak and progress</p><p><b>How To Use: 1. Login - 2. Ask a Question in Chat - 3. Make Quiz or Notes - 4. Top Your Exam</b></p></div>", unsafe_allow_html=True)
    st.stop()

# ---------- HEADER ----------
level = "Beginner"
if st.session_state.analytics["xp"] >= 100:
    level = "Advanced"
elif st.session_state.analytics["xp"] >= 50:
    level = "Intermediate"
elif st.session_state.analytics["xp"] >= 20:
    level = "Learning"
header_html = "<div class='brand-shade'><div class='brand-mini'>NEURODOCS</div><div class='main-title'>NeuroDocs AI</div><div class='sub-title'>Welcome back, <b>" + str(st.session_state.user) + "</b> - Level: " + level + " - Goal: " + str(st.session_state.goal) + "<br>Ask Anything - Learn From Your Videos</div></div>"
st.markdown(header_html, unsafe_allow_html=True)
a_real = st.session_state.analytics
stats_html = "<div class='stats-row'><div class='stat-card'><b>" + str(a_real["questions"]) + "</b><span>Questions</span></div><div class='stat-card'><b>" + str(a_real["quizzes"]) + "</b><span>Quizzes</span></div><div class='stat-card'><b>" + str(a_real["streak"]) + "d</b><span>Streak</span></div><div class='stat-card stat-cyan'><b>" + str(a_real["xp"]) + "</b><span>XP Points</span></div></div>"
st.markdown(stats_html, unsafe_allow_html=True)
tips = ["Small daily wins make big exam results. Study 25 min, take 5 min break.", "Do not read 3 hours straight. Revise after 1 day, your brain remembers more.", "Topper secret: Learn, Test, Revise. Same topic, 3 times, 3 days.", "One topic at a time. Finish one, then start next. Do not mix."]
tip = tips[a_real["questions"] % len(tips)]
st.markdown("<div class='tip-box'><b>Tip of the Day:</b> " + tip + "</div>", unsafe_allow_html=True)

# ---------- SIDEBAR ----------
with st.sidebar:
    st.markdown("## Hi, " + str(st.session_state.user))
    st.caption("Level: " + level + " - NeuroDocs AI")
    if st.button("Logout", key="logout_btn_main"):
        save_current_session()
        st.session_state.user = None
        st.rerun()
    st.markdown("## API Status")
    if GROQ_KEY:
        st.success("Groq Key Active (Secrets)")
    else:
        st.error("Groq Key Missing")
        st.caption("Add GROQ_API_KEY in Secrets")
        manual_key = st.text_input("Or Paste Key Here", type="password", key="manual_groq_key")
        if manual_key:
            GROQ_KEY = manual_key
            st.success("Key Set!")
    st.markdown("[Get Free Groq Key](https://console.groq.com)")
    st.divider()
    st.markdown("## My Daily Goal")
    st.write("Goal: " + str(st.session_state.goal))
    daily_done = st.slider("Today Progress Percent", 0, 100, 20, key="daily_slider_main")
    st.progress(daily_done / 100)
    st.caption(str(daily_done) + " percent done today. Keep going.")
    st.divider()
    st.markdown("## Previous Chats")
    if st.button("New Chat", key="new_chat_btn_main", use_container_width=True):
        save_current_session()
        st.session_state.chat = []
        st.session_state.current_session_idx = None
        st.rerun()
    if not st.session_state.chat_sessions and not st.session_state.chat:
        st.caption("No previous chats yet. Start a new chat in NeuroDocs AI.")
    for idx, sess in enumerate(st.session_state.chat_sessions):
        col_a, col_b = st.columns([4, 1])
        with col_a:
            if st.button(sess["title"][:28], key="open_" + str(idx), use_container_width=True):
                save_current_session()
                st.session_state.chat = list(sess["messages"])
                st.session_state.current_session_idx = idx
                st.rerun()
        with col_b:
            if st.button("Delete", key="del_" + str(idx), help="Delete this chat"):
                del st.session_state.chat_sessions[idx]
                if st.session_state.current_session_idx == idx:
                    st.session_state.chat = []
                    st.session_state.current_session_idx = None
                st.rerun()
    if st.session_state.chat_sessions:
        if st.button("Delete All Chats", key="delete_all_chats_main", use_container_width=True):
            st.session_state.chat_sessions = []
            st.session_state.chat = []
            st.session_state.current_session_idx = None
            st.rerun()
# ---------- SETTINGS ----------
col_s1, col_s2, col_s3, col_s4 = st.columns(4)
with col_s1:
    bot_mode = st.selectbox("Bot Mode", ["LLM Bot", "RAG Bot (PDF)"], key="bot_mode_select_main")
    st.session_state.bot_mode = bot_mode
with col_s2:
    mode = st.selectbox("Style", ["Simple Explain", "Story Mode", "Exam Mode", "Funny Mode"], key="style_select_main")
with col_s3:
    detail = st.slider("Detail Level", 1, 5, 3, key="detail_slider_main")
with col_s4:
    lang = st.selectbox("Language", ["Simple English", "English"], key="lang_select_main")

# ---------- TABS ----------
tab_chat, tab_tools, tab_pdf, tab_videos = st.tabs(["Chat", "Tools", "PDF Chat", "Videos"])

with tab_chat:
    st.markdown("**Quick Ask:**")
    q1, q2, q3, q4 = st.columns(4)
    with q1:
        if st.button("Photosynthesis", key="quick_photo_btn"):
            st.session_state.quick_prompt = "Explain Photosynthesis in simple English with example"
            st.rerun()
    with q2:
        if st.button("Pythagoras Theorem", key="quick_pytha_btn"):
            st.session_state.quick_prompt = "Explain Pythagoras Theorem with example"
            st.rerun()
    with q3:
        if st.button("Human Brain", key="quick_brain_btn"):
            st.session_state.quick_prompt = "Explain Human Brain in simple English"
            st.rerun()
    with q4:
        if st.button("Solar System", key="quick_solar_btn"):
            st.session_state.quick_prompt = "Explain Solar System in simple English"
            st.rerun()
    for msg in st.session_state.chat:
        if msg["role"] == "user":
            st.markdown(f"<div class='chat-user'><div class='chat-label'>YOU</div>{msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='chat-ai'><div class='chat-label'>NEURODOCS AI</div>{msg['content']}</div>", unsafe_allow_html=True)
    user_q = st.text_input("Ask anything... e.g. What is Photosynthesis?", value=st.session_state.quick_prompt, key="main_chat_input_main")
    if st.session_state.quick_prompt:
        st.session_state.quick_prompt = ""
    st.markdown("<div class='tip-box'><b>Speak and Ask - Mic Fixed</b><br>Press mic below, speak, it will automatically go to chat.</div>", unsafe_allow_html=True)
    audio = st.audio_input("Press mic and speak...", key="mic_main_input_fixed")
    if audio is not None:
        audio_bytes = audio.read()
        if audio_bytes and len(audio_bytes) > 100:
            with st.spinner("Listening..."):
                voice_text = transcribe_voice(audio_bytes, GROQ_KEY)
            if voice_text:
                st.success(f"You Said: {voice_text}")
                st.session_state.chat.append({"role": "user", "content": voice_text})
                with st.spinner("Thinking..."):
                    ans = ask_ai(voice_text, mode, detail, lang, "", bot_mode)
                st.session_state.chat.append({"role": "assistant", "content": ans})
                st.session_state.analytics["questions"] += 1
                st.session_state.analytics["xp"] += 5
                st.rerun()
            else:
                st.warning("Voice not understood. Please speak again or check API Key.")
        else:
            st.info("Recording is too short. Please speak longer.")
    if st.button("Send / Ask", key="send_chat_btn_main", use_container_width=True):
        if user_q.strip():
            st.session_state.chat.append({"role": "user", "content": user_q})
            with st.spinner("NeuroDocs is thinking..."):
                context = ""
                if bot_mode == "RAG Bot (PDF)" and st.session_state.vectorstore is not None:
                    try:
                        docs = st.session_state.vectorstore.similarity_search(user_q, k=3)
                        context = "\n".join([d.page_content[:1500] for d in docs])
                    except:
                        context = ""
                ans = ask_ai(user_q, mode, detail, lang, "", bot_mode, context)
            st.session_state.chat.append({"role": "assistant", "content": ans})
            st.session_state.analytics["questions"] += 1
            st.session_state.analytics["xp"] += 5
            auto_new_chat()
            st.rerun()
        else:
            st.warning("Please write something or speak first!")
    c_voice1, c_voice2 = st.columns(2)
    with c_voice1:
        st.session_state.voice_on = st.checkbox("Voice Answer On", value=st.session_state.voice_on, key="voice_toggle_main")
    with c_voice2:
        if st.button("Listen Last Answer", key="speak_last_btn_main"):
            if st.session_state.chat and st.session_state.chat[-1]["role"] == "assistant":
                audio_bytes = speak_text(st.session_state.chat[-1]["content"])
                if audio_bytes:
                    autoplay_audio(audio_bytes)
                    st.success("Playing...")
                else:
                    st.warning("Voice could not be created.")
            else:
                st.info("First ask a question.")

with tab_tools:
    st.markdown("### All Tools - Result Will Come Directly in Chat")
    topic = st.text_input("Write Topic - e.g. Photosynthesis, Human Brain", placeholder="Topic...", key="tool_topic_input_main")
    t1, t2, t3 = st.columns(3)
    with t1:
        if st.button("Make Quiz (5 MCQs)", key="tool_quiz_btn_main"):
            use_topic = topic.strip() if topic.strip() else "General Knowledge"
            with st.spinner("Making Quiz..."):
                q = f"Make 5 MCQs on {use_topic}. Each with 4 options A,B,C,D and correct answer at end. Simple English."
                ans = ask_ai(q, mode, 4, lang, "", "LLM Bot")
            st.session_state.chat.append({"role": "user", "content": f"Make Quiz on {use_topic}"})
            st.session_state.chat.append({"role": "assistant", "content": f"**Quiz on {use_topic}**\n\n{ans}"})
            st.session_state.analytics["quizzes"] += 1
            st.session_state.analytics["xp"] += 10
            st.success("Quiz created! Check Chat tab.")
            st.rerun()
    with t2:
        if st.button("Make Summary", key="tool_summary_btn_main"):
            use_topic = topic.strip() if topic.strip() else "Photosynthesis"
            with st.spinner("Making Summary..."):
                q = f"Make summary of {use_topic} in 10 simple points with headings. Simple English."
                ans = ask_ai(q, mode, 4, lang, "", "LLM Bot")
            st.session_state.chat.append({"role": "user", "content": f"Make Summary of {use_topic}"})
            st.session_state.chat.append({"role": "assistant", "content": f"**Summary - {use_topic}**\n\n{ans}"})
            st.session_state.analytics["summaries"] += 1
            st.session_state.analytics["xp"] += 8
            st.success("Summary created! Check Chat tab.")
            st.rerun()
    with t3:
        if st.button("Make Notes", key="tool_notes_btn_main"):
            use_topic = topic.strip() if topic.strip() else "Photosynthesis"
            with st.spinner("Making Notes..."):
                q = f"Make exam notes on {use_topic} with headings, definitions, examples, important points. Simple English."
                ans = ask_ai(q, mode, 5, lang, "", "LLM Bot")
            st.session_state.chat.append({"role": "user", "content": f"Make Notes on {use_topic}"})
            st.session_state.chat.append({"role": "assistant", "content": f"**Notes - {use_topic}**\n\n{ans}"})
            st.session_state.analytics["notes"] += 1
            st.session_state.analytics["xp"] += 8
            st.success("Notes created! Check Chat tab.")
            st.rerun()
    t4, t5, t6 = st.columns(3)
    with t4:
        if st.button("Flashcards", key="tool_flash_btn_main"):
            use_topic = topic.strip() if topic.strip() else "Human Brain"
            with st.spinner("Making Flashcards..."):
                q = f"Make 8 flashcards on {use_topic}. Format: Q: ... A: ... Simple English."
                ans = ask_ai(q, mode, 3, lang, "", "LLM Bot")
            st.session_state.chat.append({"role": "user", "content": f"Make Flashcards on {use_topic}"})
            st.session_state.chat.append({"role": "assistant", "content": f"**Flashcards - {use_topic}**\n\n{ans}"})
            st.session_state.analytics["xp"] += 8
            st.success("Flashcards created! Check Chat tab.")
            st.rerun()
    with t5:
        if st.button("7-Day Study Plan", key="tool_plan_btn_main"):
            use_topic = topic.strip() if topic.strip() else "Board Exam"
            with st.spinner("Making Plan..."):
                q = f"Make 7-day study plan for {use_topic} with daily tasks, revision, test. Simple English. Goal: {st.session_state.goal}"
                ans = ask_ai(q, mode, 5, lang, "", "LLM Bot")
            st.session_state.chat.append({"role": "user", "content": f"Make 7-Day Plan for {use_topic}"})
            st.session_state.chat.append({"role": "assistant", "content": f"**7-Day Plan - {use_topic}**\n\n{ans}"})
            st.session_state.analytics["xp"] += 10
            st.success("Plan created! Check Chat tab.")
            st.rerun()
    with t6:
        if st.button("Mind Map", key="tool_mind_btn_main"):
            use_topic = topic.strip() if topic.strip() else "Photosynthesis"
            with st.spinner("Making Mind Map..."):
                q = f"Make mind map for {use_topic} in tree format with branches. Simple English."
                ans = ask_ai(q, mode, 4, lang, "", "LLM Bot")
            st.session_state.chat.append({"role": "user", "content": f"Make Mind Map of {use_topic}"})
            st.session_state.chat.append({"role": "assistant", "content": f"**Mind Map - {use_topic}**\n\n{ans}"})
            st.session_state.analytics["xp"] += 8
            st.success("Mind Map created! Check Chat tab.")
            st.rerun()
    st.divider()
    st.markdown("### YouTube Summary - From Link")
    yt_link = st.text_input("Paste YouTube Link", placeholder="https://youtube.com/watch?v=...", key="yt_link_input_main")
    if st.button("Get YouTube Summary + Quiz + Notes", key="yt_summary_btn_main", use_container_width=True):
        if not yt_link.strip():
            st.warning("Please paste YouTube Link first!")
        else:
            with st.spinner("Making summary from video..."):
                video_id = ""
                try:
                    if "v=" in yt_link:
                        video_id = yt_link.split("v=")[-1].split("&")[0].split("?")[0]
                    elif "youtu.be/" in yt_link:
                        video_id = yt_link.split("youtu.be/")[-1].split("?")[0]
                    else:
                        video_id = yt_link.strip()
                except:
                    video_id = ""
                transcript_text = ""
                try:
                    from youtube_transcript_api import YouTubeTranscriptApi
                    if video_id:
                        transcript = YouTubeTranscriptApi.get_transcript(video_id)
                        transcript_text = " ".join([x['text'] for x in transcript[:150]])
                except:
                    transcript_text = ""
                if transcript_text:
                    prompt = f"Summarize this video transcript in 10 simple points, then make 5 MCQs and short notes. Simple English. Transcript: {transcript_text[:3500]}"
                else:
                    prompt = f"YouTube video link is {yt_link}. Transcript not available. Make a general summary, 5 MCQs and notes about this topic based on video link. Simple English."
                ans = ask_ai(prompt, mode, 5, lang, "", "LLM Bot")
                st.session_state.chat.append({"role": "user", "content": f"Summarize this YouTube video: {yt_link}"})
                st.session_state.chat.append({"role": "assistant", "content": f"**YouTube Summary**\nLink: {yt_link}\n\n{ans}"})
                st.session_state.analytics["summaries"] += 1
                st.session_state.analytics["xp"] += 10
                st.success("YouTube Summary created! Check Chat tab.")
                st.rerun()

with tab_pdf:
    st.markdown("### PDF Chat - RAG Bot")
    st.markdown(f"**Current Document:** {st.session_state.doc_name}")
    st.markdown("<div class='pdf-box'>Upload PDF - Then ask questions from RAG Bot, answer will come only from your PDF</div>", unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload PDF", type=["pdf"], key="pdf_uploader_main_fixed")
    if uploaded is not None:
        if st.button("Build Brain From PDF", key="build_brain_btn_main"):
            with st.spinner("Reading PDF, building brain..."):
                try:
                    with open("temp_upload.pdf", "wb") as f:
                        f.write(uploaded.read())
                    loader = PyPDFLoader("temp_upload.pdf")
                    docs = loader.load()
                    vs = build_brain_from_docs(docs)
                    if vs is not None:
                        st.session_state.vectorstore = vs
                        st.session_state.doc_name = uploaded.name
                        st.session_state.bot_mode = "RAG Bot (PDF)"
                        st.success(f"Brain Ready! Now ask from RAG Bot. Document: {uploaded.name}")
                    else:
                        text_all = "\n".join([d.page_content for d in docs[:10]])
                        st.session_state.doc_name = uploaded.name
                        st.session_state.chat.append({"role": "assistant", "content": f"PDF Loaded: {uploaded.name}\n\nFirst 2000 chars:\n{text_all[:2000]}"})
                        st.success("PDF Loaded! Ask in Chat tab.")
                    st.rerun()
                except Exception as e:
                    st.error(f"PDF Error: {str(e)[:300]}")
                    st.info("Tip: PDF should be less than 10MB and text PDF, not photo PDF.")
    st.divider()
    st.markdown("**Ask from PDF - Answer will come only from PDF**")
    rag_q = st.text_input("Ask question from PDF...", key="rag_q_input_main")
    if st.button("Ask From PDF", key="rag_ask_btn_main"):
        if not rag_q.strip():
            st.warning("Please write question first!")
        elif st.session_state.vectorstore is None and st.session_state.doc_name == "No Document":
            st.warning("Please upload PDF first!")
        else:
            with st.spinner("Searching in PDF..."):
                context = ""
                try:
                    if st.session_state.vectorstore is not None:
                        docs = st.session_state.vectorstore.similarity_search(rag_q, k=3)
                        context = "\n".join([d.page_content[:1500] for d in docs])
                except:
                    context = ""
                ans = ask_ai(rag_q, mode, detail, lang, "", "RAG Bot", context)
            st.session_state.chat.append({"role": "user", "content": f"[PDF] {rag_q}"})
            st.session_state.chat.append({"role": "assistant", "content": ans})
            st.session_state.analytics["questions"] += 1
            st.session_state.analytics["xp"] += 5
            st.success("Answer is in Chat! Check Chat tab.")
            st.rerun()

with tab_videos:
    st.markdown("### Learn From Videos")
    st.caption("Click on video - Summary + Quiz will come directly in Chat")
    videos = [
        {"title": "Neural Networks - Full Course", "desc": "What is Neural Network? Learn from scratch.", "url": "https://www.youtube.com/watch?v=aircAruvnKk", "tag": "AI"},
        {"title": "Photosynthesis - Simple Explain", "desc": "Class 10 Science - Photosynthesis in 10 min.", "url": "https://www.youtube.com/watch?v=UPBMG5EYydo", "tag": "Science"},
        {"title": "Pythagoras Theorem", "desc": "Maths - Pythagoras with examples.", "url": "https://www.youtube.com/watch?v=AA6RfgP-AHU", "tag": "Maths"},
        {"title": "Human Brain Explained", "desc": "How does brain work? Simple explanation.", "url": "https://www.youtube.com/watch?v=kMK4pWcI0s8", "tag": "Science"},
        {"title": "Python for Beginners", "desc": "Learn Python in 1 hour - Full course.", "url": "https://www.youtube.com/watch?v=_uQrJ0TkZlc", "tag": "Coding"},
        {"title": "Solar System", "desc": "All planets explained simply.", "url": "https://www.youtube.com/watch?v=libKVRa01L8", "tag": "Science"},
    ]
    search_v = st.text_input("Search Video...", key="video_search_input_main")
    filtered = videos
    if search_v.strip():
        filtered = [v for v in videos if search_v.lower() in v["title"].lower() or search_v.lower() in v["tag"].lower()]
    if not filtered:
        st.info("No video found. Try another name.")
    for i, video in enumerate(filtered):
        st.markdown(f"<div class='glass'><h3>{video['title']}</h3><p>{video['desc']} | Tag: {video['tag']}</p></div>", unsafe_allow_html=True)
        vc1, vc2, vc3 = st.columns(3)
        vid_id = video["url"][-11:] if len(video["url"]) >= 11 else str(i)
        with vc1:
            if st.button("Load This Video", key=f"load_video_{i}_{vid_id}"):
                st.session_state.selected_video = video["url"]
                st.video(video["url"])
                st.success("Video Loaded!")
        with vc2:
            if st.button("Summary", key=f"video_summary_{i}_{vid_id}"):
                with st.spinner("Making Summary..."):
                    ans = ask_ai(f"Make summary of {video['title']} in 10 points. Simple English.", mode, 4, lang, "", "LLM Bot")
                st.session_state.chat.append({"role": "user", "content": f"Summary of {video['title']}"})
                st.session_state.chat.append({"role": "assistant", "content": f"**{video['title']}**\n\n{ans}"})
                st.success("Summary is in Chat! Check Chat tab.")
                st.rerun()
        with vc3:
            if st.button("Quiz", key=f"video_quiz_{i}_{vid_id}"):
                with st.spinner("Making Quiz..."):
                    ans = ask_ai(f"Make 5 MCQs on {video['title']} with options and answers. Simple English.", mode, 4, lang, "", "LLM Bot")
                st.session_state.chat.append({"role": "user", "content": f"Quiz on {video['title']}"})
                st.session_state.chat.append({"role": "assistant", "content": f"**Quiz - {video['title']}**\n\n{ans}"})
                st.session_state.analytics["quizzes"] += 1
                st.session_state.analytics["xp"] += 10
                st.success("Quiz is in Chat! Check Chat tab.")
                st.rerun()
    if st.session_state.selected_video:
        st.divider()
        st.markdown("### Now Playing")
        st.video(st.session_state.selected_video)

st.divider()
st.markdown("<p style='text-align:center;opacity:0.7'>Made with Love by Viraj - D.R High School, Nandurbar | NeuroDocs AI - 2026</p>", unsafe_allow_html=True)
