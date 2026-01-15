# file: server.py
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from Xfrate2.utils import logger
from Xfrate2.main import build_agent # Ensure main.py has build_agent() exposed

# --- API Models ---
class ExtractionRequest(BaseModel):
    document_url: str
    request_id: Optional[str] = "req_default"

class ExtractionResponse(BaseModel):
    status: str
    request_id: str
    metrics: Dict[str, int]
    successful_orders: List[Dict[str, Any]]
    orders_requiring_review: List[Dict[str, Any]]

# --- App Setup ---
app = FastAPI(title="FTL Extraction Agent", version="1.0")

# Build the Graph once on startup
logger.info("Initializing AI Agent...")
agent_app = build_agent()

@app.post("/extract", response_model=ExtractionResponse)
async def extract_endpoint(payload: ExtractionRequest):
    logger.info(f"Received Request: {payload.request_id}")
    
    # 1. Prepare Initial State
    initial_state = {
        "document_url": payload.document_url,
        "file_path": "", # Will be handled by Node 1
        "extracted_text": "",
        "file_type": "",
        "raw_extraction": {},
        "validation_errors": [],
        "final_orders": [],
        "needs_review": []
    }

    try:
        # 2. Run the Agent
        result = agent_app.invoke(initial_state)
        
        # 3. Format Response
        success_list = result.get("final_orders", [])
        review_list = result.get("needs_review", [])
        
        return ExtractionResponse(
            status="completed",
            request_id=payload.request_id,
            metrics={
                "total_found": len(success_list) + len(review_list),
                "success": len(success_list),
                "needs_review": len(review_list)
            },
            successful_orders=success_list,
            orders_requiring_review=review_list
        )

    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Start the server locally
    uvicorn.run(app, host="0.0.0.0", port=8000)