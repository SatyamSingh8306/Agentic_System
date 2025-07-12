from langchain.agents import initialize_agent, AgentType
from agents.llm import __llm
from langchain_community.tools import DuckDuckGoSearchResults
import agents.system_prompts as sp
from langchain_tavily import TavilySearch
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent
import logging
from os import getenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

prompts = ChatPromptTemplate(
    [
        ("system", f"{sp.web_system_prompt}"
        "-Genrate the response based on user context with a friendly and same tone as user asked."),
        ("human", "{query}")
    ]
)
tool = TavilySearchResults(tavily_api_key = getenv("TAVILY_API_KEY"), max_results=2)

agent = initialize_agent(
    llm = __llm,
    tools=[tool],
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose = True,
    handle_parsing_errors = True,
    max_iteration = 2,
    early_stopping_method = "force"
)


def process_search(query):
    if isinstance(query, dict):
        query = query.get("query", "")
    logger.info(f"Processing search query: {query}")
    try:
        response = agent.invoke({"input": query})
        logger.info(f"Search agent response: {response}")
        return {"output": response["output"]}
    except Exception as e:
        logger.error(f"Error in search agent: {e}")
        return {"output": f"Error occurred: {str(e)}"}

web_agent = process_search

if __name__ == "__main__":
    ans = web_agent("who is pm of india?")
    print(ans)