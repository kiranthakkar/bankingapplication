"""OCI Object Storage MCP tool implementations.

These functions are registered with FastMCP in ``registry.py`` and are used by
both the banking agent and the banking application's statement APIs.
"""

import json
from types import SimpleNamespace

from fastmcp import Context

from app.mcp.auth import ociclients

try:
    from fastmcp.server.dependencies import get_access_token as _get_access_token  # type: ignore
except Exception:
    from fastmcp.server.dependencies import get_http_headers

    def _get_access_token():
        headers = get_http_headers()
        auth_header = headers.get("authorization") or headers.get("Authorization") or ""
        token_value = ""
        if auth_header.lower().startswith("bearer "):
            token_value = auth_header.split(" ", 1)[1].strip()
        return SimpleNamespace(token=token_value, claims={})


async def get_os_namespace(region: str, ctx: Context) -> str:
    """Return the Object Storage namespace for the authenticated OCI tenancy.

    Args:
        region: OCI region identifier such as ``us-ashburn-1``.
        ctx: FastMCP request context.
    """
    object_storage_client = ociclients.get_os_client(_get_access_token(), region)
    namespace_response = object_storage_client.get_namespace()
    return namespace_response.data


async def upload_object_file(
    region: str,
    bucket_name: str,
    object_name: str,
    file_name: str,
    ctx: Context,
) -> str:
    """Upload a local file to OCI Object Storage.

    Args:
        region: OCI region identifier such as ``us-ashburn-1``.
        bucket_name: Target Object Storage bucket name.
        object_name: Full object key to create or overwrite.
        file_name: Local filesystem path to upload.
        ctx: FastMCP request context.
    """
    object_storage_client = ociclients.get_os_client(_get_access_token(), region)
    namespace_name = object_storage_client.get_namespace().data

    with open(file_name, "rb") as file_data:
        put_object_response = object_storage_client.put_object(
            namespace_name,
            bucket_name,
            object_name,
            file_data,
        )

    if put_object_response.status == 200:
        return json.dumps(
            {
                "success": True,
                "message": f"Object '{object_name}' successfully uploaded to bucket '{bucket_name}'",
            }
        )
    return json.dumps(
        {
            "success": False,
            "message": f"Failed to upload object '{object_name}' to bucket '{bucket_name}'",
        }
    )


async def upload_object_text(
    region: str,
    bucket_name: str,
    object_name: str,
    object_content: str,
    ctx: Context,
) -> str:
    """Upload UTF-8 text content as an object into OCI Object Storage.

    Args:
        region: OCI region identifier such as ``us-ashburn-1``.
        bucket_name: Target Object Storage bucket name.
        object_name: Full object key to create or overwrite.
        object_content: Text content to persist as the object body.
        ctx: FastMCP request context.
    """
    object_storage_client = ociclients.get_os_client(_get_access_token(), region)
    namespace_name = object_storage_client.get_namespace().data

    put_object_response = object_storage_client.put_object(
        namespace_name,
        bucket_name,
        object_name,
        object_content.encode("utf-8"),
    )

    if put_object_response.status == 200:
        return json.dumps(
            {
                "success": True,
                "message": f"Object '{object_name}' successfully uploaded to bucket '{bucket_name}'",
            }
        )
    return json.dumps(
        {
            "success": False,
            "message": f"Failed to upload object '{object_name}' to bucket '{bucket_name}'",
        }
    )


async def list_objects(
    region: str,
    bucket_name: str,
    prefix: str = "",
    ctx: Context = None,
) -> str:
    """List objects in a bucket, optionally filtered by a key prefix.

    Args:
        region: OCI region identifier such as ``us-ashburn-1``.
        bucket_name: Target Object Storage bucket name.
        prefix: Optional object key prefix to filter results.
        ctx: FastMCP request context.
    """
    object_storage_client = ociclients.get_os_client(_get_access_token(), region)
    namespace_name = object_storage_client.get_namespace().data
    list_objects_response = object_storage_client.list_objects(
        namespace_name,
        bucket_name,
        prefix=prefix or None,
    )

    objects = []
    for obj in list_objects_response.data.objects or []:
        objects.append(
            {
                "name": obj.name,
                "size": int(obj.size or 0),
                "time_created": str(obj.time_created) if getattr(obj, "time_created", None) else None,
                "etag": getattr(obj, "etag", None),
            }
        )

    return json.dumps({"success": True, "Bucket": bucket_name, "Objects": objects})


async def get_object(region: str, bucket_name: str, object_name: str, ctx: Context) -> str:
    """Fetch and return a text object from OCI Object Storage.

    Args:
        region: OCI region identifier such as ``us-ashburn-1``.
        bucket_name: Target Object Storage bucket name.
        object_name: Full object key to read.
        ctx: FastMCP request context.
    """
    object_storage_client = ociclients.get_os_client(_get_access_token(), region)
    namespace_name = object_storage_client.get_namespace().data
    get_object_response = object_storage_client.get_object(namespace_name, bucket_name, object_name)
    body = getattr(get_object_response.data, "content", b"")
    if isinstance(body, bytes):
        content = body.decode("utf-8", errors="replace")
    else:
        content = str(body)
    return json.dumps(
        {
            "success": True,
            "object_name": object_name,
            "content_type": get_object_response.headers.get("content-type"),
            "content": content,
        }
    )


def delete_object(region: str, bucket_name: str, object_name: str) -> str:
    """Delete an object from a bucket.

    Args:
        region: OCI region identifier such as ``us-ashburn-1``.
        bucket_name: Target Object Storage bucket name.
        object_name: Full object key to delete.
    """
    object_storage_client = ociclients.get_os_client(_get_access_token(), region)
    namespace_name = object_storage_client.get_namespace().data
    delete_object_response = object_storage_client.delete_object(namespace_name, bucket_name, object_name)

    if delete_object_response.status in [200, 204]:
        return json.dumps(
            {
                "success": True,
                "message": f"Object '{object_name}' successfully deleted from bucket '{bucket_name}'",
            }
        )
    return json.dumps(
        {
            "success": False,
            "message": f"Failed to delete object '{object_name}'",
        }
    )
