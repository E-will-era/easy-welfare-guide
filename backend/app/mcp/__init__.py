"""
MCP (Model Context Protocol) External Search Module

Description: Provides MCP-based external search capabilities for Korean government
    welfare portals. Exposes a unified client for querying 정부24, 복지로, and
    other public welfare information portals to supplement and verify RAG results.

Exports:
    MCPSearchClient  - Main async search client class
    SearchResult     - Dataclass representing a single search result
    get_mcp_client   - Factory function returning the singleton client instance
"""

from app.mcp.search_client import MCPSearchClient, SearchResult, get_mcp_client

__all__ = [
    "MCPSearchClient",
    "SearchResult",
    "get_mcp_client",
]
