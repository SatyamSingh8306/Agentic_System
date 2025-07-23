from httpx import AsyncClient
from langchain.tools import BaseTool
from pydantic import BaseModel
from typing import Annotated, Optional, Type
from dotenv import load_dotenv
from os import getenv


load_dotenv()

BASE_URL = getenv("RAG_BASE_URL","")

CHAT_URL  = BASE_URL + "/api/v1/chat/vector-search"

client = AsyncClient()

class QueryInput(BaseModel):
    query: Annotated[Optional[str], "The formatted best query to search in database"]


class QueryTool(BaseTool):
    name: str = "rag_tool"
    description: str = (
        "Retrieves relevant context or knowledge from the vector database for answering user queries. Invoke this when user asks about company policies, team info, or internal knowledge (mochand)."
    )
    args_schema: Type[BaseModel] = QueryInput
    return_direct: bool = True

    async def _run(self, query: str) -> str:
        response = await retrieve(query)
        return response


rag_tool = QueryTool()


async def retrieve(query : Annotated[Optional[str], "The formatted best query to search in database"]):
    """retrieving data from vector database"""
    request =  {
        "query": query,
        "collection": "mochand",
        "top_k": 5
        }
    ans = await client.post(url=CHAT_URL,json=request)
    documents = ans.json()
    texts = [doc.get("text", "") for doc in documents['top_chunks']]
    full_text = "\n".join(texts)
    return { "output" : full_text }


# agent = initialize_agent(
#     llm= __llm,
#     tools=[retrieve],
#     agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
#     verbose = True,
#     handle_parsing_errors = True,
#     max_iteration = 1,
#     early_stopping_method = "generate",
#     agent_kwargs={
#         "system_message" : sp.rag_system_prompt
#     },
# )

# rag_agent = agent

if __name__ == "__main__":
    async def main():
        response = await retrieve("Privacy policy of mochand")
        print(response)
    
    import asyncio
    asyncio.run(main())

