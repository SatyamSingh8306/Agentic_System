from langgraph.graph import StateGraph, add_messages, END
from langgraph.prebuilt import ToolNode
from langchain_ollama import ChatOllama
from langchain.tools import Tool
from agents.web_agent import tool
from agents.sale_agent import search_tool
import agents.system_prompts as sp
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
from os import getenv
load_dotenv()
import logging
logging.basicConfig(level=logging.INFO)


mohanD_prompt = ChatPromptTemplate.from_messages([
    ("system", sp.customer_care_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])

boss_prompt = ChatPromptTemplate.from_messages([
    ("system", sp.boss_system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "Human Query : {input} \n Tool Results : {tool_result}")
])


_llm = ChatOllama(model = getenv("OLLAMA_MODEL"), base_url=getenv("OLLAMA_BASE_URL"))

from typing import TypedDict, Annotated, List, Any
class BaseState(TypedDict):
    messages: Annotated[List[Any], add_messages]
    tool_result : Annotated[List[Any], "List of tool results"]

# online_search_tool = Tool(
#     name="custom_search_tool",
#     description="Tool for web or online searching",
#     func=tool
# )

# event_search_tool = Tool(
#     name="event_search_tool",
#     description="Tool for searching events or activities",
#     func=search_tool
# )

model_with_tools = _llm.bind_tools([tool, search_tool])
model = mohanD_prompt | model_with_tools

boss_chain = boss_prompt | _llm

def mohanD(state : BaseState) -> BaseState:
    messages = state["messages"]
    message = state["messages"][-1]
    response = model.invoke({"chat_history": messages[:-1], "input": message})
    logging.info(f"Response from MohanD: {response}")
    return {
        "messages": response
    }

def splitter(state: BaseState):
    messages = state["messages"][-1]
    ans = []
    if messages.tool_calls:
        tool_calls = messages.tool_calls
        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            if tool_name == "search_tool":
                query = tool_call.get("args", {})
                ans.append(search_tool.invoke(query))
            elif tool_name == "tavily_search_json":
                query = tool_call.get("args", {})
                ans.append(tool.invoke(query))
    return {
        "tool_result": ans
    }

def sales_agent(state: BaseState) -> BaseState:
    messages = state["messages"]
    message = state["messages"][-1]
    tools_result = state["tool_result"]
    response = boss_chain.invoke({"chat_history": messages[:-1], "input": message, "tool_result": tools_result})
    return {
        "messages": response,
        "__next__": END
    }

graph = StateGraph(BaseState)

graph.add_node("mohanD", mohanD)
graph.add_node("splitter", splitter)
graph.add_node("sales_agent", sales_agent)  

graph.set_entry_point("mohanD")
graph.add_edge("mohanD", "splitter")
graph.add_edge("splitter", "sales_agent")   
graph.add_edge("sales_agent", END)

app = graph.compile()

if __name__ == "__main__":
    ans = app.invoke({"messages": [HumanMessage(content="Hii bhai kya haal hai?"), AIMessage(content="Sab badhiya hai, aap kaise hain?"), HumanMessage("Mera bhi sahi hai lucknow me events dikhao"), AIMessage(content="""Lucknow ke events dekho bhai! 🎉
- **Zakir Khan ka "Papa Yaar"** 30 July ko Indira Gandhi Pratishthan me, ticket ₹1299
- **Anuv Jain & Zaeden** 29 July ko Phoenix Palassio me, ₹999 me enjoy karo
- **Twilight Carnival 2025** (New Year ke liye!) 31 December ko Dayal Gateway me, ₹699

Kya kuch specific event ya genre pasand hai? Mera pass lock karo ya details chahiye? 😎"""), HumanMessage("Chalo ab delhi me events batao weekend ke")], "tool_result": []})
    print(ans["messages"][-1].content)