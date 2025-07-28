import requests
from typing import Dict, Any, Optional
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class ModelClient:
    def __init__(
            self,
            base_url: str = "http://localhost:8000",
            timeout: int = 30,
            max_retries: int = 3
    ):
        """
        Initialize Model API client

        Args:
            base_url (str): Base URL of the API
            timeout (int): Request timeout in seconds
            max_retries (int): Maximum number of retries for failed requests
        """
        self.base_url = base_url
        self.timeout = timeout
        self.session = self._create_session(max_retries)

    def _create_session(self, max_retries: int) -> requests.Session:
        """Create a session with retry strategy"""
        session = requests.Session()

        retries = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )

        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))

        return session

    def invoke_model(self, prompt: str) -> Dict[str, Any]:
        """
        Invoke the model API

        Args:
            prompt (str): The prompt to send to the model

        Returns:
            Dict[str, Any]: Model response
        """
        url = f"{self.base_url}/model/invoke"
        headers = {"Content-Type": "application/json"}
        data = {"prompt": prompt}

        try:
            response = self.session.post(
                url,
                json=data,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            logger.error("Request timed out")
            raise TimeoutError("Request to model API timed out")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling model API: {str(e)}")
            raise

    def health_check(self) -> Dict[str, str]:
        """Check API health status"""
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Health check failed: {str(e)}")
            raise

    def close(self):
        """Close the session"""
        self.session.close()

# @contextmanager
# def model_client(
#         base_url: str = "http://localhost:8000",
#         timeout: int = 30,
#         max_retries: int = 3
# ):
#     """Context manager for ModelClient"""
#     client = ModelClient(base_url, timeout, max_retries)
#     try:
#         yield client
#     finally:
#         client.close()
#
# # Example usage
# from app.client.model_client import model_client
#
# # Using with context manager (recommended)
# with model_client(base_url="http://localhost:8000") as client:
#     # Check API health
#     health_status = client.health_check()
#     print("API Health:", health_status)
#
#     # Invoke model
#     try:
#         result = client.invoke_model(
#             prompt="Explain what is machine learning in simple terms"
#         )
#         print("Model Response:", result)
#     except Exception as e:
#         print(f"Error: {str(e)}")
#
# # Alternative usage without context manager
# client = ModelClient(base_url="http://localhost:8000")
# try:
#     result = client.invoke_model(
#         prompt="Write a short story about AI"
#     )
#     print(result)
# finally:
#     client.close()
# import requests
#
# # Simple one-off request
# response = requests.post(
#     "http://localhost:8000/model/invoke",
#     json={"prompt": "Tell me a joke about programming"},
#     headers={"Content-Type": "application/json"}
# )
# print(response.json())