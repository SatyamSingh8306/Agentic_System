from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import JSONResponse
from api import chat
import uvicorn
from agents.system_prompts import update_prompts
import agents.system_prompts as system_prompt

app = FastAPI(title="Agentic System", summary="Capable of handling multiple agents")

# Create a root router first
router = APIRouter()

@router.get("/")
async def health_check():
    return {
        "service": "Multi Agent and Agentic System"
    }

@app.post("/update-prompt")
async def change_prompts(request: Request):
    req_json = await request.json()
    for key in req_json:
        system_prompt_value = req_json[key]
        update_prompts(system_prompt_value, key)
    return JSONResponse(content={"message": "Prompt changed successfully!"}, status_code=200)

# ----------- Current Prompt Endpoint ----------- #
@app.get("/current-prompt")
async def current_prompt():
    try:
        current_prompts = {
            "supervisor": system_prompt.supervisor_prompt,
            "sales": system_prompt.sale_system_prompt,
            "rag": system_prompt.rag_system_prompt,
            "web" : system_prompt.web_system_prompt
        }
        return JSONResponse(content=current_prompts, status_code=200)
    except Exception as e:
        return JSONResponse(content={"message": "Failed to retrieve current prompts"}, status_code=500)
    
app.include_router(router)
app.include_router(chat.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
