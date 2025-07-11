from langchain.agents import initialize_agent, AgentType
from llm import __llm
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import tool
from typing import Annotated, Optional
from dotenv import load_dotenv
from os import getenv
import requests
import agents.system_prompts as sp
load_dotenv()

BASE_URL = getenv("RAG_BASE_URL","")

CHAT_URL  = BASE_URL + "/api/v1/chat/query"

@tool
def retrieve(query : Annotated[Optional[str], "The formatted best query to search in database"]):
    request =  {
        "query": query,
        "collection": "1234"
        }
    ans = requests.post(url=CHAT_URL,params=request)
    return ans.json()["answer"]


template = ChatPromptTemplate(
    [
        ("ai" ,f"{sp.rag_system_prompt}"),
        ("human", "{query}")
    ]
)

agent = initialize_agent(
    llm= __llm,
    tools=[retrieve],
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose = True
)

rag_agent = template | agent

if __name__ == "__main__":
    ans = rag_agent.invoke({"query" : "who is pm of india?"})
    print(ans)

