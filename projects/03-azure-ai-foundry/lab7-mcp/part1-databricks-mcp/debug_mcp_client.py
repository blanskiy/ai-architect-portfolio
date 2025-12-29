"""Simpler debug to find the actual client error"""

import os
import asyncio
import traceback
from pathlib import Path

# Load project-level .env
from dotenv import load_dotenv
project_root = Path(__file__).resolve().parents[4]
load_dotenv(project_root / ".env")


async def test_mcp_client():
    """Test MCP client with detailed error output"""
    print("=" * 60)
    print("Debug: MCP Client Connection")
    print("=" * 60)
    
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    
    catalog = os.getenv("DATABRICKS_CATALOG", "ai_systems")
    schema = os.getenv("DATABRICKS_SCHEMA", "stihl_gold")
    mcp_dir = Path(__file__).parent / "databricks-mcp"
    
    server_params = StdioServerParameters(
        command="uv",
        args=[
            "--directory", str(mcp_dir),
            "run", "unitycatalog-mcp",
            "-s", f"{catalog}.{schema}"
        ],
        env={
            "DATABRICKS_HOST": os.getenv("DATABRICKS_HOST"),
            "DATABRICKS_TOKEN": os.getenv("DATABRICKS_TOKEN"),
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),  # Windows needs this
            "USERPROFILE": os.environ.get("USERPROFILE", ""),
        }
    )
    
    print(f"\nServer command: uv --directory {mcp_dir} run unitycatalog-mcp -s {catalog}.{schema}")
    print(f"DATABRICKS_HOST: {os.getenv('DATABRICKS_HOST')}")
    
    try:
        print("\n1. Creating stdio_client...")
        async with stdio_client(server_params) as (read, write):
            print("   ✓ stdio_client created")
            
            print("\n2. Creating ClientSession...")
            async with ClientSession(read, write) as session:
                print("   ✓ ClientSession created")
                
                print("\n3. Initializing session...")
                await session.initialize()
                print("   ✓ Session initialized")
                
                print("\n4. Listing tools...")
                tools = await session.list_tools()
                print(f"   ✓ Found {len(tools.tools)} tools")
                
                for tool in tools.tools:
                    print(f"      - {tool.name}")
                    
    except Exception as e:
        print(f"\n❌ Error at some step:")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {e}")
        print(f"\n   Full traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_mcp_client())