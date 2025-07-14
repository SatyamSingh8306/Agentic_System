from langchain.agents import initialize_agent, AgentType
from agents.llm import __llm
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
    """retrieving data from vector database"""
    request =  {
        "query": query,
        "collection": "1234"
        }
    ans = requests.post(url=CHAT_URL,json=request)
    return ans.json()["answer"]


agent = initialize_agent(
    llm= __llm,
    tools=[retrieve],
    agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose = True,
    handle_parsing_errors = True,
    max_iteration = 1,
    early_stopping_method = "force",
    agent_kwargs={
        "system_message" : sp.rag_system_prompt
    }
)

rag_agent = agent

if __name__ == "__main__":
    ans = rag_agent.invoke("Check the events you have about music events?")
    print(ans)

