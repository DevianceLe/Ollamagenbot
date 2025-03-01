print("""
                                                               
     ╔═══════════════════════════════════════════════╗         
     ║           Ollama Chat Bot Bridge              ║         
     ║                    Version 0.9                ║         
     ╚═══════════════════════════════════════════════╝         
                                                                
     GitHub: @DevianceLe                              
     X.com:  @DevianceLe       
     Greetz: @WWelna @TexSantos @acidvegas @SuperNETS
                                    
    """)

import asyncio
import aiohttp
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from typing import List, Dict, Any, Tuple
import json
import time
from contextlib import asynccontextmanager

# Configuration
MAX_CONCURRENT_REQUESTS = 1  # Maximum number of concurrent requests to Ollama
OLLAMA_API_URL = "http://localhost:11434/api/chat"
BRIDGE_HOST = "0.0.0.0"
BRIDGE_PORT = 11435  # Different from Ollama's port

# Initialize FastAPI app with lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the queue processor on startup
    queue_processor_task = asyncio.create_task(process_queue())
    yield
    # Cleanup (if needed) can go here
    queue_processor_task.cancel()
    try:
        await queue_processor_task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

# Create a queue for requests
request_queue = asyncio.Queue()
# Create a single semaphore for processing one request at a time
request_semaphore = asyncio.Semaphore(1)

class ChatRequest(BaseModel):
    model: str
    messages: List[Dict[str, str]]
    stream: bool = False

async def forward_to_ollama(data: Dict[str, Any]) -> Dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    
    async with request_semaphore:  # Limit concurrent requests
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    OLLAMA_API_URL,
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 minute timeout
                ) as response:
                    response.raise_for_status()
                    # Format response to match what the bot expects
                    ollama_response = await response.json()
                    return {
                        "message": {
                            "role": "assistant",
                            "content": ollama_response.get("message", {}).get("content", "")
                        }
                    }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Ollama API error: {str(e)}")

# Background task to process queued requests
async def process_queue():
    while True:
        data, future, timestamp = await request_queue.get()
        current_size = request_queue.qsize()
        print(f"Current queue size: {current_size}")
        
        # Clear queue if size reaches 10
        if current_size >= 10:
            # Cancel all remaining items in queue
            while not request_queue.empty():
                _, pending_future, _ = await request_queue.get()
                pending_future.set_exception(HTTPException(
                    status_code=503, 
                    detail="Queue cleared due to high load"
                ))
                request_queue.task_done()
            print("Queue cleared due to high load")
        
        # Check if request has expired (waited more than 250 seconds)
        if time.time() - timestamp > 250:
            future.set_exception(HTTPException(status_code=408, detail="Request timeout - queue wait time exceeded 250 seconds"))
            request_queue.task_done()
            continue
            
        try:
            result = await forward_to_ollama(data)
            future.set_result(result)
        except Exception as e:
            future.set_exception(e)
        finally:
            request_queue.task_done()

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # Create a future to get the result
        future = asyncio.Future()
        # Queue the request with current timestamp
        await request_queue.put((request.dict(), future, time.time()))
        # Wait for the result
        result = await future
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def start_bridge():
    uvicorn.run(app, host=BRIDGE_HOST, port=BRIDGE_PORT)

if __name__ == "__main__":
    start_bridge()
