import boto3
import json
from botocore.exceptions import ClientError
from typing import Dict, Any, List, Union, Optional
import logging
import requests


logger = logging.getLogger(__name__)

class AWSUtils:
    def __init__(self, profile_name: str = None, region: str = None):
        """
        Initialize AWS clients with automatic detection of execution environment.

        Args:
            profile_name (str, optional): AWS profile name for local development
            region (str, optional): AWS region to use
        """
        self.is_ec2 = self._is_running_on_ec2()
        self.session = self._initialize_session(profile_name, region)

        # Initialize clients using the session
        self.s3_client = self.session.client('s3')
        self.lambda_client = self.session.client('lambda')
        self.bedrock_runtime = self.session.client('bedrock-runtime')
        self.ec2_client = self.session.client('ec2')
        self.sts_client = self.session.client('sts')

    def _is_running_on_ec2(self) -> bool:
        """
        Check if the code is running on an EC2 instance

        Returns:
            bool: True if running on EC2, False otherwise
        """
        try:
            # Try to access EC2 instance metadata service with a timeout of 1 second
            requests.get('http://169.254.169.254/latest/meta-data/', timeout=1)
            return True
        except (requests.RequestException, requests.Timeout):
            return False

    def _initialize_session(self, profile_name: str = None, region: str = None) -> boto3.Session:
        """
        Initialize AWS session based on the execution environment

        Args:
            profile_name (str, optional): AWS profile name for local development
            region (str, optional): AWS region to use

        Returns:
            boto3.Session: Configured AWS session
        """
        if self.is_ec2:
            logger.info("Running on EC2, using instance metadata for credentials")
            return boto3.Session(region_name=region)
        else:
            logger.info("Running locally, using profile or environment credentials")
            return boto3.Session(profile_name=profile_name, region_name=region)

    def setup_local_credentials(self,
                                aws_access_key_id: str,
                                aws_secret_access_key: str,
                                region: str = 'us-east-1',
                                profile_name: str = 'default') -> bool:
        """
        Set up AWS credentials file for local development

        Args:
            aws_access_key_id (str): AWS access key ID
            aws_secret_access_key (str): AWS secret access key
            region (str, optional): AWS region
            profile_name (str, optional): AWS profile name

        Returns:
            bool: True if credentials were set up successfully, False otherwise
        """
        if self.is_ec2:
            logger.warning("Running on EC2, no need to set up local credentials")
            return False

        try:
            # Create ~/.aws directory if it doesn't exist
            aws_dir = Path.home() / '.aws'
            aws_dir.mkdir(exist_ok=True)

            # Initialize config parser
            config = configparser.ConfigParser()

            # Read existing credentials file if it exists
            credentials_file = aws_dir / 'credentials'
            if credentials_file.exists():
                config.read(credentials_file)

            # Add or update profile
            if not config.has_section(profile_name):
                config.add_section(profile_name)

            config[profile_name]['aws_access_key_id'] = aws_access_key_id
            config[profile_name]['aws_secret_access_key'] = aws_secret_access_key

            # Write credentials file
            with open(credentials_file, 'w') as f:
                config.write(f)

            # Update config file with region
            config_file = aws_dir / 'config'
            config = configparser.ConfigParser()

            if config_file.exists():
                config.read(config_file)

            profile_section = f"profile {profile_name}" if profile_name != "default" else "default"
            if not config.has_section(profile_section):
                config.add_section(profile_section)

            config[profile_section]['region'] = region

            with open(config_file, 'w') as f:
                config.write(f)

            # Reinitialize the session with new credentials
            self.session = self._initialize_session(profile_name, region)

            # Reinitialize clients with new session
            self.s3_client = self.session.client('s3')
            self.lambda_client = self.session.client('lambda')
            self.bedrock_runtime = self.session.client('bedrock-runtime')
            self.ec2_client = self.session.client('ec2')
            self.sts_client = self.session.client('sts')

            logger.info(f"Successfully set up AWS credentials for profile: {profile_name}")
            return True

        except Exception as e:
            logger.error(f"Error setting up AWS credentials: {str(e)}")
            return False

    def verify_credentials(self) -> Dict[str, Any]:
        """
        Verify AWS credentials are working and return account information

        Returns:
            dict: Account information and credentials status
        """
        try:
            response = self.sts_client.get_caller_identity()
            return {
                'status': 'valid',
                'account_id': response['Account'],
                'arn': response['Arn'],
                'user_id': response['UserId'],
                'environment': 'ec2' if self.is_ec2 else 'local'
            }
        except Exception as e:
            return {
                'status': 'invalid',
                'error': str(e),
                'environment': 'ec2' if self.is_ec2 else 'local'
            }


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

# # Example test setup
# def setup_test_environment():
#     # For local testing
#     aws_utils = AWSUtils(profile_name='test')
#
#     # Set up test credentials if needed
#     if not aws_utils.is_ec2:
#         aws_utils.setup_local_credentials(
#             aws_access_key_id='TEST_ACCESS_KEY_ID',
#             aws_secret_access_key='TEST_SECRET_ACCESS_KEY',
#             region='us-west-2',
#             profile_name='test'
#         )
#
#     return aws_utils
#
# # In your tests
# def test_aws_operations():
#     aws_utils = setup_test_environment()
#
#     # Verify credentials are working
#     creds_status = aws_utils.verify_credentials()
#     assert creds_status['status'] == 'valid'
#
#     # Test AWS operations
#     result = aws_utils.list_s3_objects('test-bucket')
#     # Add assertions...



