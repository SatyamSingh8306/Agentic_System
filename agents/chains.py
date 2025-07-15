from langchain_groq import ChatGroq 
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate , ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel , Field
from typing import Annotated, Literal, List, Optional
from dotenv import load_dotenv
from os import getenv
import agents.system_prompts as sp
load_dotenv()

class AgentInputFormat(BaseModel):
    agent_name : Annotated[str, Literal[
            "search_tool_agent", 
            "rag_agent",
            "sales_agent",
            "customer_care_agent"]]
    query : Annotated[List[str], "Queries to asked by corresponding selected Agent"]

class UnderstandingContext(BaseModel):
    criteria : Annotated[List[str],"A detailed List of criterion required based on user query to pass the user query"]
    keywords : Annotated[List[str], "A detailed List of important key point mentioned in user query"]


class SupervisorResponse(BaseModel):
    """
    SupervisorResponse model for categorizing user queries into specific agent domains.
    
    This model ensures structured routing of user queries to appropriate specialized agents
    based on query intent and content analysis.
    """
    
    subtasks : Annotated[List[AgentInputFormat] , "A List of necessary subtask which can improve the reponse based on user context"]
    understading : Annotated[List[UnderstandingContext], "A List which includes what are the criterion to accept the answer and keypoint of understanding of user query"]
    


# template = ChatPromptTemplate(
#     [
#         ("system", """
# You are an expert Supervisor AI responsible for intelligent query routing. Your primary task is to analyze incoming user queries and classify them into exactly one of the following specialized agent categories. 

# **CLASSIFICATION RULES:**
# - Always return ONLY the agent category name (e.g., "content_generation_agent")
# - Never provide explanations, reasoning, or multiple options
# - If uncertain, default to "content_generation_agent"
# - Consider the user's primary intent, not secondary aspects

# **AGENT CATEGORIES:**

# **1. content_generation_agent**
# - Purpose: General conversations, creative writing, explanations, educational content
# - Triggers: Creative requests, general knowledge questions, explanations of concepts, casual conversation
# - Examples: "Write a story about dragons", "Explain machine learning", "Tell me a joke", "How does photosynthesis work?"

# **2. search_tool_agent**
# - Purpose: Real-time information, current events, recent news, time-sensitive data
# - Triggers: Keywords like "latest", "current", "recent", "news", "today", "this week"
# - Examples: "What's the latest news about Tesla?", "Current weather in Paris", "Recent developments in AI", "Who won yesterday's game?"

# **3. event_tool_agent**
# - Purpose: Event discovery, entertainment listings, activity recommendations
# - Triggers: Event-related queries with location/time constraints
# - Examples: "Concerts in NYC this weekend", "Comedy shows tonight in London", "Art exhibitions near me", "Sports events tomorrow"

# **4. rag_agent**
# - Purpose: Document retrieval, knowledge base queries, specific information lookup
# - Triggers: Requests for specific documentation, company information, technical specifications
# - Examples: "What does our policy say about...", "Find information about product X", "Show me the documentation for..."

# **5. sales_agent**
# - Purpose: Product inquiries, sales support, purchase assistance
# - Triggers: Product interest, pricing questions, purchase intent
# - Examples: "I want to buy...", "What's the price of...", "Can you help me choose a product?", "Product recommendations"

# **6. billing_info_agent**
# - Purpose: Billing inquiries, invoice requests, payment history
# - Triggers: Financial account information, billing statements, payment records
# - Examples: "Show me my invoice", "What's my billing history?", "I need my payment records", "Billing statement for last month"

# **7. payment_order_agent**
# - Purpose: Payment processing, order status, transaction support
# - Triggers: Payment issues, order tracking, transaction problems
# - Examples: "My payment failed", "Where's my order?", "Track my purchase", "Payment not processed"

# **8. feedback_agent**
# - Purpose: User feedback collection, reviews, suggestions, complaints
# - Triggers: Feedback expressions, review submissions, improvement suggestions
# - Examples: "I want to leave feedback", "This product is great/terrible", "Suggestion for improvement", "Report a problem"

# **9. analytics_agent**
# - Purpose: Data analysis, statistics, metrics, reporting
# - Triggers: Data requests, statistical analysis, performance metrics
# - Examples: "Show me the sales report", "What are the usage statistics?", "Generate analytics dashboard", "Performance metrics"

# **EDGE CASE HANDLING:**
# - Mixed queries: Route to the agent handling the PRIMARY intent
# - Ambiguous queries: Default to "content_generation_agent"
# - Multiple intents: Choose the most specific/specialized agent that applies

# Analyze the query and respond with only the appropriate agent category name.
# """),
#         ("human", "{query}")
#     ]
# )

template = ChatPromptTemplate(
    [
        ("system", f"{sp.supervisor_prompt}"),
        ("human", "{query}")
    ]
)


# __llm = ChatGroq(
#     model = "deepseek-r1-distill-llama-70b"
# )

__llm = ChatOllama(
    model = getenv("OLLAMA_MODEL"),
    base_url = getenv("OLLAMA_BASE_URL")
)

llm = __llm.with_structured_output(SupervisorResponse)
classification_chain = template | llm


conversation_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful AI assistant. Engage in a friendly and informative conversation with the user."),
    ("human", "{input}")
])

conversation_chain = conversation_prompt | __llm

# --- Search Chain ---
search_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are Search Expert assistant. Refine the user query to search on internet Note : Make sure to return query in search prompt"),
    ("human", "{input}")
])

query_chain = search_prompt | __llm



if __name__ == "__main__":
    response = conversation_chain.invoke({"query" :"what hapened in lucknow on date 3 july 2025"})
    print(response)