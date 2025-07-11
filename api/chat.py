from fastapi import FastAPI, APIRouter
from typing import Annotated, Literal, List, Dict,Optional, Any
router = APIRouter(prefix="/chat")
from agents.supervisor import final_agent

@router.post("/")
async def chatAgenticSystem(self,
            user_query: Optional[Dict[Any, Any]]):
    
    formatted_query = {
        "message" : user_query
    }
    agent = final_agent
    response = agent.invoke(formatted_query)
    
    return response["message"][-2].content

