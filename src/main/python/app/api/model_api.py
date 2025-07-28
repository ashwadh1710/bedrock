from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import logging
from app.services.bedrock_service import BedrockService
from app.utils.aws_utils import AWSUtils

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Model Invocation API")

# Initialize AWS utils and Bedrock service
aws_utils = AWSUtils()
bedrock_service = BedrockService(aws_utils)

class ModelRequest(BaseModel):
    prompt: str

class ModelResponse(BaseModel):
    response: Dict[str, Any]

@app.post("/model/invoke", response_model=ModelResponse)
async def invoke_model(request: ModelRequest):
    try:
        response = bedrock_service.invoke_model(request.prompt)
        return ModelResponse(response=response)
    except Exception as e:
        logger.error(f"Error invoking model: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}