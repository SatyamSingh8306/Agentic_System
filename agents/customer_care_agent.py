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

template = ChatPromptTemplate([
    ("system" , f"{sp.customer_care_prompt}"),
    ("human", "{query}")
])

customer_care_chain = template | __llm

if __name__ == "__main__":
    ans = customer_care_chain.invoke({"query" :"Check the events you have about music events?"})
    print(ans.content)

