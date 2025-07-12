from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse
from fastapi import Body
from langchain.schema.runnable import RunnableConfig
from agents.supervisor import graph
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict,Any
from langchain_core.messages import HumanMessage, AIMessage

router = APIRouter()
memory = MemorySaver()
agent = graph.compile(checkpointer=memory)

from pydantic import BaseModel
from typing import List, Dict, Any

class QueryMessage(BaseModel):
    role: str
    content: str

class UserQuery(BaseModel):
    messages: List[QueryMessage]

@router.post("/chat")
async def chat_agentic_system(user_query: UserQuery = Body(...)):
    lc_messages = []
    for msg in user_query.messages:
        if msg.role == "human":
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "ai":
            lc_messages.append(AIMessage(content=msg.content))
    
    config = RunnableConfig(
        configurable={
            "thread_id": "1"
        }
    )
    
    formatted_query = {
        "message" : lc_messages,
        "category" : []
    }

    # Call agent.ainvoke with converted messages
    response = await agent.ainvoke(formatted_query, config=config)

    # If response is a dict and you want to extract last message content
    # Adjust based on actual agent response structure
    last_message = response["message"][-2].content
    print(last_message)
    return JSONResponse(content={"content": last_message}, status_code=200)
