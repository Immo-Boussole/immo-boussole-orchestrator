"""Allow running the MCP server standalone: python -m app.mcp_server"""
import uvicorn
from app.config import get_settings
from app.mcp_server import create_mcp_app

if __name__ == "__main__":
    settings = get_settings()
    mcp_app = create_mcp_app()
    uvicorn.run(mcp_app, host="0.0.0.0", port=settings.mcp_port)
