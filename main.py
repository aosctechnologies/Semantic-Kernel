# main.py

import traceback
import uuid
from typing import List
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from semantic_kernel import Kernel
from semantic_kernel.contents import ChatHistory

# AI Service Imports
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.connectors.ai.open_ai import OpenAIPromptExecutionSettings
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior

# Local Imports
from config.settings import settings 
from config.prompts import SYSTEM_PROMPT 
from kernel.kernel_setup import create_kernel
from models.schemas import ChatRequest, ChatResponse, QueueRequest 
from plugins.queue_handler import QueuePlugin 
from services.http_client import get_client

app = FastAPI(title="Semantic Agent - Assessment First")

# --- CORS Configuration ---
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

kernel: Kernel = None
chat_history: ChatHistory = ChatHistory()

# Initialize the plugin for direct use
queue_plugin = QueuePlugin()

@app.on_event("startup")
async def startup_event():
    global kernel
    try:
        key = settings.OPENROUTER_API_KEY
        if not key:
            print("ERROR: OPENROUTER_API_KEY is empty!")
        else:
            masked_key = f"{key[:10]}...{key[-5:]}"
            print(f"Loaded API Key: {masked_key}")

        kernel = await create_kernel()
        chat_history.add_system_message(SYSTEM_PROMPT)
        print("Application startup complete.")
    except Exception as e:
        print(f"Kernel initialization failed: {str(e)}")
        raise

# --- UPDATED ENDPOINT TO CAPTURE EMAIL ---
@app.post("/invoke-batch")
async def invoke_batch(request: QueueRequest):
    """
    Directly invokes the batch processing queue. 
    Captures 'email' for MongoDB logging but does not pass it to processing APIs.
    """
    run_id = str(uuid.uuid4())
    user_email = request.email # Extract email from request body
    
    print(f"Invoking Batch | Run ID: {run_id} | User: {user_email}")

    project_ids = [item.project_id for item in request.items]
    workbook_ids = [item.workbook_id for item in request.items]

    if not project_ids:
        return {"success": False, "message": "No items provided", "run_id": run_id}

    try:
        # 1. Call the plugin logic - email is passed here for the MongoDB log call
        result_log = await queue_plugin.process_items_queue(
            project_ids=project_ids, 
            workbook_ids=workbook_ids,
            run_id=run_id,
            email=user_email
        )

        return {
            "success": True,
            "run_id": run_id,
            "processed_count": len(project_ids),
            "user_logged": user_email
        }

    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"Batch Invocation Error [Run ID: {run_id}]:", error_detail)

        # Log the failure to MongoDB API including the email
        try:
            async with await get_client() as client:
                await client.post(
                    f"{settings.MONGODB_LOG_API_URL}/api/records/semantic-kernel",
                    json={
                        "project_name": "Semantic-Kernel-Agent-Error",
                        "run_id": run_id,
                        "status": "failed",
                        "payload": {
                            "user_email": user_email,
                            "error": str(e),
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
                )
        except:
            pass

        return {
            "success": False,
            "run_id": run_id,
            "error": str(e)
        }

# --- UPDATED CHAT ENDPOINT ---
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    if kernel is None:
        raise HTTPException(status_code=503, detail="Kernel not initialized yet")

    run_id = str(uuid.uuid4())
    user_email = request.email

    try:
        # Inject email into history so plugins/kernel have the context if needed
        chat_history.add_user_message(f"[User Context: {user_email}]")
        chat_history.add_user_message(request.message)
        
        chat_service = kernel.get_service("openrouter-chat", type=OpenAIChatCompletion)

        execution_settings = OpenAIPromptExecutionSettings(
            service_id="openrouter-chat",
            model_id="openai/gpt-4o-mini", 
            temperature=0.0, 
            max_tokens=2000,
            function_choice_behavior=FunctionChoiceBehavior.Auto() 
        )

        result = await chat_service.get_chat_message_content(
            chat_history=chat_history,
            settings=execution_settings,
            kernel=kernel 
        )

        final_answer = str(result).strip()
        chat_history.add_assistant_message(final_answer)

        return ChatResponse(
            response=final_answer,
            success=True,
            run_id=run_id
        )

    except Exception as e:
        return ChatResponse(
            response=f"Processing error: {str(e)}",
            success=False,
            run_id=run_id
        )

@app.get("/health")
async def health_check():
    return {"status": "ok", "kernel_initialized": kernel is not None}

@app.post("/reset")
async def reset_conversation():
    global chat_history
    chat_history = ChatHistory()
    chat_history.add_system_message(SYSTEM_PROMPT)
    return {"message": "Reset complete"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=9000, reload=True)