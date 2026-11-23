from langchain_core.prompts import ChatPromptTemplate

def build_prompt(lang, mode):
    lang_map = {
        "English": "Answer in clear, simple English.",
        "Hinglish - Desi Style": "Answer in full Hinglish, like a desi friend. Use Hindi words in English letters, fun tone.",
        "Hindi + English Mix": "Answer in Hindi + English mix, friendly.",
        "Marathi Mix": "Answer in Marathi + Hindi mix."
    }
    mode_map = {
        "Fast Answer - Short & Quick": "Give short, quick answer in 3-4 lines.",
        "Deep Reasoning - Detailed": "Give deep, detailed answer with reasoning and examples.",
        "Exam Mode - Answer + 5 Questions": "Give answer + 5 exam questions from this topic with answers.",
        "Explain Like I'm 5 - Super Simple": "Explain like I'm 5 years old, super simple words, with example.",
    }
    return ChatPromptTemplate.from_template(f"""You are NeuroDocs AI, built by a 15-year-old genius from India. You answer ONLY from given context.
    {lang_map[lang]}
    {mode_map[mode]}
    Context: {{context}}
    Question: {{question}}
    Rules:
    1. ONLY from Context. If not in doc, say "Ye document me nahi hai".
    2. Be accurate, no hallucination.
    3. Use bullet points for summary.
    Answer in Markdown:""")
