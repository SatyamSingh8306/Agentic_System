from langchain_community.utilities import GoogleSerperAPIWrapper
from pydantic import BaseModel
from langchain_core.tools import BaseTool
import agents.system_prompts as sp
from typing import Type
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
from langchain_core.prompts import SystemMessagePromptTemplate,MessagesPlaceholder
from langchain_core.prompts import ChatPromptTemplate
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

# tool = TavilySearchResults(tavily_api_key = getenv("TAVILY_API_KEY"), max_results=2)

tool = GoogleSerperAPIWrapper(
    api_key=getenv("SERPER_API_KEY"),
    k=30,
    hl="en",
    gl="in"
)

class WebSearchInput(BaseModel):
    query: str

class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = (
        "Use this tool to search the web for current information, news, or general queries. "
    )
    args_schema: Type[BaseModel] = WebSearchInput
    return_direct: bool = True

    def _run(self, query: str) -> str:
        # Placeholder method — replace with actual sync call if needed.
        return f"Searching the web for: {query} (this is a placeholder response)"


web_tool = WebSearchTool()


async def web_search(query) -> str:
    """
    Asynchronously formats search result items into Markdown.
    
    Args:
        query (str): The search query to be processed.

    Returns:
        str: A markdown-formatted string of the results.
    """
    results = await tool.aresults(query)
    if not results:
        return "❌ No results found."

    organic_results = results.get("organic", [])

    md_lines = ["# 🔍 Web Search Results\n"]

    for idx, result in enumerate(organic_results):
        title = result.get("title", "No Title")
        snippet = result.get("snippet", "No snippet available.")
        link = result.get("link", "#")
        date = result.get("date", "Unknown time")

        md_lines.append(
            f"### {idx + 1}. [{title}]({link})\n"
            f"**🕒 {date}**\n\n"
            f"{snippet}\n"
        )

    return { "output" : "\n".join(md_lines) }


if __name__ == "__main__":

    lst = ["Most affordable hospitals in indore"]
    async def main():
        for l in lst:
            ans = await web_search(l)
            print(ans)
    import asyncio
    asyncio.run(main())