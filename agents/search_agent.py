from langgraph.graph import StateGraph, END, START, add_messages
from langgraph.prebuilt import ToolNode
from agents.llm import __llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, ToolMessage, BaseMessage
from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langchain_community.tools.tavily_search import TavilySearchResults
from os import getenv
from dotenv import load_dotenv
import logging

load_dotenv()
import agents.system_prompts as sp

class WebAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    tool_calls: Annotated[Optional[List[BaseMessage]], add_messages]
    agent_message: Annotated[Optional[List[str]], add_messages]

# Create the prompt template
template = ChatPromptTemplate([
    ("system", sp.web_system_prompt),
    ("placeholder", "{messages}")
])

# Initialize tools
tool = TavilySearchResults(max_results=3, api_key=getenv("TAVILY_API_KEY"))
llm = __llm.bind_tools([tool])

web_chain = template | llm

def web_agent(state: WebAgentState):
    """Main agent node that processes messages and decides on actions"""
    messages = state["messages"]
    
    # Get the conversation history for context
    response = web_chain.invoke({"messages": messages})
    
    logging.info(f"Response Generated: {response}")
    
    # Check if the agent wants to use tools
    if response.tool_calls and len(response.tool_calls) > 0:
        return {
            "tool_calls": [response],
            "messages": [response]
        }
    else:
        return {
            "agent_message": [response.content],
            "messages": [response]
        }

def should_search(state: WebAgentState) -> str:
    """Conditional edge function to determine next step"""
    # Check if there are tool calls in the last message
    last_message = state["messages"][-1] if state["messages"] else None
    
    if last_message and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "search_node"
    else:
        return END

def process_search_results(state: WebAgentState):
    """Process search results and generate final response"""
    messages = state["messages"]
    
    # Generate response based on search results
    response = web_chain.invoke({"messages": messages})
    
    logging.info(f"Final Response Generated: {response}")
    
    return {
        "agent_message": [response.content],
        "messages": [response]
    }

# Create tool node
search_node = ToolNode(tools=[tool])

# Build the graph
graph = StateGraph(WebAgentState)

# Add nodes
graph.add_node("web_agent", web_agent)
graph.add_node("search_node", search_node)
graph.add_node("process_results", process_search_results)

# Set entry point
graph.set_entry_point("web_agent")

# Add edges
graph.add_conditional_edges(
    "web_agent",
    should_search,
    {
        "search_node": "search_node",
        END: END
    }
)

# After search, process the results
graph.add_edge("search_node", "process_results")
graph.add_edge("process_results", END)

# Compile the graph
app = graph.compile()

def run_web_agent(query: str) -> Dict[str, Any]:
    """Helper function to run the web agent with a query"""
    state = {
        "messages": [HumanMessage(content=query)]
    }
    
    try:
        response = app.invoke(state)
        return response
    except Exception as e:
        logging.error(f"Error running web agent: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    # Test the agent
    queries = [
        "find some cheap helmet in lucknow?"
    ]
    
    for query in queries:
        print(f"\n{'='*50}")
        print(f"Query: {query}")
        print(f"{'='*50}")
        
        result = run_web_agent(query)
        
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            # Print the final agent message
            if "agent_message" in result and result["agent_message"]:
                print(f"Response: {result['agent_message'][-1]}")
            else:
                print("No response generated")