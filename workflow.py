from agents.excess.chains import chain
from langgraph.graph import StateGraph, END, add_messages
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field
from typing import TypedDict, List, Annotated, Literal, Optional
import asyncio


class BaseState(TypedDict):
    message: Annotated[str, add_messages]
    categories: Annotated[str, add_messages]
    user_input: str  # Current user input
    continue_conversation: bool  # Flag to control the loop
    response: str  # Response to send back to frontend
    conversation_history: List[dict]  # Store conversation history


def categories(state):
    """Categorize the user's message"""
    user_input = state.get("user_input", "")
    
    if not user_input:
        return {
            "categories": "invalid",
            "response": "Please provide a valid message.",
            "continue_conversation": True
        }
    
    try:
        ans = chain.invoke({"query": user_input})
        return {
            "categories": ans.categories,
            "message": user_input
        }
    except Exception as e:
        return {
            "categories": "error",
            "response": f"Error processing your request: {str(e)}",
            "continue_conversation": True
        }


def next_node_selector(state):
    """Route to appropriate agent based on category"""
    cat_list = state.get("categories", [])
    if not cat_list:
        return "user_interaction"
    
    # Get the latest category
    cat = cat_list[-1] if isinstance(cat_list, list) else cat_list
    
    if cat == "search_tool_agent":
        return "search_tool_agent"
    elif cat == "event_tool_agent":
        return "event_tool_agent"
    elif cat == "content_generation_agent":
        return "content_generation_agent"
    elif cat == "error" or cat == "invalid":
        return "user_interaction"
    else:
        return "user_interaction"


def search_tool_agent(state):
    """Handle search-related queries"""
    user_input = state.get("user_input", "")
    
    # Add your actual search logic here
    response = f"🔍 Search completed for: '{user_input}'\nResults: [Your search results would go here]"
    
    # Update conversation history
    history = state.get("conversation_history", [])
    history.append({
        "user": user_input,
        "agent": "search_tool_agent",
        "response": response,
        "timestamp": "now"  # You can add actual timestamp
    })
    
    return {
        "message": "search_agent called",
        "response": response,
        "conversation_history": history,
        "continue_conversation": True
    }


def event_tool_agent(state):
    """Handle event-related queries"""
    user_input = state.get("user_input", "")
    
    # Add your actual event logic here
    response = f"📅 Event processing for: '{user_input}'\nEvent details: [Your event results would go here]"
    
    # Update conversation history
    history = state.get("conversation_history", [])
    history.append({
        "user": user_input,
        "agent": "event_tool_agent",
        "response": response,
        "timestamp": "now"
    })
    
    return {
        "message": "event_agent called",
        "response": response,
        "conversation_history": history,
        "continue_conversation": True
    }


def content_generation_agent(state):
    """Handle content generation queries"""
    user_input = state.get("user_input", "")
    
    # Add your actual content generation logic here
    response = f"✨ Content generated for: '{user_input}'\nGenerated content: [Your generated content would go here]"
    
    # Update conversation history
    history = state.get("conversation_history", [])
    history.append({
        "user": user_input,
        "agent": "content_generation_agent",
        "response": response,
        "timestamp": "now"
    })
    
    return {
        "message": "content_generation_agent called",
        "response": response,
        "conversation_history": history,
        "continue_conversation": True
    }


def user_interaction(state):
    """Handle user interaction and control loop continuation"""
    response = state.get("response", "")
    
    # If no response is set, provide a default
    if not response:
        response = "👋 Hello! I'm ready to help you. What would you like to do?\n\n" \
                  "I can help with:\n" \
                  "• Search queries\n" \
                  "• Event management\n" \
                  "• Content generation\n\n" \
                  "Type 'exit' or 'quit' to end the conversation."
    
    return {
        "response": response,
        "continue_conversation": True
    }


def should_continue(state):
    """Determine if the conversation should continue"""
    user_input = state.get("user_input", "").lower().strip()
    
    # End conversation if user wants to exit
    if user_input in ['exit', 'quit', 'bye', 'goodbye']:
        return "end_conversation"
    
    # Continue if flag is set
    if state.get("continue_conversation", False):
        return "user_interaction"
    
    return "end_conversation"


def end_conversation(state):
    """End the conversation gracefully"""
    history = state.get("conversation_history", [])
    
    return {
        "response": "👋 Goodbye! Thanks for using our assistant. Have a great day!",
        "continue_conversation": False,
        "conversation_history": history
    }


# Create the graph
graph = StateGraph(BaseState)

# Add nodes
graph.add_node("categories", categories)
graph.add_node("search_tool_agent", search_tool_agent)
graph.add_node("event_tool_agent", event_tool_agent)
graph.add_node("content_generation_agent", content_generation_agent)
graph.add_node("user_interaction", user_interaction)
graph.add_node("end_conversation", end_conversation)

# Set entry point
graph.set_entry_point("categories")

# Add conditional edges from categories to route to appropriate agents
graph.add_conditional_edges(
    "categories",
    next_node_selector,
    {
        "search_tool_agent": "search_tool_agent",
        "event_tool_agent": "event_tool_agent",
        "content_generation_agent": "content_generation_agent",
        "user_interaction": "user_interaction"
    }
)

# Add edges from agents back to user interaction (to continue the loop)
graph.add_conditional_edges("search_tool_agent", should_continue)
graph.add_conditional_edges("event_tool_agent", should_continue)
graph.add_conditional_edges("content_generation_agent", should_continue)

# Add conditional edges from user_interaction to either continue or end
graph.add_conditional_edges(
    "user_interaction",
    should_continue,
    {
        "user_interaction": "categories",  # Loop back to categorize new input
        "end_conversation": "end_conversation"
    }
)

# End conversation terminates the graph
graph.add_edge("end_conversation", END)

# Compile the graph
app = graph.compile()
