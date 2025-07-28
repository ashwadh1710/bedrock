import boto3
import json
from app.config.settings import AppConfig
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class BedrockService:
    def __init__(self):
        self.client = self._initialize_client()

    def _initialize_client(self):
        return boto3.client(
            service_name='bedrock-runtime',
            region_name=AppConfig.AWS_REGION,
            aws_access_key_id=AppConfig.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AppConfig.AWS_SECRET_ACCESS_KEY
        )

    def invoke_model(self, prompt, max_tokens=512):
        try:
            request_body = {
                "prompt": prompt,
                "maxTokens": max_tokens
            }

            response = self.client.invoke_model(
                modelId=AppConfig.BEDROCK_MODEL_ID,
                body=json.dumps(request_body)
            )

            return json.loads(response['body'].read())
        except Exception as e:
            logger.error(f"Error in model invocation: {str(e)}")
            raise