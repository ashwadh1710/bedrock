import boto3
import json
from botocore.exceptions import ClientError
from typing import Dict, Any, List, Union, Optional
import logging

logger = logging.getLogger(__name__)

class AWSUtils:
    def __init__(self):
        """
        Initialize AWS clients using EC2 instance IAM role credentials.
        boto3 will automatically use the IAM role credentials when running on EC2.
        """
        self.s3_client = boto3.client('s3')
        self.lambda_client = boto3.client('lambda')
        self.bedrock_runtime = boto3.client('bedrock-runtime')
        self.s3_client = boto3.client('s3')
        self.lambda_client = boto3.client('lambda')
        self.bedrock_runtime = boto3.client('bedrock-runtime')
        self.ec2_client = boto3.client('ec2')
        self.sts_client = boto3.client('sts')

    # S3 Operations
    def upload_to_s3(self, file_content: Union[bytes, str], bucket: str, key: str) -> bool:
        """
        Upload content to S3 bucket
        """
        try:
            if isinstance(file_content, str):
                file_content = file_content.encode('utf-8')
            self.s3_client.put_object(Bucket=bucket, Key=key, Body=file_content)
            return True
        except ClientError as e:
            logger.error(f"Error uploading to S3: {str(e)}")
            return False

    def download_from_s3(self, bucket: str, key: str) -> Union[bytes, None]:
        """
        Download content from S3 bucket
        """
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"Error downloading from S3: {str(e)}")
            return None

    def list_s3_objects(self, bucket: str, prefix: str = '') -> List[Dict]:
        """
        List objects in S3 bucket with optional prefix
        """
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            return response.get('Contents', [])
        except ClientError as e:
            logger.error(f"Error listing S3 objects: {str(e)}")
            return []

    # Lambda Operations
    def invoke_lambda(self, function_name: str, payload: Dict[str, Any]) -> Dict:
        """
        Invoke AWS Lambda function
        """
        try:
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            return {
                'StatusCode': response['StatusCode'],
                'Payload': json.loads(response['Payload'].read().decode('utf-8'))
            }
        except ClientError as e:
            logger.error(f"Error invoking Lambda function: {str(e)}")
            return {'StatusCode': 500, 'Error': str(e)}

    def list_lambda_functions(self) -> List[str]:
        """
        List all Lambda functions
        """
        try:
            response = self.lambda_client.list_functions()
            return [function['FunctionName'] for function in response['Functions']]
        except ClientError as e:
            logger.error(f"Error listing Lambda functions: {str(e)}")
            return []

    # Bedrock Runtime Operations
    def invoke_bedrock_model(self,
                             model_id: str,
                             prompt: str,
                             max_tokens: int = 512) -> Dict:
        """
        Invoke Amazon Bedrock model
        """
        try:
            request_body = {
                "prompt": prompt,
                "max_tokens_to_generate": max_tokens,
                "temperature": 0.7,
                "top_p": 0.9,
            }

            response = self.bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )

            response_body = json.loads(response.get('body').read())
            return response_body
        except ClientError as e:
            logger.error(f"Error invoking Bedrock model: {str(e)}")
            return {'error': str(e)}

    def get_account_id_from_lambda_arn(self, lambda_arn: str) -> Optional[str]:
        """
        Extract AWS account ID from Lambda ARN

        Args:
            lambda_arn (str): Lambda ARN in format
                'arn:aws:lambda:region:account-id:function:function-name'

        Returns:
            str: AWS account ID or None if parsing fails
        """
        try:
            # ARN format: arn:aws:lambda:region:account-id:function:function-name
            arn_parts = lambda_arn.split(':')
            if len(arn_parts) >= 5:
                return arn_parts[4]
            return None
        except Exception as e:
            logger.error(f"Error parsing Lambda ARN: {str(e)}")
            return None

    def get_lambda_function_arn(self, function_name: str) -> Optional[str]:
        """
        Get the full ARN of a Lambda function

        Args:
            function_name (str): Name of the Lambda function

        Returns:
            str: Lambda function ARN or None if not found
        """
        try:
            response = self.lambda_client.get_function(FunctionName=function_name)
            return response['Configuration']['FunctionArn']
        except ClientError as e:
            logger.error(f"Error getting Lambda function ARN: {str(e)}")
            return None

    def get_current_account_id(self) -> Optional[str]:
        """
        Get the current AWS account ID using STS

        Returns:
            str: AWS account ID or None if failed
        """
        try:
            response = self.sts_client.get_caller_identity()
            return response['Account']
        except ClientError as e:
            logger.error(f"Error getting AWS account ID: {str(e)}")
            return None

    def get_instance_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the current EC2 instance

        Returns:
            dict: Instance metadata including AZ, instance ID, and region
        """
        try:
            # Get instance ID from instance metadata service
            instance_identity = boto3.client('ec2').describe_instances()

            # Extract relevant information from the first instance
            reservations = instance_identity['Reservations']
            if reservations and reservations[0]['Instances']:
                instance = reservations[0]['Instances'][0]
                return {
                    'instance_id': instance['InstanceId'],
                    'availability_zone': instance['Placement']['AvailabilityZone'],
                    'region': instance['Placement']['AvailabilityZone'][:-1],  # Remove AZ letter to get region
                    'instance_type': instance['InstanceType'],
                    'private_ip': instance.get('PrivateIpAddress'),
                    'public_ip': instance.get('PublicIpAddress'),
                    'vpc_id': instance.get('VpcId'),
                    'subnet_id': instance.get('SubnetId')
                }
            return {}
        except Exception as e:
            logger.error(f"Error getting instance metadata: {str(e)}")
            return {}

    def get_account_id_from_az(self, availability_zone: Optional[str] = None) -> Optional[str]:
        """
        Get AWS account ID from the instance running in specified AZ
        If no AZ is provided, uses the current instance's AZ

        Args:
            availability_zone (str, optional): Availability Zone to query

        Returns:
            str: AWS account ID or None if failed
        """
        try:
            if not availability_zone:
                # If no AZ provided, get it from current instance
                instance_metadata = self.get_instance_metadata()
                availability_zone = instance_metadata.get('availability_zone')

            if not availability_zone:
                raise ValueError("Could not determine availability zone")

            # Use STS to get account ID
            return self.get_current_account_id()
        except Exception as e:
            logger.error(f"Error getting account ID from AZ: {str(e)}")
            return None



