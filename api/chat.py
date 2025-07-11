from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse
from typing import Annotated, Literal, List, Dict,Optional, Any
router = APIRouter(prefix="/chat")
from agents.supervisor import final_agent

@router.post("/")
async def chatAgenticSystem(user_query: Optional[Dict[Any, Any]]):
    
    formatted_query = {
        "message" : [user_query],
        "category" : []
    }
    agent = final_agent
    response = agent.invoke(formatted_query)
    
    return JSONResponse(content={"content" : response["message"][-2].content}, status_code=200)
