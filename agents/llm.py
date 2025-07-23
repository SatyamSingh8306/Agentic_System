from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
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

___llm = ChatOllama(
    model = getenv("OLLAMA_MODEL"),
    base_url= getenv("OLLAMA_BASE_URL"),
    temperature=0.4,
    num_predict=300
)

__llm = ChatOpenAI(
    model = getenv("OPENAI_MODEL", "gpt-4.1-nano"),
    temperature=0.4,
    max_tokens=1000
)

# ___llm = ChatGoogleGenerativeAI(
#     model = "gemini-2.5-pro",
#     api_key = getenv("GOOGLE_API_KEY"),
#     temperature=0.2
# )
