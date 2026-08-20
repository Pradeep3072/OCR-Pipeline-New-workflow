import boto3
from botocore.client import Config
import os
import io
from logger import get_logger

logger = get_logger(__name__)

S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
S3_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
S3_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "ocr-bucket")

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        config=Config(signature_version='s3v4')
    )

def ensure_bucket_exists():
    s3 = get_s3_client()
    try:
        s3.head_bucket(Bucket=S3_BUCKET_NAME)
    except Exception:
        s3.create_bucket(Bucket=S3_BUCKET_NAME)

def upload_file_to_s3(file_path_or_bytes, object_name):
    s3 = get_s3_client()
    ensure_bucket_exists()
    
    if isinstance(file_path_or_bytes, str):
        s3.upload_file(file_path_or_bytes, S3_BUCKET_NAME, object_name)
    else:
        # file_path_or_bytes is bytes or a file-like object
        if isinstance(file_path_or_bytes, bytes):
            s3.put_object(Bucket=S3_BUCKET_NAME, Key=object_name, Body=file_path_or_bytes)
        else:
            s3.upload_fileobj(file_path_or_bytes, S3_BUCKET_NAME, object_name)

def download_file_from_s3(object_name, download_path):
    s3 = get_s3_client()
    s3.download_file(S3_BUCKET_NAME, object_name, download_path)

def get_file_bytes_from_s3(object_name):
    s3 = get_s3_client()
    try:
        response = s3.get_object(Bucket=S3_BUCKET_NAME, Key=object_name)
        return response['Body'].read()
    except Exception as e:
        logger.error(f"Error fetching {object_name} from S3: {e}")
        return None
