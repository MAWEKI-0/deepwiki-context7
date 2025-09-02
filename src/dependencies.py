from fastapi import Depends
from supabase import Client
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from functools import lru_cache
import google.generativeai as genai
from src.config import Settings
from src.supabase_client import get_supabase_client

@lru_cache()
def get_settings() -> Settings:
    return Settings()

@lru_cache()
def get_genai_client(settings: Settings = Depends(get_settings)) -> genai.Client:
    return genai.Client(api_key=settings.GOOGLE_API_KEY)

def get_supabase() -> Client:
    return get_supabase_client()

def get_gemini_flash(settings: Settings = Depends(get_settings)) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=settings.GEMINI_FLASH_MODEL, temperature=0.1, google_api_key=settings.GOOGLE_API_KEY)

def get_gemini_pro(settings: Settings = Depends(get_settings)) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=settings.GEMINI_PRO_MODEL, temperature=0.2, google_api_key=settings.GOOGLE_API_KEY)

def get_embedding_model(settings: Settings = Depends(get_settings)) -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(model=settings.EMBEDDING_MODEL, google_api_key=settings.GOOGLE_API_KEY)
