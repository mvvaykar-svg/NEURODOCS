# Central prompt builder - easy to change style / language / detail

def build_prompt(question, mode, detail, lang, extra, bot_mode, context=""):
    detail_map = {
        1: "Answer in 1 line",
        2: "Answer in short",
        3: "Answer in detail",
        4: "Answer in very detail with example",
        5: "Answer like a full chapter with headings"
    }

    lang_map = {
        "English": "Answer in English",
        "Hinglish 🇮🇳": "Answer in Hinglish - Hindi in English letters, casual like a friend",
        "Hindi 🇮🇳": "Answer in Hindi (Devanagari)",
        "Simple English": "Answer in very simple English"
    }

    detail_text = detail_map.get(detail, "Answer in detail")
    lang_text = lang_map.get(lang, "Answer in English")

    if bot_mode == "LLM Bot":
        return (
            f"You are a helpful universal AI assistant. "
            f"Style: {mode}. Detail: {detail_text}. Language: {lang_text}. {extra}\n"
            f"Question: {question}"
        )
    else:
        return (
            f"You are a RAG assistant. Answer ONLY from the given Context. "
            f"If answer is not in Context, say 'Not found in your document'. "
            f"Style: {mode}. Detail: {detail_text}. Language: {lang_text}. {extra}\n"
            f"Context: {context}\n"
            f"Question: {question}"
        )
