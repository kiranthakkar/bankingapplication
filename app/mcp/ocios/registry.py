"""Tool registration helpers for the OCI Object Storage FastMCP server."""

from app.mcp.ocios import tools


def register_tools(mcp) -> None:
    """Register OCI Object Storage tools with descriptive docstrings for FastMCP."""
    mcp.tool()(tools.get_os_namespace)
    mcp.tool()(tools.upload_object_file)
    mcp.tool()(tools.upload_object_text)
    mcp.tool()(tools.list_objects)
    mcp.tool()(tools.get_object)
    mcp.tool()(tools.delete_object)


def register_resources(mcp) -> None:
    """Register MCP resources.

    The current Object Storage server exposes tools only, so this is a no-op.
    """
    return None
