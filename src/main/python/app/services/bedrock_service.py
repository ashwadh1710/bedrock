from typing import Dict, Any
import json
import logging
from app.utils.aws_utils import AWSUtils

logger = logging.getLogger(__name__)

class BedrockService:
    def __init__(self, aws_utils: AWSUtils):
        self.aws_utils = aws_utils
        self.bedrock_runtime = aws_utils.bedrock_runtime

    def invoke_model(self, prompt: str) -> Dict[str, Any]:
        """
        Invoke AWS Bedrock model with the given prompt

        Args:
            prompt (str): The prompt to send to the model

        Returns:
            Dict[str, Any]: Model response
        """
        try:
            # Configure the request body for Claude model
            request_body = {
                "prompt": prompt,
                "max_tokens_to_sample": 2048,
                "temperature": 0.7,
                "top_p": 1,
                "stop_sequences": ["\n\nHuman:"]
            }

            # Invoke the model
            response = self.bedrock_runtime.invoke_model(
                modelId="anthropic.claude-v2",
                body=json.dumps(request_body)
            )

            # Parse the response
            response_body = json.loads(response['body'].read())

            return {
                "generated_text": response_body.get('completion', ''),
                "model_id": "anthropic.claude-v2",
                "prompt_tokens": response_body.get('prompt_tokens', 0),
                "completion_tokens": response_body.get('completion_tokens', 0)
            }

        except Exception as e:
            logger.error(f"Error invoking Bedrock model: {str(e)}")
            raise