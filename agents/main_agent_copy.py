from langgraph.graph import StateGraph, add_messages, END
from langchain_ollama import ChatOllama
from .rag_agent import retrieve, rag_tool
from agents.web_agent import web_search, web_tool
from agents.instamart_sale_tool import sales_tool, get_products
import asyncio
from functools import partial
from datetime import datetime
import agents.system_prompts as sp
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from .llm import __llm, ___llm
from dotenv import load_dotenv
from os import getenv
load_dotenv()
import logging
logging.basicConfig(level=logging.INFO)



def get_mochand_prompt():
    return ChatPromptTemplate.from_messages([
        ("system", f"{sp.instamart_sales_prompt} Today's date is {datetime.now().strftime("%Y-%m-%d")}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ])

def get_boss_prompt():
    return ChatPromptTemplate.from_messages([
        ("system", f"{sp.instamart_boss_prompt} Today's date is {datetime.now().strftime('%Y-%m-%d')}"),
        # MessagesPlaceholder(variable_name="chat_history"),
        ("human", "Human Query : {input} \n Tool Results : {tool_result}")
    ])



# _llm = ChatOllama(model = getenv("OLLAMA_MODEL"), base_url=getenv("OLLAMA_BASE_URL"))

from typing import TypedDict, Annotated, List, Any
class BaseState(TypedDict):
    messages: Annotated[List[Any], add_messages]
    tool_result : Annotated[List[Any], "List of tool results"]


# Added tools
model_with_tools = __llm.bind_tools([web_tool, sales_tool, rag_tool])
# Added tools

# model_with_tools = ___llm
# model = mohanD_prompt | model_with_tools

# boss_chain = boss_prompt | __llm

async def mochanD(state : BaseState) -> BaseState:
    mochand_prompt = get_mochand_prompt()
    model = mochand_prompt | model_with_tools
    messages = state["messages"]
    message = state["messages"][-1]
    response = await model.ainvoke({"chat_history": messages[:-1], "input": message})
    logging.info(f"Response from MochanD: {response}")
    return {
        "messages": response
    }


async def splitter(state: BaseState):
    messages = state["messages"][-1]
    results = []

    if messages.tool_calls:
        tasks = []

        logging.info(f"Processing tool calls: {messages.tool_calls}")

        for tool_call in messages.tool_calls:
            tool_name = tool_call.get("name")

            if tool_name == "instamart_product_search":
                search_query = tool_call.get("args", {})
                logging.info(f"Search query instamart: {search_query}")

                tasks.append(asyncio.create_task(
                    get_products(search_query)
                ))

            elif tool_name == "web_search":
                query_dict = tool_call.get("args", {})
                query = query_dict.get("query", "")
                logging.info(f"Web search query: {query}")

                tasks.append(asyncio.create_task(
                    web_search(query)
                ))
            elif tool_name == "rag_tool":
                query = tool_call.get("args", {}).get("query", "")
                logging.info(f"RAG tool query: {query}")

                tasks.append(asyncio.create_task(
                    retrieve(query)
                ))

        results = await asyncio.gather(*tasks)

        for res in results:
            logging.info(f"Tool result: {res}")

    return {
        "tool_result": results
    }


async def sales_agent(state: BaseState) -> BaseState:
    boss_prompt = get_boss_prompt()
    boss_chain = boss_prompt | __llm
    messages = state["messages"]
    message = state["messages"][-2]
    tools_result = state["tool_result"]
    logging.info(f"Sales Agent received message: {message.content}")
    logging.info(f"Sales Agent received tool results: {tools_result}")
    if not tools_result:
        return {
            "messages": message,
            "__next__": END
        }

    logging.info(f"Message to boss Agent: {message}")
    tool_results = "\n".join(tool["output"] for tool in tools_result)
    response = await boss_chain.ainvoke({"input": message, "tool_result": tool_results})
    logging.info(f"Response from Sales Agent: {response}")
    return {
        "messages": response,
        "__next__": END
    }

graph = StateGraph(BaseState)

graph.add_node("mochanD", mochanD)
graph.add_node("splitter", splitter)
graph.add_node("sales_agent", sales_agent)  

graph.set_entry_point("mochanD")
graph.add_edge("mochanD", "splitter")
graph.add_edge("splitter", "sales_agent")   
graph.add_edge("sales_agent", END)

app = graph.compile()

if __name__ == "__main__":
    async def main():
        print("Starting the agent...")
        ans = await app.ainvoke({
            "messages": [
                HumanMessage(content="""Find broccoli. Agar broccoli out of stock ho toh koi accha alternative suggest kar do for pasta, please?"""),
            ]})
        print(ans["messages"][-1].content)
        # print(ans)
    
    import asyncio
    asyncio.run(main())
