from langgraph.graph import StateGraph, END, add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, BaseMessage
from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langchain_community.tools.tavily_search import TavilySearchResults
from os import getenv
from dotenv import load_dotenv
import logging

load_dotenv()

# ---------- System Prompt ----------
# Example system prompt instructing LLM to use search tool if needed
web_system_prompt = """You are a helpful web assistant who can answer user queries and perform online searches if needed.
If the user's query requires current, factual, or online information, use the search tool to gather data before responding."""

# ---------- State Definition ----------
class WebAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    tool_calls: Annotated[Optional[List[BaseMessage]], add_messages]
    agent_message: Annotated[Optional[List[str]], add_messages]

# ---------- Prompt Template ----------
template = ChatPromptTemplate.from_messages([
    ("system", web_system_prompt),
    ("placeholder", "{messages}")
])

# ---------- Tool ----------
tool = TavilySearchResults(max_results=3, api_key=getenv("TAVILY_API_KEY"))

# ---------- LLM Bind Tools ----------
from agents.llm import __llm  # You said this is your local LLM wrapper
llm = __llm.bind_tools([tool])

# ---------- Web Chain ----------
web_chain = template | llm

# ---------- Agent Node ----------
def web_agent(state: WebAgentState):
    messages = state["messages"]

    # Call chain and get raw output so we can access tool_calls
    result = web_chain.invoke({"messages": messages}, return_only_outputs=False)
    logging.info(f"LLM full result: {result}")

    # Get last generated AIMessage
    response = result["messages"][-1]

    if hasattr(response, "tool_calls") and response.tool_calls:
        return {
            "tool_calls": [response],
            "messages": [response]
        }
    else:
        return {
            "agent_message": [response.content],
            "messages": [response]
        }

# ---------- Condition Check ----------
def should_search(state: WebAgentState) -> str:
    last_message = state["messages"][-1] if state["messages"] else None
    if last_message and hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "search_node"
    else:
        return END

# ---------- Process Search Results Node ----------
def process_search_results(state: WebAgentState):
    messages = state["messages"]

    # Call again to generate final summary after tool results
    result = web_chain.invoke({"messages": messages}, return_only_outputs=False)
    logging.info(f"Final LLM result after search: {result}")

    response = result["messages"][-1]

    return {
        "agent_message": [response.content],
        "messages": [response]
    }

# ---------- Tool Node ----------
search_node = ToolNode(tools=[tool])

# ---------- Graph ----------
graph = StateGraph(WebAgentState)

graph.add_node("web_agent", web_agent)
graph.add_node("search_node", search_node)
graph.add_node("process_results", process_search_results)

graph.set_entry_point("web_agent")

graph.add_conditional_edges(
    "web_agent",
    should_search,
    {
        "search_node": "search_node",
        END: END
    }
)

graph.add_edge("search_node", "process_results")
graph.add_edge("process_results", END)

# ---------- Compile ----------
app = graph.compile()

# ---------- Run Helper ----------
def run_web_agent(query: str) -> Dict[str, Any]:
    state = {
        "messages": [HumanMessage(content=query)]
    }

    try:
        response = app.invoke(state)
        return response
    except Exception as e:
        logging.error(f"Error running web agent: {e}")
        return {"error": str(e)}

# ---------- Test ----------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    queries = [
        "Find some cheap helmets in Lucknow? Search online.",
        "Tell me about the latest trends in AI research.",
        "What's the weather today in Paris?"
    ]

    for query in queries:
        print(f"\n{'='*50}")
        print(f"Query: {query}")
        print(f"{'='*50}")

        result = run_web_agent(query)

        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            if "agent_message" in result and result["agent_message"]:
                print(f"Response: {result['agent_message'][-1]}")
            else:
                print("No response generated.")
