"""MinIO sync client for worker tasks."""

from functools import lru_cache

from minio import Minio

from astoka_worker.config import get_worker_settings


@lru_cache(maxsize=1)
def get_minio_client() -> Minio:
    s = get_worker_settings()
    return Minio(
        s.minio_endpoint,
        access_key=s.minio_root_user,
        secret_key=s.minio_root_password,
        secure=s.minio_secure,
    )


def upload_file(local_path: str, storage_key: str) -> None:
    s = get_worker_settings()
    client = get_minio_client()
    client.fput_object(s.minio_bucket, storage_key, local_path)


def download_file(storage_key: str, local_path: str) -> None:
    s = get_worker_settings()
    client = get_minio_client()
    client.fget_object(s.minio_bucket, storage_key, local_path)


def stat_object(storage_key: str) -> int:
    """Returns size in bytes; raises if missing."""
    s = get_worker_settings()
    client = get_minio_client()
    info = client.stat_object(s.minio_bucket, storage_key)
    return int(info.size or 0)
