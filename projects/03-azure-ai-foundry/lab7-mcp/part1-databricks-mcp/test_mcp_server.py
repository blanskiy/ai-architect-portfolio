"""
Lab 7 Part 1: Test Databricks Unity Catalog MCP Server
Tests the MCP server by connecting as a client and calling tools
"""

import os
import asyncio
import json
from pathlib import Path

# Load project-level .env
from dotenv import load_dotenv
project_root = Path(__file__).resolve().parents[4]
load_dotenv(project_root / ".env")

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_databricks_mcp():
    """Test the Databricks MCP server"""
    print("=" * 60)
    print("Testing Databricks Unity Catalog MCP Server")
    print("=" * 60)
    
    catalog = os.getenv("DATABRICKS_CATALOG", "ai_systems")
    schema = os.getenv("DATABRICKS_SCHEMA", "stihl_gold")
    
    # Path to the cloned databricks-mcp repo
    mcp_dir = Path(__file__).parent / "databricks-mcp"
    
    if not mcp_dir.exists():
        print(f"✗ Databricks MCP not found at {mcp_dir}")
        print("  Run setup_databricks_mcp.py first!")
        return
    
    print(f"\n🔌 Connecting to Databricks MCP Server...")
    print(f"   Catalog.Schema: {catalog}.{schema}")
    
    # Server parameters
    server_params = StdioServerParameters(
        command="uv",
        args=[
            "--directory", str(mcp_dir),
            "run", "unitycatalog-mcp",
            "-s", f"{catalog}.{schema}"
        ],
        env={
            **os.environ,
            "DATABRICKS_HOST": os.getenv("DATABRICKS_HOST"),
            "DATABRICKS_TOKEN": os.getenv("DATABRICKS_TOKEN"),
        }
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize
                await session.initialize()
                print("✓ MCP Server initialized!")
                
                # List available tools
                print("\n📋 Discovering tools...")
                tools_response = await session.list_tools()
                
                print(f"\n✓ Found {len(tools_response.tools)} tools:")
                for tool in tools_response.tools:
                    print(f"\n   🔧 {tool.name}")
                    print(f"      {tool.description[:80]}...")
                
                # List resources (tables exposed)
                print("\n📋 Discovering resources...")
                try:
                    resources_response = await session.list_resources()
                    print(f"\n✓ Found {len(resources_response.resources)} resources:")
                    for resource in resources_response.resources[:5]:
                        print(f"   - {resource.name}")
                except Exception as e:
                    print(f"   (Resources not available: {e})")
                
                # Try calling a tool if available
                if tools_response.tools:
                    print("\n🧪 Testing first available tool...")
                    first_tool = tools_response.tools[0]
                    print(f"   Calling: {first_tool.name}")
                    
                    try:
                        result = await session.call_tool(first_tool.name, {})
                        print(f"   ✓ Tool executed successfully!")
                        if result.content:
                            content = result.content[0].text[:200]
                            print(f"   Response preview: {content}...")
                    except Exception as e:
                        print(f"   Tool call failed: {e}")
                
                print("\n" + "=" * 60)
                print("✅ Databricks MCP Server Test Complete!")
                print("=" * 60)
                
    except Exception as e:
        print(f"\n✗ MCP Server connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure 'uv' is installed and in PATH")
        print("2. Run setup_databricks_mcp.py first")
        print("3. Check DATABRICKS_HOST and DATABRICKS_TOKEN in .env")


if __name__ == "__main__":
    asyncio.run(test_databricks_mcp())