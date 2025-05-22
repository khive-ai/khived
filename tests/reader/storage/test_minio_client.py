from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from khive.reader.storage.minio_client import ObjectStorageClient


@pytest.fixture
def mock_boto_s3_constructor():  # Renamed to reflect it's the constructor mock
    # Patch boto3.client where it's used in the ObjectStorageClient module
    with patch("khive.reader.storage.minio_client.boto3.client") as mock_constructor:
        # The constructor itself will be called; its return_value is the s3 client instance
        mock_s3_instance = MagicMock()
        mock_constructor.return_value = mock_s3_instance
        yield mock_constructor  # Yield the constructor mock to assert calls to it


@pytest.fixture
def mock_s3_client_instance(mock_boto_s3_constructor: MagicMock):
    # This fixture provides the S3 client instance that the ObjectStorageClient will use.
    # It depends on mock_boto_s3_constructor to ensure patching is active.
    return mock_boto_s3_constructor.return_value


@pytest.fixture
def storage_client_config():
    return {
        "endpoint_url": "http://localhost:9000",
        "access_key": "test_access_key",
        "secret_key": "test_secret_key",
        "bucket_name": "test-bucket",
        "region_name": "us-east-1",
        "secure": False,
    }


@pytest.fixture
def client(
    storage_client_config, mock_boto_s3_constructor: MagicMock
):  # Corrected dependency
    # mock_boto_s3_constructor ensures that when ObjectStorageClient calls boto3.client,
    # it gets the mocked constructor. This fixture instantiates an ObjectStorageClient,
    # so the patch needs to be active.
    return ObjectStorageClient(**storage_client_config)


# Removed duplicate: return ObjectStorageClient(**storage_client_config) at line 41


def test_object_storage_client_initialization(
    storage_client_config, mock_boto_s3_constructor: MagicMock
):
    """Test client initialization and that boto3.client is called correctly."""
    ObjectStorageClient(
        **storage_client_config
    )  # Instantiate to trigger the constructor
    mock_boto_s3_constructor.assert_called_once_with(  # Assert on the constructor mock
        "s3",
        endpoint_url=storage_client_config["endpoint_url"],
        aws_access_key_id=storage_client_config["access_key"],
        aws_secret_access_key=storage_client_config["secret_key"],
        region_name=storage_client_config["region_name"],
        use_ssl=storage_client_config["secure"],
    )


