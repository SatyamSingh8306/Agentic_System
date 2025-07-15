from langchain.agents import initialize_agent, AgentType
from langchain.agents import create_react_agent, AgentExecutor
from agents.llm import __llm
from langchain_community.tools import DuckDuckGoSearchResults
import agents.system_prompts as sp
from langchain_ollama import ChatOllama
from langchain_core.prompts import SystemMessagePromptTemplate,MessagesPlaceholder
from langchain_tavily import TavilySearch
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent
import logging
from os import getenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# prompts = ChatPromptTemplate(
#     [
#         ("system", f"{sp.web_system_prompt}"),
#         ("human", "{input}")
#     ]
# )
prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(sp.web_system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

tool = TavilySearchResults(tavily_api_key = getenv("TAVILY_API_KEY"), max_results=2)

agent = initialize_agent(
    llm = __llm,
    tools=[tool],
    agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose = True,
    handle_parsing_errors = True,
    max_iteration = 1,
    agent_kwargs={
            "system_message": sp.web_system_prompt
    },
    early_stopping_method = "force"
 )
# model = ChatOllama(
#     model = "qwen3:30b",
#     base_url='https://r5c7ifq4m0tjvf-11434.proxy.runpod.net/'
# )

# _agent = create_react_agent(
#     model = model,
#     tools=[tool]
# )

# agent = AgentExecutor(agent=_agent, 
#                       tools = [tool], 
#                       verbose=True)

def process_search(query):
    if isinstance(query, dict):
        query = query.get("query", "")
    logger.info(f"Processing search query: {query}")
    try:
        response = agent.invoke({"query": query})
        logger.info(f"Search agent response: {response}")
        return {
            "query": query,
            "output": response["output"]
        }
    except Exception as e:
        logger.error(f"Error in search agent: {e}")
        return {"output": f"Error occurred: {str(e)}"}

web_agent = process_search

if __name__ == "__main__":
    ans = agent.invoke({"input": "who is current pm of usa 2025 do web search?"})
    print(ans)