"""
S3 Storage Module for the AI Form Assistant Application
Handles file storage operations using AWS S3 or compatible service (like MinIO)
"""
try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    ClientError = None
    BOTO3_AVAILABLE = False

from typing import Optional, Tuple, BinaryIO
import logging
from io import BytesIO
import uuid
from datetime import datetime

from app.config.settings import settings

logger = logging.getLogger(__name__)


class S3Storage:
    """
    Handles file storage operations using AWS S3 or compatible service (like MinIO)
    """
    def __init__(self):
        if not BOTO3_AVAILABLE:
            logger.warning("boto3 is not available. S3 storage will not be functional.")
            self.s3_client = None
            self.bucket_name = None
            self.region_name = None
            return
            
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region_name = settings.S3_REGION_NAME
        
        # Create S3 client using credentials from settings
        if settings.S3_ENDPOINT_URL:
            # For local S3-compatible services like MinIO
            self.s3_client = boto3.client(
                's3',
                endpoint_url=settings.S3_ENDPOINT_URL,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                region_name=self.region_name
            )
        else:
            # For AWS S3
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                region_name=self.region_name
            )
        
        # Create bucket if it doesn't exist
        self._create_bucket_if_not_exists()

    def _create_bucket_if_not_exists(self):
        """Create the S3 bucket if it doesn't already exist"""
        if not BOTO3_AVAILABLE or self.s3_client is None:
            logger.warning("boto3 is not available. Cannot create S3 bucket.")
            return
            
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket {self.bucket_name} already exists.")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.info(f"Bucket {self.bucket_name} does not exist. Creating it...")
                try:
                    if self.region_name == 'us-east-1':
                        # Special case: us-east-1 doesn't support LocationConstraint
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region_name}
                        )
                    logger.info(f"Bucket {self.bucket_name} created successfully.")
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket {self.bucket_name}: {create_error}")
                    raise
            else:
                logger.error(f"Error checking bucket existence: {e}")
                raise

    def upload_file(self, file_data: bytes, filename: str, content_type: str, metadata: Optional[dict] = None) -> str:
        """
        Uploads a file to S3 and returns the S3 object key (which will serve as our file ID)
        
        Args:
            file_data: The binary file data to upload
            filename: The original filename
            content_type: The content type of the file
            metadata: Optional metadata to store with the file
            
        Returns:
            The S3 object key which will serve as our file identifier
        """
        try:
            # Generate a unique file key (path) for the S3 object
            # Format: {timestamp}/{uuid}-{filename}
            timestamp = datetime.utcnow().strftime("%Y%m%d")
            file_extension = filename.split('.')[-1] if '.' in filename else ''
            unique_id = str(uuid.uuid4())
            file_key = f"{timestamp}/{unique_id}-{filename}"
            
            # Prepare the metadata
            s3_metadata = {
                "original-filename": filename,
                "content-type": content_type,
                "upload-timestamp": datetime.utcnow().isoformat()
            }
            if metadata:
                s3_metadata.update(metadata)
            
            # Upload the file to S3
            file_stream = BytesIO(file_data)
            self.s3_client.upload_fileobj(
                file_stream,
                self.bucket_name,
                file_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'Metadata': s3_metadata
                }
            )
            
            logger.info(f"File uploaded successfully to S3 with key: {file_key}")
            return file_key
            
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise

    def get_file(self, file_key: str) -> Tuple[bytes, str, str, dict]:
        """
        Retrieves a file from S3
        
        Args:
            file_key: The S3 object key of the file to retrieve
            
        Returns:
            A tuple containing (file_content, original_filename, content_type, metadata)
        """
        if not BOTO3_AVAILABLE or self.s3_client is None:
            logger.error("boto3 is not available. Cannot retrieve file from S3.")
            raise RuntimeError("S3 storage is not available. Please install boto3.")
            
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
            
            file_content = response['Body'].read()
            metadata = response.get('Metadata', {})
            original_filename = metadata.get('original-filename', 'unknown')
            content_type = metadata.get('content-type', response.get('ContentType', 'application/octet-stream'))
            
            return file_content, original_filename, content_type, metadata
            
        except ClientError as e:
            logger.error(f"Failed to retrieve file from S3: {e}")
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"File with key {file_key} does not exist in S3 bucket {self.bucket_name}")
            raise

    def delete_file(self, file_key: str) -> bool:
        """
        Deletes a file from S3
        
        Args:
            file_key: The S3 object key of the file to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if not BOTO3_AVAILABLE or self.s3_client is None:
            logger.error("boto3 is not available. Cannot delete file from S3.")
            return False
            
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_key)
            logger.info(f"File with key {file_key} deleted successfully from S3")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            return False

    def file_exists(self, file_key: str) -> bool:
        """
        Checks if a file exists in S3
        
        Args:
            file_key: The S3 object key of the file to check
            
        Returns:
            True if file exists, False otherwise
        """
        if not BOTO3_AVAILABLE or self.s3_client is None:
            logger.warning("boto3 is not available. Cannot check if file exists in S3.")
            return False
            
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise

    def get_file_url(self, file_key: str, expiry: int = 3600) -> str:
        """
        Generates a presigned URL for a file in S3
        
        Args:
            file_key: The S3 object key of the file
            expiry: Time in seconds for the URL to expire (default 1 hour)
            
        Returns:
            Presigned URL for the file
        """
        if not BOTO3_AVAILABLE or self.s3_client is None:
            logger.error("boto3 is not available. Cannot generate presigned URL for S3 file.")
            raise RuntimeError("S3 storage is not available. Please install boto3.")
            
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_key},
                ExpiresIn=expiry
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise