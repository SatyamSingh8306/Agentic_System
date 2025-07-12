from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from dotenv import load_dotenv
from os import getenv
load_dotenv()


_llm = ChatGroq(
    model = "gemma2-9b-it"
)



__llm = ChatOllama(
    model = getenv("OLLAMA_MODEL"),
    base_url= getenv("OLLAMA_BASE_URL")
)
