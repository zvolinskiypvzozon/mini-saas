import os
from urllib.parse import quote

import boto3
from botocore.config import Config

BUCKET = os.environ.get("S3_BUCKET", "files")


def _client(endpoint: str | None):
    return boto3.client(
        "s3",
        endpoint_url=endpoint or None,
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY"),
        aws_secret_access_key=os.environ.get("S3_SECRET_KEY"),
        region_name=os.environ.get("S3_REGION", "us-east-1"),
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def s3():
    return _client(os.environ.get("S3_ENDPOINT"))


def s3_public():
    return _client(os.environ.get("S3_PUBLIC_ENDPOINT") or os.environ.get("S3_ENDPOINT"))


def ensure_bucket() -> None:
    client = s3()
    names = [b["Name"] for b in client.list_buckets().get("Buckets", [])]
    if BUCKET not in names:
        client.create_bucket(Bucket=BUCKET)


def put(key: str, data: bytes, content_type: str) -> None:
    s3().put_object(Bucket=BUCKET, Key=key, Body=data, ContentType=content_type)


def delete(key: str) -> None:
    s3().delete_object(Bucket=BUCKET, Key=key)


def presigned_get(key: str, filename: str, expires: int) -> str:
    return s3_public().generate_presigned_url(
        "get_object",
        Params={
            "Bucket": BUCKET,
            "Key": key,
            "ResponseContentDisposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        },
        ExpiresIn=expires,
    )
