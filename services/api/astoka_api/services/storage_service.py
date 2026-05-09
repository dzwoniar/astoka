"""MinIO client wrapper.

Two clients are needed because Docker container DNS (`minio:9000`) is unreachable
from the user's browser. The browser uploads/downloads via presigned URLs which
embed the endpoint hostname; those must point at a host the browser can resolve
(e.g. `localhost:9000` in dev, `minio.example.com` in prod).

- `get_minio_client()`         — internal endpoint, used for server-side ops
                                  (bucket_exists, stat_object, put_object).
- `get_public_minio_client()`  — public endpoint, used ONLY to mint presigned
                                  PUT/GET URLs that the browser will call.

Both share the same credentials + bucket. Region is hardcoded to `us-east-1`
to skip minio-py's GetBucketLocation auto-discovery (the call which causes
the 500 error reported by Janek).
"""

from datetime import timedelta
from functools import lru_cache

from minio import Minio

from astoka_api.config import get_settings


@lru_cache(maxsize=1)
def get_minio_client() -> Minio:
    """Internal client — uses `minio_endpoint` (server↔MinIO)."""
    settings = get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
        region=settings.minio_region,
    )


@lru_cache(maxsize=1)
def get_public_minio_client() -> Minio:
    """Public client — uses `minio_public_endpoint`. ONLY for presigned URLs.

    Never call put_object/stat_object on this client from inside the API container
    — it'd try to reach `localhost:9000` which is the host's loopback, not the
    container network.
    """
    settings = get_settings()
    return Minio(
        settings.minio_public_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
        region=settings.minio_region,
    )


def ensure_bucket() -> None:
    settings = get_settings()
    client = get_minio_client()
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)


def storage_key_for_source(source_material_id: str, original_filename: str | None) -> str:
    """Deterministic key: source_materials/{id}/original{ext}."""
    ext = ""
    if original_filename and "." in original_filename:
        ext = "." + original_filename.rsplit(".", 1)[-1].lower()
    return f"source_materials/{source_material_id}/original{ext}"


def storage_key_for_proxy(source_material_id: str) -> str:
    return f"source_materials/{source_material_id}/proxy_480p.mp4"


def storage_key_for_thumbnail(source_material_id: str) -> str:
    return f"source_materials/{source_material_id}/thumbnail.jpg"


def presign_upload_url(storage_key: str, ttl_minutes: int = 60) -> str:
    """Presigned PUT URL — browser uploads directly to MinIO, bypassing FastAPI."""
    settings = get_settings()
    client = get_public_minio_client()
    return client.presigned_put_object(
        settings.minio_bucket,
        storage_key,
        expires=timedelta(minutes=ttl_minutes),
    )


def presign_download_url(storage_key: str, ttl_minutes: int = 60) -> str:
    settings = get_settings()
    client = get_public_minio_client()
    return client.presigned_get_object(
        settings.minio_bucket,
        storage_key,
        expires=timedelta(minutes=ttl_minutes),
    )


def object_exists(storage_key: str) -> bool:
    settings = get_settings()
    client = get_minio_client()
    try:
        client.stat_object(settings.minio_bucket, storage_key)
        return True
    except Exception:
        return False
