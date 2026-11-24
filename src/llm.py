from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

def get_llm(model_choice, keys):
    """
    Returns (llm, model_name)
    keys = {"GROQ_API_KEY": ..., "GOOGLE_API_KEY": ..., "OPENAI_API_KEY": ...}
    If key is missing, returns (None, "Demo")
    """
    # Groq - FREE - GPT-OSS Models
    if "GPT-OSS" in model_choice:
        if not keys.get("GROQ_API_KEY"):
            return None, "Demo"
        model = "openai/gpt-oss-20b" if "20B" in model_choice else "openai/gpt-oss-120b"
        llm = ChatGroq(model=model, api_key=keys["GROQ_API_KEY"], temperature=0.7)
        return llm, model

    # Gemini
    if "Gemini" in model_choice:
        if not keys.get("GOOGLE_API_KEY"):
            return None, "Demo"
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=keys["GOOGLE_API_KEY"],
            temperature=0.7
        )
        return llm, "Gemini 2.0 Flash"

    # OpenAI
    if "GPT-4o" in model_choice:
        if not keys.get("OPENAI_API_KEY"):
            return None, "Demo"
        llm = ChatOpenAI(model="gpt-4o-mini", api_key=keys["OPENAI_API_KEY"], temperature=0.7)
        return llm, "GPT-4o-mini"

    return None, "Demo"
