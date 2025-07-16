from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse
from fastapi import Body
from langchain.schema.runnable import RunnableConfig
from agents.supervisor import graph
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict,Any
from langchain_core.messages import HumanMessage, AIMessage

router = APIRouter()

from pydantic import BaseModel
from typing import List, Dict, Any

class QueryMessage(BaseModel):
    role: str
    content: str

class UserQuery(BaseModel):
    messages: List[QueryMessage]

class ChatMessage(BaseModel):
    userid : str
    user_query : UserQuery

@router.post("/chat")
async def chat_agentic_system(request: ChatMessage = Body(...)):
    lc_messages = []
    user_id = request.userid
    user_query = request.user_query
    
    for msg in user_query.messages:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_messages.append(AIMessage(content=msg.content))
    print(f"<{"="*50}List of messages are : {lc_messages} {"="}>")
    config = RunnableConfig(
        configurable={
            "thread_id": f"{user_id}"
        }
    )
    
    formatted_query = {
        "message" : lc_messages,
        "category" : []
    }

    memory = MemorySaver()
    agent = graph.compile(checkpointer=memory)
    # Call agent.ainvoke with converted messages
    response = await agent.ainvoke(formatted_query, config=config)

    # If response is a dict and you want to extract last message content
    # Adjust based on actual agent response structure
    last_message =  response.get("boss_state", {"approved" : True})[-1].get("ans")
    print(last_message)
    return JSONResponse(content={"content": last_message}, status_code=200)
