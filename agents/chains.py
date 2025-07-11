from langchain_groq import ChatGroq 
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate , ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel , Field
from typing import Annotated, Literal
from dotenv import load_dotenv
load_dotenv()

class SupervisorResponse(BaseModel):
    """
    SupervisorResponse model for categorizing user queries into specific agent domains.
    
    This model ensures structured routing of user queries to appropriate specialized agents
    based on query intent and content analysis.
    """
    
    # category: Annotated[
    #     Literal[
    #         "content_generation_agent",
    #         "search_tool_agent", 
    #         "event_tool_agent",
    #         "rag_agent",
    #         "sales_agent",
    #         "billing_info_agent", 
    #         "payment_order_agent",
    #         "feedback_agent",
    #         "analytics_agent"
    #     ],
    #     Field(
    #         description="""
    #         Categorizes the user query into one of the following specialized agent domains:
            
    #         • content_generation_agent: General conversations, creative writing, explanations, 
    #           educational content that don't require real-time data or specialized tools
              
    #         • search_tool_agent: Queries requiring current information, recent news, 
    #           real-time data, or web search capabilities
              
    #         • event_tool_agent: Event-related queries including concerts, shows, activities 
    #           with specific location, time, or date constraints
              
    #         • rag_agent: Document retrieval, knowledge base queries, company-specific 
    #           information lookup from internal sources
              
    #         • sales_agent: Product inquiries, purchase assistance, pricing questions, 
    #           sales support, and product recommendations
              
    #         • billing_info_agent: Billing inquiries, invoice requests, payment history, 
    #           account balance, and financial record access
              
    #         • payment_order_agent: Payment processing issues, order tracking, transaction 
    #           status, and order management support
              
    #         • feedback_agent: User feedback collection, reviews, suggestions, complaints, 
    #           and improvement recommendations
              
    #         • analytics_agent: Data analysis requests, statistics, metrics, reporting, 
    #           and business intelligence queries
    #         """,
    #         default="content_generation_agent"
    #     )
    # ]
    category: Annotated[
        Literal[
            "search_tool_agent", 
            "rag_agent",
            "sales_agent",
        ],
        Field(
            description="""
            Categorizes the user query into one of the following specialized agent domains:
              
            • search_tool_agent: Queries requiring current information, recent news, 
              real-time data, or web search capabilities
              
            • rag_agent: Document retrieval, knowledge base queries, company-specific 
              information lookup from internal sources
              
            • sales_agent: Product inquiries, purchase assistance, pricing questions, 
              sales support, and product recommendations
            """,
            default="sales_agent"
        )
    ]
    


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
        ("system", """
You are an expert Supervisor AI responsible for intelligent query routing. Your primary task is to analyze incoming user queries and classify them into exactly one of the following specialized agent categories. 

**CLASSIFICATION RULES:**
- Always return ONLY the agent category name (e.g., "content_generation_agent")
- Never provide explanations, reasoning, or multiple options
- If uncertain, default to "content_generation_agent"
- Consider the user's primary intent, not secondary aspects

**AGENT CATEGORIES:**
**1. search_tool_agent**
- Purpose: Real-time information, current events, recent news, time-sensitive data
- Triggers: Keywords like "latest", "current", "recent", "news", "today", "this week"
- Examples: "What's the latest news about Tesla?", "Current weather in Paris", "Recent developments in AI", "Who won yesterday's game?"

**2. rag_agent**
- Purpose: Document retrieval, knowledge base queries, specific information lookup
- Triggers: Requests for specific documentation, company information, technical specifications
- Examples: "What does our policy say about...", "Find information about product X", "Show me the documentation for..."

**3. sales_agent**
- Purpose: Product inquiries, sales support, purchase assistance
- Triggers: Product interest, pricing questions, purchase intent
- Examples: "I want to buy...", "What's the price of...", "Can you help me choose a product?", "Product recommendations"

Analyze the query and respond with only the appropriate agent category name.
"""),
        ("human", "{query}")
    ]
)


__llm = ChatGroq(
    model = "gemma2-9b-it"
)

# __llm = ChatOllama(
#     model = "qwen3:14b",
#     base_url = "https://a59ulrlntmv161-11434.proxy.runpod.net/"
# )

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