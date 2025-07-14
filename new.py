import os
from typing import Dict, Any, List, Annotated
from typing_extensions import TypedDict
import operator

from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver


class AgentState(TypedDict):
    """State of the agent"""
    messages: Annotated[List[BaseMessage], operator.add]
    user_message: str
    search_results: str
    summary: str
    next_action: str

class LangGraphAgent:
    def __init__(self):
        # Initialize the language model
        self.llm = ChatGroq(
            model="llama3-8b-8192",
            temperature=0.1,
            max_tokens=1000
        )
        
        # Initialize search tool
        self.search_tool = TavilySearchResults(
            max_results=5,
            search_depth="advanced"
        )
        
        # Create the graph
        self.graph = self._create_graph()
    
    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("controller", self._controller_node)
        workflow.add_node("search", self._search_node)
        workflow.add_node("summarize", self._summarize_node)
        workflow.add_node("finish", self._finish_node)
        
        # Add edges
        workflow.set_entry_point("controller")
        
        # Conditional edges from controller
        workflow.add_conditional_edges(
            "controller",
            self._route_decision,
            {
                "search": "search",
                "summarize": "summarize",
                "finish": "finish"
            }
        )
        
        # Both search and summarize go to finish
        workflow.add_edge("search", "finish")
        workflow.add_edge("summarize", "finish")
        
        # Finish goes to END
        workflow.add_edge("finish", END)
        
        # Compile the graph
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    
    def _controller_node(self, state: AgentState) -> Dict[str, Any]:
        """Controller node that decides the next action"""
        user_message = state.get("user_message", "")
        if not user_message and state.get("messages"):
            user_message = state["messages"][-1].content
        
        controller_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a controller that decides what action to take based on the user's message.
            
            Analyze the user's message and decide:
            - "search" if the user needs current information, facts, or web search
            - "summarize" if the user wants to summarize existing content or needs analysis
            - "finish" if the message is a simple greeting or doesn't require search/summarization
            
            Respond with ONLY one word: search, summarize, or finish"""),
            ("human", "{user_message}")
        ])
        
        chain = controller_prompt | self.llm | StrOutputParser()
        next_action = chain.invoke({"user_message": user_message}).strip().lower()
        
        return {
            "next_action": next_action,
            "user_message": user_message,
            "messages": [AIMessage(content=f"Controller decided: {next_action}")]
        }
    
    def _search_node(self, state: AgentState) -> Dict[str, Any]:
        """Search node that performs web search"""
        user_message = state.get("user_message", "")
        
        try:
            # Perform search
            search_results = self.search_tool.invoke({"query": user_message})
            
            # Format results
            formatted_results = "\n".join([
                f"Title: {result.get('title', 'N/A')}\n"
                f"Content: {result.get('content', 'N/A')}\n"
                f"URL: {result.get('url', 'N/A')}\n"
                for result in search_results
            ])
            
            return {
                "search_results": formatted_results,
                "messages": [AIMessage(content="Search completed successfully")]
            }
        
        except Exception as e:
            return {
                "search_results": f"Search failed: {str(e)}",
                "messages": [AIMessage(content=f"Search failed: {str(e)}")]
            }
    
    def _summarize_node(self, state: AgentState) -> Dict[str, Any]:
        """Summarize node that creates summaries"""
        user_message = state.get("user_message", "")
        
        summarize_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful assistant that provides summaries and analysis.
            Create a clear, concise response to the user's request."""),
            ("human", "{user_message}")
        ])
        
        chain = summarize_prompt | self.llm | StrOutputParser()
        summary = chain.invoke({"user_message": user_message})
        
        return {
            "summary": summary,
            "messages": [AIMessage(content="Summary completed")]
        }
    
    def _finish_node(self, state: AgentState) -> Dict[str, Any]:
        """Finish node that prepares the final response"""
        user_message = state.get("user_message", "")
        search_results = state.get("search_results", "")
        summary = state.get("summary", "")
        next_action = state.get("next_action", "")
        
        # Create final response based on what was done
        if next_action == "search" and search_results:
            response_prompt = ChatPromptTemplate.from_messages([
                ("system", """Based on the search results, provide a comprehensive answer to the user's question.
                Use the search results to give accurate, up-to-date information."""),
                ("human", """User Question: {user_message}
                
                Search Results:
                {search_results}
                
                Please provide a helpful response based on this information.""")
            ])
            
            chain = response_prompt | self.llm | StrOutputParser()
            final_response = chain.invoke({
                "user_message": user_message,
                "search_results": search_results
            })
            
        elif next_action == "summarize" and summary:
            final_response = summary
            
        else:
            # Simple greeting or direct response
            simple_prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful assistant. Respond naturally to the user."),
                ("human", "{user_message}")
            ])
            
            chain = simple_prompt | self.llm | StrOutputParser()
            final_response = chain.invoke({"user_message": user_message})
        
        return {
            "messages": [AIMessage(content=final_response)]
        }
    
    def _route_decision(self, state: AgentState) -> str:
        """Route based on controller decision"""
        next_action = state.get("next_action", "finish")
        return next_action
    
    def run(self, user_message: str, thread_id: str = "default") -> str:
        """Run the agent with a user message"""
        initial_state = {
            "messages": [HumanMessage(content=user_message)],
            "user_message": user_message,
            "search_results": "",
            "summary": "",
            "next_action": ""
        }
        
        config = {"configurable": {"thread_id": thread_id}}
        
        # Run the graph
        final_state = self.graph.invoke(initial_state, config)
        
        # Return the final message
        return final_state["messages"][-1].content

def visualize_graph(agent: LangGraphAgent):
    """Visualize the graph structure (requires graphviz)"""
    try:
        from IPython.display import Image, display
        display(Image(agent.graph.get_graph().draw_mermaid_png()))
    except ImportError:
        print("To visualize the graph, install: pip install graphviz")
        print("Graph structure:")
        print("User Message → Controller → [Search|Summarize] → Finish → Done")

# Example usage
if __name__ == "__main__":
    # Make sure to set your API keys first:
    # os.environ["GROQ_API_KEY"] = "your_groq_api_key"
    # os.environ["TAVILY_API_KEY"] = "your_tavily_api_key"
    
    agent = LangGraphAgent()
    
    # Example interactions
    examples = [
        """Hey MohanD, I’m looking for fun events in Delhi this weekend, preferably music-related. Also, what’s the weather like there, and can you suggest something that’s indoors if it rains?"""
    ]
    
    for example in examples:
        print(f"\n🤖 User: {example}")
        try:
            response = agent.run(example)
            print(f"🎯 Agent: {response}")
        except Exception as e:
            print(f"❌ Error: {e}")
            print("Make sure to set GROQ_API_KEY and TAVILY_API_KEY environment variables")
