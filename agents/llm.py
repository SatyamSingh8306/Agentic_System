from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from os import getenv
load_dotenv()

_llm = ChatGroq(
    model = "gemma2-9b-it"
)

# __llm = ChatGroq(
#     model = "gemma2-9b-it",
#     temperature=0.2
# )

__llm = ChatOllama(
    model = getenv("OLLAMA_MODEL", "qwen3:30b"),
    base_url= getenv("OLLAMA_BASE_URL"),
    temperature=0.2
)
___llm = ChatGoogleGenerativeAI(
    model = "gemini-2.0-flash-lite",
    api_key = getenv("GOOGLE_API_KEY"),
    temperature=0.2
)
