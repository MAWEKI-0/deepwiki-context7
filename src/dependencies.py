from fastapi import Depends
from supabase import Client
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
import google.genai as genai
from src.config import Settings
from src.supabase_client import get_supabase_client as get_actual_supabase_client # Rename to avoid conflict

def get_settings() -> Settings:
    return Settings()

def get_supabase() -> Client: # Renamed to get_supabase for FastAPI Depends consistency
    return get_actual_supabase_client()

def create_gemini_flash_client(settings: Settings) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=settings.GEMINI_FLASH_MODEL, temperature=0.1, google_api_key=settings.GOOGLE_API_KEY)

def create_gemini_pro_client(settings: Settings) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=settings.GEMINI_PRO_MODEL, temperature=0.2, google_api_key=settings.GOOGLE_API_KEY)

def create_embedding_model_client(settings: Settings) -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(model=settings.EMBEDDING_MODEL, google_api_key=settings.GOOGLE_API_KEY)
