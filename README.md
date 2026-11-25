# 🧠 NeuroDocs AI

> Your Universal AI Assistant — Ask Anything, Learn From Your Files.

## 📖 About
NeuroDocs AI is a smart AI learning assistant for students. Ask ANY question like ChatGPT, or upload your PDF / URL / Notes and ask questions only from that. Make Quiz, Flashcards, Mind Map, Summary, Notes in 1 click.

## ✨ Features
- 🧠 LLM Bot - Unlimited General Knowledge
- 📚 RAG Bot - Answer From YOUR Document Only
- 🌐 URL Support - Add Multiple Websites
- 📄 PDF Upload - Read Any PDF
- ✍️ Paste Text Support
- 🎯 Quiz - 5 MCQ + Answers
- 🗂️ Cards - 5 Flashcards
- 🗺️ Mind Map - Tree Structure
- 📝 Summary - 5 Points Summary
- 💡 Simple - Explain Like 10 Year Old
- 📓 Notes - Clean Exam Notes
- 📏 5 Detail Levels - 1 Line To Full Chapter
- 🎭 4 Learning Styles - Normal / 5 Year Old / Exam / Simple English
- 💾 Chat Memory - Saved in SQLite
- 📄 Download Notes - Full Chat as .txt

## 🤖 Two Bot Modes
### 1. LLM Bot - Ask Anything
No file needed. Ask Science, Coding, History, Homework, Life.

### 2. RAG Bot - Learn From Your File
Upload PDF / Paste URL / Paste Text. Answers ONLY from your file. No extra info.

## ⚡ Quick Actions
| Tool | Output |
| --- | --- |
| 🎯 Quiz | 5 MCQ + Answers |
| 🗂️ Cards | 5 Flashcards |
| 🗺️ Mind Map | Tree Structure |
| 📝 Summary | 5 Points Summary |
| 💡 Simple | Very Simple Explain |
| 📓 Notes | Clean Exam Notes |

## 🛠️ Tech Stack
- Frontend: Streamlit
- Backend: Python
- AI Framework: LangChain
- LLM: Groq GPT-OSS 20B / 120B, Gemini 2.0 Flash, OpenAI GPT-4o-mini
- Vector DB: FAISS
- Document Loader: PyPDFLoader, WebBaseLoader
- Database: SQLite

## 📁 Project Structure
NEURODOCS 
├── http://app.py
├── http://requirements.txt
├── http://README.md
├── src/
       ├── http://llm.py
       ├── http://brain.py
       └── http://memory.py

##⚙️ How It Works
- 1. User Selects Bot Mode
- 2. If RAG Bot - Docs -> Chunks -> FAISS Vectorstore
- 3. User Taps Quick Action - Extra Prompt Added
- 4. User Asks Question - similarity_search(k=3) -> Context
- 5. Final Prompt = Style + Detail + Extra + Context + Question
- 6. llm.invoke(prompt) -> Answer
- 7. save_chat() -> SQLite

## 🔮 Future Updates

- YouTube Video Summarizer
- Voice Input
- Export Notes As PDF
- Multiple PDFs Chat
- Hindi / Hinglish Mode
- Dark / Light Theme Toggle
- Chat History Search
- Image / Handwritten Notes OCR

## deployment 
1. Push Code To GitHub
2. Go To https://share.streamlit.io
3. New App -> Select Repo
4. Main File: app.py
5. Deploy
