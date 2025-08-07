import os
import sys

# mcp_server_freesearch
from .server import mcp

VERSION = "1.0.0"


def main():
    """
    Initialize and run the MCP server.
    """
    # api_url = os.environ.get('SEARXNG_API_URL')
    # if not api_url:
    #     print('SEARXNG_API_URL is not set')
    #     sys.exit(1)
    mcp.run(transport="stdio")


# 导出 server 对象，使其可以被外部访问
__all__ = ["main", "mcp"]
