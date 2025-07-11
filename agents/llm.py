from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from dotenv import load_dotenv
load_dotenv()


_llm = ChatGroq(
    model = "gemma2-9b-it"
)
__llm = ChatOllama(
    model = "gemma2:9b",
    base_url="https://a59ulrlntmv161-11434.proxy.runpod.net/" 
)
