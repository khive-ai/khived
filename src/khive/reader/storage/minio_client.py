import logging
import boto3
from botocore.exceptions import ClientError
from io import BytesIO
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class ObjectStorageClient:
    """
    A client for interacting with S3-compatible object storage like MinIO.
    """

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        region_name: Optional[str] = None,
        secure: bool = True,
    ):
        """
        Initializes the MinIO client.

        Args:
            endpoint_url: The URL of the MinIO server.
            access_key: The access key for MinIO.
            secret_key: The secret key for MinIO.
            bucket_name: The default bucket name to use.
            region_name: The region name (optional).
            secure: Whether to use HTTPS (default: True).
        """
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.secure = secure

        try:
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region_name,
                use_ssl=self.secure,
                # config=boto3.session.Config(signature_version='s3v4') # May be needed for some S3 providers
            )
            logger.info(
                f"Successfully initialized S3 client for bucket '{self.bucket_name}' at endpoint '{self.endpoint_url}'"
            )
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}", exc_info=True)
            raise

    def upload_object(
        self,
        object_name: str,
        data: bytes,
        bucket_name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
    ) -> bool:
        """
        Uploads an object to the specified S3 bucket.

        Args:
            object_name: The name of the object in the bucket.
            data: The byte content of the object.
            bucket_name: The name of the bucket (defaults to instance's bucket_name).
            metadata: A dictionary of metadata to store with the object.
            content_type: The MIME type of the object.

        Returns:
            True if upload was successful, False otherwise.
        """
        target_bucket = bucket_name or self.bucket_name
        try:
            extra_args: Dict[str, Any] = {}
            if metadata:
                extra_args["Metadata"] = metadata
            if content_type:
                extra_args["ContentType"] = content_type

            self.s3_client.upload_fileobj(
                BytesIO(data), target_bucket, object_name, ExtraArgs=extra_args
            )
            logger.info(
                f"Successfully uploaded object '{object_name}' to bucket '{target_bucket}'"
            )
            return True
        except ClientError as e:
            logger.error(
                f"Failed to upload object '{object_name}' to bucket '{target_bucket}': {e}",
                exc_info=True,
            )
            return False
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while uploading object '{object_name}' to bucket '{target_bucket}': {e}",
                exc_info=True,
            )
            return False

    def download_object(
        self, object_name: str, bucket_name: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Downloads an object from the specified S3 bucket.

        Args:
            object_name: The name of the object in the bucket.
            bucket_name: The name of the bucket (defaults to instance's bucket_name).

        Returns:
            The byte content of the object, or None if download failed.
        """
        target_bucket = bucket_name or self.bucket_name
        try:
            response = self.s3_client.get_object(Bucket=target_bucket, Key=object_name)
            object_data = response["Body"].read()
            logger.info(
                f"Successfully downloaded object '{object_name}' from bucket '{target_bucket}'"
            )
            return object_data
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.warning(
                    f"Object '{object_name}' not found in bucket '{target_bucket}'."
                )
            else:
                logger.error(
                    f"Failed to download object '{object_name}' from bucket '{target_bucket}': {e}",
                    exc_info=True,
                )
            return None
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while downloading object '{object_name}' from bucket '{target_bucket}': {e}",
                exc_info=True,
            )
            return None

    def get_presigned_url(
        self,
        object_name: str,
        bucket_name: Optional[str] = None,
        expiration: int = 3600,
        http_method: str = "GET",
    ) -> Optional[str]:
        """
        Generates a presigned URL for an S3 object.

        Args:
            object_name: The name of the object in the bucket.
            bucket_name: The name of the bucket (defaults to instance's bucket_name).
            expiration: Time in seconds for the presigned URL to remain valid (default: 3600).
            http_method: The HTTP method allowed for the presigned URL (e.g., 'GET', 'PUT').
                         Typically 'GET' for downloads, 'PUT' for uploads.

        Returns:
            The presigned URL as a string, or None if generation failed.
        """
        target_bucket = bucket_name or self.bucket_name
        s3_method_name = None
        if http_method.upper() == "GET":
            s3_method_name = "get_object"
        elif http_method.upper() == "PUT":
            s3_method_name = "put_object"
        # Add other methods like 'DELETE' if needed
        else:
            logger.error(f"Unsupported HTTP method '{http_method}' for presigned URL.")
            return None

        try:
            params = {"Bucket": target_bucket, "Key": object_name}
            url = self.s3_client.generate_presigned_url(
                ClientMethod=s3_method_name,
                Params=params,
                ExpiresIn=expiration,
                HttpMethod=http_method.upper(),
            )
            logger.info(
                f"Successfully generated {http_method.upper()} presigned URL for object '{object_name}' in bucket '{target_bucket}'"
            )
            return url
        except ClientError as e:
            logger.error(
                f"Failed to generate presigned URL for object '{object_name}' in bucket '{target_bucket}': {e}",
                exc_info=True,
            )
            return None
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while generating presigned URL for object '{object_name}' in bucket '{target_bucket}': {e}",
                exc_info=True,
            )
            return None

    def object_exists(
        self, object_name: str, bucket_name: Optional[str] = None
    ) -> bool:
        """
        Checks if an object exists in the specified S3 bucket.

        Args:
            object_name: The name of the object in the bucket.
            bucket_name: The name of the bucket (defaults to instance's bucket_name).

        Returns:
            True if the object exists, False otherwise.
        """
        target_bucket = bucket_name or self.bucket_name
        try:
            self.s3_client.head_object(Bucket=target_bucket, Key=object_name)
            logger.debug(
                f"Object '{object_name}' exists in bucket '{target_bucket}'."
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logger.debug(
                    f"Object '{object_name}' does not exist in bucket '{target_bucket}'."
                )
                return False
            logger.error(
                f"Error checking existence of object '{object_name}' in bucket '{target_bucket}': {e}",
                exc_info=True,
            )
            return False # Or raise, depending on desired error handling
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while checking existence of object '{object_name}' in bucket '{target_bucket}': {e}",
                exc_info=True,
            )
            return False

    def ensure_bucket_exists(self, bucket_name: Optional[str] = None) -> bool:
        """
        Ensures that the specified bucket exists, creating it if necessary.
        Note: Bucket creation permissions are required.

        Args:
            bucket_name: The name of the bucket (defaults to instance's bucket_name).

        Returns:
            True if the bucket exists or was successfully created, False otherwise.
        """
        target_bucket = bucket_name or self.bucket_name
        try:
            self.s3_client.head_bucket(Bucket=target_bucket)
            logger.info(f"Bucket '{target_bucket}' already exists.")
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404": # Not Found
                logger.info(f"Bucket '{target_bucket}' not found. Attempting to create.")
                try:
                    # For MinIO, region is often not strictly required for bucket creation
                    # but some S3 providers might need it.
                    create_bucket_config = {}
                    if self.region_name and self.region_name != "us-east-1": # us-east-1 is default and often doesn't need explicit LocationConstraint
                        create_bucket_config['LocationConstraint'] = self.region_name
                    
                    if create_bucket_config:
                        self.s3_client.create_bucket(Bucket=target_bucket, CreateBucketConfiguration=create_bucket_config)
                    else:
                        self.s3_client.create_bucket(Bucket=target_bucket)

                    logger.info(f"Successfully created bucket '{target_bucket}'.")
                    return True
                except ClientError as ce:
                    logger.error(f"Failed to create bucket '{target_bucket}': {ce}", exc_info=True)
                    return False
                except Exception as ex:
                    logger.error(f"Unexpected error creating bucket '{target_bucket}': {ex}", exc_info=True)
                    return False
            else:
                logger.error(f"Error checking bucket '{target_bucket}': {e}", exc_info=True)
                return False
        except Exception as e:
            logger.error(f"Unexpected error checking bucket '{target_bucket}': {e}", exc_info=True)
            return False

if __name__ == "__main__":
    # Example Usage (requires MinIO server running and configured .env or similar for credentials)
    # This is for illustrative purposes and should be adapted for actual use.
    import os
    from dotenv import load_dotenv

    load_dotenv() # Load environment variables from .env file

    MINIO_ENDPOINT_URL = os.getenv("MINIO_ENDPOINT_URL", "http://localhost:9000")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "khive-reader-dev")

    logging.basicConfig(level=logging.INFO)

    if not all([MINIO_ENDPOINT_URL, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET_NAME]):
        logger.error("MinIO environment variables not fully set. Skipping example.")
    else:
        try:
            client = ObjectStorageClient(
                endpoint_url=MINIO_ENDPOINT_URL,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                bucket_name=MINIO_BUCKET_NAME,
                secure=MINIO_ENDPOINT_URL.startswith("https"),
            )

            # Ensure bucket exists
            if not client.ensure_bucket_exists():
                logger.error(f"Failed to ensure bucket '{client.bucket_name}' exists. Aborting example.")
            else:
                # 1. Upload an object
                test_object_name = "test_file.txt"
                test_data = b"Hello from khive ObjectStorageClient!"
                if client.upload_object(test_object_name, test_data, content_type="text/plain"):
                    logger.info(f"Uploaded '{test_object_name}' successfully.")

                    # 2. Check if object exists
                    if client.object_exists(test_object_name):
                        logger.info(f"Object '{test_object_name}' confirmed to exist.")
                    else:
                        logger.error(f"Object '{test_object_name}' does not exist after upload.")

                    # 3. Download the object
                    downloaded_data = client.download_object(test_object_name)
                    if downloaded_data:
                        logger.info(f"Downloaded data: {downloaded_data.decode()}")
                        assert downloaded_data == test_data

                    # 4. Get a presigned URL for GET
                    get_url = client.get_presigned_url(test_object_name, http_method="GET")
                    if get_url:
                        logger.info(f"Presigned GET URL: {get_url}")
                        # You can try opening this URL in a browser or with curl

                    # 5. Get a presigned URL for PUT (for uploading)
                    put_object_name = "upload_via_presigned.txt"
                    put_url = client.get_presigned_url(put_object_name, http_method="PUT", expiration=600)
                    if put_url:
                        logger.info(f"Presigned PUT URL (valid for 10 mins): {put_url}")
                        logger.info(f"Try: curl -X PUT -T /path/to/your/local/file.txt '{put_url}' -H 'Content-Type: text/plain'")

                else:
                    logger.error(f"Failed to upload '{test_object_name}'.")

                # Example of non-existent object
                logger.info(f"Checking for non-existent object 'does_not_exist.txt': {client.object_exists('does_not_exist.txt')}")
                logger.info(f"Attempting to download non-existent object: {client.download_object('does_not_exist.txt')}")

        except Exception as e:
            logger.error(f"Error in ObjectStorageClient example: {e}", exc_info=True)