from agents.chains import classification_chain, conversation_chain
from langgraph.graph import StateGraph, END, add_messages
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import ToolNode
from langchain.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field
from typing import TypedDict, List, Annotated, Literal

memory = MemorySaver()

class BaseState(TypedDict):
    message: Annotated[List[str], add_messages]
    categories: Annotated[List[str], add_messages]

def categories(state):
    # Extract the actual message content for the chain
    message_content = state.get("message", "")[-1]
    if isinstance(message_content, list):
        message_content = message_content[-1] if message_content else ""
    ans = classification_chain.invoke({"query": message_content}).model_dump()
    print(ans["categories"])
    return {
        "categories": ans["categories"]
    }


def next_node_selector(state):
    # Get the categories from state
    cat_list = state.get("categories", [])
    print(cat_list)
    if not cat_list:
        return END
    
    # Get the latest category
    cat = cat_list[-1].content 
    print(cat)
    if cat == "search_tool_agent":
        return "search_tool_agent"
    elif cat == "event_tool_agent":
        return "event_tool_agent"
    elif cat == "content_generation_agent":
        return "content_generation_agent"
    else:
        print(f"executing end  {cat}\n")
        return END

@tool
def search_tool_agent(query : Annotated[str, "User Query to search online"]):
    """Search Online """
    return {
        "message": "search_agent called"
    }

@tool
def event_tool_agent(state : Annotated[str, "event queryies to search online"]):
    """Search Events Online"""
    return {
        "message": "event_agent called"
    }


def content_generation_agent(state):
    # Get the latest message for content generation
    messages = state.get("message", [])
    if not messages:
        return {"message": [AIMessage("I'm here to help! What can I do for you?")]}
    
    # Get the user's message
    user_message = messages[-1]
    if isinstance(user_message, HumanMessage):
        user_input = user_message.content
    elif isinstance(user_message, str):
        user_input = user_message
    else:
        user_input = str(user_message)
    
    try:
        response = conversation_chain.invoke({"input": user_input})
        return {
            "message": [AIMessage(response.content)]
        }
    except Exception as e:
        print(f"Error in content generation: {e}")
        return {
            "message": [AIMessage("I apologize, but I encountered an error. Please try again.")]
        }

search_tool_agents = ToolNode(tools =[search_tool_agent])
event_tool_agents = ToolNode(tools= [event_tool_agent])
# Create the graph
graph = StateGraph(BaseState)

# Add nodes
graph.add_node("categories", categories)
graph.add_node("search_tool_agent", search_tool_agents)
graph.add_node("event_tool_agent", event_tool_agents)
graph.add_node("content_generation_agent", content_generation_agent)

# Set entry point
graph.set_entry_point("categories")

# Add conditional edges - the function name should match a function that returns the next node
graph.add_conditional_edges(
    "categories",
    next_node_selector,
    {
        "search_tool_agent": "search_tool_agent",
        "event_tool_agent": "event_tool_agent", 
        "content_generation_agent": "content_generation_agent",
        END: END
    }
)

# Add edges to END from each agent
graph.add_edge("search_tool_agent", END)
graph.add_edge("event_tool_agent", END)
graph.add_edge("content_generation_agent", END)

# Compile the graph
app = graph.compile(checkpointer=memory)


# Example usage:
if __name__ == "__main__":
    # Test the graph
    initial_state = BaseState(
        message= ["Yuph"],
        categories = []
    )

    while True:
        user = input("Enter your Questions : ")
        config = {"configurable": {
            "thread_id": "1"
        }}
        initial_state["message"] = [user]
        result = app.invoke(initial_state, config=config)
        # print(result)
        print(result)
        category = result["categories"][-1].content
        initial_state["categories"] = category
        print("Final result:", result["categories"][-1].content)