# Tests below should use mock_s3_client_instance for asserting calls on the S3 client
def test_upload_object_success(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    object_name = "test_obj.txt"
    data = b"test data"
    metadata = {"custom": "value"}
    content_type = "text/plain"

    result = client.upload_object(
        object_name, data, metadata=metadata, content_type=content_type
    )

    assert result is True
    mock_s3_client_instance.upload_fileobj.assert_called_once()
    args, kwargs = mock_s3_client_instance.upload_fileobj.call_args
    assert isinstance(args[0], BytesIO)
    assert args[0].read() == data
    assert args[1] == client.bucket_name
    assert args[2] == object_name
    assert kwargs["ExtraArgs"] == {"Metadata": metadata, "ContentType": content_type}


def test_upload_object_client_error(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    mock_s3_client_instance.upload_fileobj.side_effect = ClientError(
        {"Error": {"Code": "SomeError", "Message": "Details"}}, "upload_fileobj"
    )
    result = client.upload_object("test.txt", b"data")
    assert result is False


def test_upload_object_unexpected_error(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    mock_s3_client_instance.upload_fileobj.side_effect = Exception("Unexpected")
    result = client.upload_object("test.txt", b"data")
    assert result is False


def test_download_object_success(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    object_name = "test_obj.txt"
    expected_data = b"downloaded data"
    mock_response = {"Body": BytesIO(expected_data)}
    mock_s3_client_instance.get_object.return_value = mock_response

    result = client.download_object(object_name)

    assert result == expected_data
    mock_s3_client_instance.get_object.assert_called_once_with(
        Bucket=client.bucket_name, Key=object_name
    )


def test_download_object_no_such_key(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    mock_s3_client_instance.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}, "get_object"
    )
    result = client.download_object("non_existent.txt")
    assert result is None


def test_download_object_client_error(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    mock_s3_client_instance.get_object.side_effect = ClientError(
        {"Error": {"Code": "SomeError", "Message": "Details"}}, "get_object"
    )
    result = client.download_object("test.txt")
    assert result is None


def test_download_object_unexpected_error(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    mock_s3_client_instance.get_object.side_effect = Exception("Unexpected")
    result = client.download_object("test.txt")
    assert result is None


def test_get_presigned_url_get_success(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    object_name = "test_obj.txt"
    expected_url = "http://presigned.url/test_obj.txt"
    mock_s3_client_instance.generate_presigned_url.return_value = expected_url

    result = client.get_presigned_url(object_name, expiration=60, http_method="GET")

    assert result == expected_url
    mock_s3_client_instance.generate_presigned_url.assert_called_once_with(
        ClientMethod="get_object",
        Params={"Bucket": client.bucket_name, "Key": object_name},
        ExpiresIn=60,
        HttpMethod="GET",
    )


def test_get_presigned_url_put_success(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    object_name = "upload_obj.txt"
    expected_url = "http://presigned.url/upload_obj.txt"
    mock_s3_client_instance.generate_presigned_url.return_value = expected_url

    result = client.get_presigned_url(object_name, expiration=300, http_method="PUT")

    assert result == expected_url
    mock_s3_client_instance.generate_presigned_url.assert_called_once_with(
        ClientMethod="put_object",
        Params={"Bucket": client.bucket_name, "Key": object_name},
        ExpiresIn=300,
        HttpMethod="PUT",
    )


def test_get_presigned_url_unsupported_method(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    result = client.get_presigned_url("test.txt", http_method="DELETE")
    assert result is None
    mock_s3_client_instance.generate_presigned_url.assert_not_called()


def test_get_presigned_url_client_error(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    mock_s3_client_instance.generate_presigned_url.side_effect = ClientError(
        {"Error": {"Code": "SomeError", "Message": "Details"}}, "generate_presigned_url"
    )
    result = client.get_presigned_url("test.txt")
    assert result is None


def test_get_presigned_url_unexpected_error(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    mock_s3_client_instance.generate_presigned_url.side_effect = Exception("Unexpected")
    result = client.get_presigned_url("test.txt")
    assert result is None


def test_object_exists_true(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    mock_s3_client_instance.head_object.return_value = {}  # Success, no error
    result = client.object_exists("existing_obj.txt")
    assert result is True
    mock_s3_client_instance.head_object.assert_called_once_with(
        Bucket=client.bucket_name, Key="existing_obj.txt"
    )


def test_object_exists_false_404(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    mock_s3_client_instance.head_object.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "head_object"
    )
    result = client.object_exists("non_existing_obj.txt")
    assert result is False


def test_object_exists_client_error(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    mock_s3_client_instance.head_object.side_effect = ClientError(
        {"Error": {"Code": "SomeError", "Message": "Details"}}, "head_object"
    )
    result = client.object_exists("test.txt")
    assert (
        result is False
    )  # Or True/raise depending on how you want to handle non-404 errors


def test_object_exists_unexpected_error(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    mock_s3_client_instance.head_object.side_effect = Exception("Unexpected")
    result = client.object_exists("test.txt")
    assert result is False


def test_ensure_bucket_exists_already_exists(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    mock_s3_client_instance.head_bucket.return_value = {}  # Bucket exists
    result = client.ensure_bucket_exists()
    assert result is True
    mock_s3_client_instance.head_bucket.assert_called_once_with(
        Bucket=client.bucket_name
    )
    mock_s3_client_instance.create_bucket.assert_not_called()


def test_ensure_bucket_exists_creates_new_bucket_no_region_constraint(
    client: ObjectStorageClient,
    mock_s3_client_instance: MagicMock,
    storage_client_config,
    mock_boto_s3_constructor: MagicMock,
):
    # Simulate bucket not found, then successful creation
    mock_s3_client_instance.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "head_bucket"
    )
    mock_s3_client_instance.create_bucket.return_value = {}

    # Test with a client configured for us-east-1 or no region, where LocationConstraint is not needed
    client_us_east_1_config = storage_client_config.copy()
    client_us_east_1_config["region_name"] = "us-east-1"  # or None
    client_us_east_1 = ObjectStorageClient(**client_us_east_1_config)

    result = (
        client_us_east_1.ensure_bucket_exists()
    )  # This will use the mock_s3_client_instance associated with client_us_east_1
    assert result is True

    # The mock_s3_client_instance is shared if not careful.
    # We need to ensure we are checking the calls on the correct instance or reset calls.
    # For this test, ObjectStorageClient is re-instantiated, so it gets a fresh s3 client from the patched constructor.
    # The mock_boto_s3_constructor.return_value is the one used by client_us_east_1.
    s3_instance_for_client_us_east_1 = mock_boto_s3_constructor.return_value

    s3_instance_for_client_us_east_1.head_bucket.assert_called_with(
        Bucket=client_us_east_1.bucket_name
    )

    # Check the specific call to create_bucket
    create_bucket_call_args = None
    for c_name, c_args, c_kwargs in s3_instance_for_client_us_east_1.method_calls:
        if (
            c_name == "create_bucket"
            and c_kwargs.get("Bucket") == client_us_east_1.bucket_name
        ):
            create_bucket_call_args = c_kwargs
            break
    assert create_bucket_call_args is not None
    assert (
        create_bucket_call_args.get("CreateBucketConfiguration") is None
    )  # No constraint for us-east-1


def test_ensure_bucket_exists_creates_new_bucket_with_region_constraint(
    client: ObjectStorageClient,
    mock_s3_client_instance: MagicMock,
    storage_client_config,
    mock_boto_s3_constructor: MagicMock,
):
    # When client_other_region = ObjectStorageClient(...) is called, it uses the mock_boto_s3_constructor.
    # The s3 client it gets is mock_boto_s3_constructor.return_value.
    # So, we set side_effects on that specific instance.
    s3_client_for_other_region = mock_boto_s3_constructor.return_value
    s3_client_for_other_region.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "head_bucket"
    )
    s3_client_for_other_region.create_bucket.return_value = {}

    # Test with a client configured for a region other than us-east-1
    client_other_region_config = storage_client_config.copy()
    client_other_region_config["region_name"] = "eu-west-1"
    # This instantiation will use the mock_boto_s3_constructor and its current return_value (s3_client_for_other_region)
    client_other_region = ObjectStorageClient(**client_other_region_config)

    result = client_other_region.ensure_bucket_exists()
    assert result is True

    # Check the specific call to create_bucket on the s3 client used by client_other_region
    create_bucket_call_kwargs = None
    # Important: method_calls on s3_client_for_other_region might be cumulative if the mock instance is reused.
    # Resetting mock or being careful with assertions is key.
    # Here, we assume s3_client_for_other_region is "fresh" for this client_other_region instance.
    for c_name, c_args, c_kwargs_dict in reversed(
        s3_client_for_other_region.method_calls
    ):
        if (
            c_name == "create_bucket"
            and c_kwargs_dict.get("Bucket") == client_other_region.bucket_name
        ):
            create_bucket_call_kwargs = c_kwargs_dict
            break
    assert create_bucket_call_kwargs is not None
    assert create_bucket_call_kwargs.get("CreateBucketConfiguration") == {
        "LocationConstraint": "eu-west-1"
    }


def test_ensure_bucket_exists_creation_fails(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    mock_s3_client_instance.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "head_bucket"
    )
    mock_s3_client_instance.create_bucket.side_effect = ClientError(
        {"Error": {"Code": "BucketAlreadyExists", "Message": "Cannot create"}},
        "create_bucket",
    )
    result = client.ensure_bucket_exists()
    assert result is False


def test_ensure_bucket_exists_head_bucket_fails_non_404(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    mock_s3_client_instance.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "SomeOtherError", "Message": "Access Denied"}}, "head_bucket"
    )
    result = client.ensure_bucket_exists()
    assert result is False
    mock_s3_client_instance.create_bucket.assert_not_called()


def test_ensure_bucket_exists_unexpected_error_on_head(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    mock_s3_client_instance.head_bucket.side_effect = Exception("Network Error")
    result = client.ensure_bucket_exists()
    assert result is False


def test_ensure_bucket_exists_unexpected_error_on_create(
    client: ObjectStorageClient, mock_s3_client_instance: MagicMock
):
    mock_s3_client_instance.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "head_bucket"
    )
    mock_s3_client_instance.create_bucket.side_effect = Exception(
        "Unexpected error during creation"
    )
    result = client.ensure_bucket_exists()
    assert result is False
