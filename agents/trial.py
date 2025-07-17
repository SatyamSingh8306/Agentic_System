# main.py
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.prompts import ChatPromptTemplate

from agents.llm import __llm
from langchain_community.tools.tavily_search import TavilySearchResults

search_tool = TavilySearchResults()

from typing import TypedDict, Annotated, List, Dict

# ----------- Define State -------------
class AgentState(TypedDict):
    messages: Annotated[List, lambda x: x]

# ----------- Prompt Template -------------
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful AI agent. Answer using the available tools."),
    ("human", "{input}")
])

# ----------- LLM Node -------------
def llm_node(state: AgentState) -> AgentState:
    response = __llm.invoke(state["messages"])
    return {"messages": state["messages"] + [response]}

# ----------- Tool Node (e.g., Search) -------------
search_node = ToolNode(tools=[search_tool])

# ----------- Final Answer -------------
def final_answer(state: AgentState) -> str:
    return state["messages"][-1].content

# ----------- Router Node (Simple Logic) -------------
def route(state: AgentState) -> str:
    last_msg = state["messages"][-1].content.lower()
    if "search" in last_msg or "google" in last_msg:
        return "search"
    return "llm"

# ----------- Build Graph -------------
builder = StateGraph(AgentState)
builder.add_node("llm", llm_node)
builder.add_node("search", search_node)

builder.set_entry_point("llm")
builder.add_conditional_edges("llm", route, {
    "llm": "llm",
    "search": "search"
})
builder.add_edge("search", "llm")
builder.add_edge("llm", END)

graph = builder.compile()

# ----------- Run Agentic System -------------
if __name__ == "__main__":
    user_input = input("Ask something: ")
    inputs = {
        "messages": [HumanMessage(content=user_input)]
    }

    result = graph.invoke(inputs)
    print("\n🤖 Final Answer:", result["messages"][-1].content)
