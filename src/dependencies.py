from supabase import Client
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from src.config import settings
from src.supabase_client import get_supabase_client

def get_supabase() -> Client:
    return get_supabase_client()

def get_gemini_flash() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=settings.GEMINI_FLASH_MODEL, temperature=0.1, google_api_key=settings.GOOGLE_API_KEY)

def get_gemini_pro() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=settings.GEMINI_PRO_MODEL, temperature=0.2, google_api_key=settings.GOOGLE_API_KEY)

def get_embedding_model() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(model=settings.EMBEDDING_MODEL, google_api_key=settings.GOOGLE_API_KEY)
