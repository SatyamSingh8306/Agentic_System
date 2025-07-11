from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse
from fastapi import Body
from langchain.schema.runnable import RunnableConfig
from agents.supervisor import graph
from langgraph.checkpoint.memory import MemorySaver

router = APIRouter()
memory = MemorySaver()
agent = graph.compile(checkpointer=memory)

@router.post("/chat")
async def chat_agentic_system(user_query: str = Body(..., embed=True)):
    formatted_query = {
        "message": [user_query],
        "categories": []
    }

    config = RunnableConfig(
        configurable={
            "thread_id": "1"
        }
    )
    
    # Check if your `agent.invoke` is async; if so, use await
    response = await agent.ainvoke(formatted_query, config=config)
    
    return JSONResponse(content={"content": response["message"][-2].content}, status_code=200)
