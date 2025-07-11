from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse
from langchain.schema.runnable import RunnableConfig
from typing import Annotated, Literal, List, Dict,Optional, Any
router = APIRouter()
from agents.supervisor import final_agent

@router.post("/chat")
async def chatAgenticSystem(user_query: Optional[Dict[Any, Any]]):
    
    formatted_query = {
        "message" : [user_query],
        "category" : []
    }
    agent = final_agent
    config = RunnableConfig(
            configurable={
                "thread_id" : "1"
            }
        )
    response = agent.invoke(formatted_query,config=config)
    
    return JSONResponse(content={"content" : response["message"][-2].content}, status_code=200)
