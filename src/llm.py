import os
import streamlit as st
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

def get_llm(model_choice):
    groq_key = os.getenv("GROQ_API_KEY") or (st.secrets.get("GROQ_API_KEY","") if hasattr(st,"secrets") else "")
    gemini_key = os.getenv("GOOGLE_API_KEY") or (st.secrets.get("GOOGLE_API_KEY","") if hasattr(st,"secrets") else "")
    openai_key = os.getenv("OPENAI_API_KEY") or (st.secrets.get("OPENAI_API_KEY","") if hasattr(st,"secrets") else "")
    # --- SIRF YAHI 1 LINE BADLI HAI - GROQ MODEL ---
    if ("Groq" in model_choice or "GPT-OSS" in model_choice) and groq_key:
        m = "openai/gpt-oss-120b" if "120B" in model_choice else "openai/gpt-oss-20b"
        return ChatGroq(model=m, groq_api_key=groq_key, temperature=0.2), f"Groq {m}"
    if "Gemini" in model_choice and gemini_key:
        return ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=gemini_key, temperature=0.3), "Gemini 2.0 Flash"
    if "OpenAI" in model_choice and openai_key:
        return ChatOpenAI(model="gpt-4o-mini", api_key=openai_key), "OpenAI GPT-4o-mini"
    if groq_key: return ChatGroq(model="openai/gpt-oss-20b", groq_api_key=groq_key, temperature=0.3), "Groq 20B (Auto)"
    if gemini_key: return ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=gemini_key, temperature=0.3), "Gemini (Auto)"
    if openai_key: return ChatOpenAI(model="gpt-4o-mini", api_key=openai_key), "OpenAI (Auto)"
    return None, "No Key - Demo Mode"
