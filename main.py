from fastapi import FastAPI, APIRouter
from api import chat
import uvicorn

app = FastAPI(title="Agentic System", summary="Capable of handling multiple agents")

# Create a root router first
router = APIRouter()

@router.get("/")
async def health_check():
    return {
        "service": "Multi Agent and Agentic System"
    }


app.include_router(router)
app.include_router(chat.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
