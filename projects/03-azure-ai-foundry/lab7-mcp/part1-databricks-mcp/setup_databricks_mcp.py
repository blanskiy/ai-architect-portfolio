"""
Lab 7 Part 1: Setup and Test Databricks Unity Catalog MCP Server
"""

import os
import subprocess
import sys
from pathlib import Path

# Load project-level .env
from dotenv import load_dotenv
project_root = Path(__file__).resolve().parents[4]
load_dotenv(project_root / ".env")


def check_prerequisites():
    """Check if required tools are installed"""
    print("=" * 60)
    print("Lab 7 Part 1: Databricks MCP Server Setup")
    print("=" * 60)
    
    # Check uv
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        print(f"✓ uv installed: {result.stdout.strip()}")
    except FileNotFoundError:
        print("✗ uv not found. Install with: irm https://astral.sh/uv/install.ps1 | iex")
        return False
    
    # Check environment variables
    required_vars = ["DATABRICKS_HOST", "DATABRICKS_TOKEN", "DATABRICKS_CATALOG"]
    missing = [v for v in required_vars if not os.getenv(v)]
    
    if missing:
        print(f"✗ Missing environment variables: {missing}")
        return False
    
    print("✓ Environment variables configured")
    print(f"  DATABRICKS_HOST: {os.getenv('DATABRICKS_HOST')}")
    print(f"  DATABRICKS_CATALOG: {os.getenv('DATABRICKS_CATALOG')}")
    return True


def clone_databricks_mcp():
    """Clone the official Databricks MCP repository"""
    print("\n" + "-" * 60)
    print("Step 1: Clone Databricks MCP Repository")
    print("-" * 60)
    
    if os.path.exists("databricks-mcp"):
        print("✓ Repository already exists")
        return True
    
    try:
        subprocess.run([
            "git", "clone", 
            "https://github.com/databrickslabs/mcp.git",
            "databricks-mcp"
        ], check=True)
        print("✓ Cloned databrickslabs/mcp repository")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to clone: {e}")
        return False


def install_dependencies():
    """Install MCP server dependencies"""
    print("\n" + "-" * 60)
    print("Step 2: Install Dependencies")
    print("-" * 60)
    
    os.chdir("databricks-mcp")
    
    try:
        # Create virtual environment and install
        subprocess.run(["uv", "venv"], check=True)
        subprocess.run(["uv", "pip", "install", "-e", "."], check=True)
        print("✓ Dependencies installed")
        os.chdir("..")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Installation failed: {e}")
        os.chdir("..")
        return False


def generate_mcp_config():
    """Generate MCP client configuration"""
    print("\n" + "-" * 60)
    print("Step 3: Generate MCP Configuration")
    print("-" * 60)
    
    catalog = os.getenv("DATABRICKS_CATALOG")
    schema = os.getenv("DATABRICKS_SCHEMA", "stihl_gold")
    host = os.getenv("DATABRICKS_HOST")
    token = os.getenv("DATABRICKS_TOKEN")
    
    # Configuration for Claude Desktop / VS Code
    config = {
        "mcpServers": {
            "databricks_unity_catalog": {
                "command": "uv",
                "args": [
                    "--directory", 
                    str(Path.cwd() / "databricks-mcp"),
                    "run",
                    "unitycatalog-mcp",
                    "-s", f"{catalog}.{schema}"
                ],
                "env": {
                    "DATABRICKS_HOST": host,
                    "DATABRICKS_TOKEN": token
                }
            }
        }
    }
    
    import json
    with open("mcp_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print("✓ Configuration saved to mcp_config.json")
    print(f"\nTo use with Claude Desktop, add this to your config:")
    print(json.dumps(config, indent=2))
    
    return True


def test_databricks_connection():
    """Test direct Databricks connection (not via MCP yet)"""
    print("\n" + "-" * 60)
    print("Step 4: Test Databricks Connection")
    print("-" * 60)
    
    try:
        from databricks import sql as databricks_sql
        
        conn = databricks_sql.connect(
            server_hostname=os.getenv("DATABRICKS_HOST"),
            http_path=os.getenv("DATABRICKS_HTTP_PATH"),
            access_token=os.getenv("DATABRICKS_TOKEN"),
            catalog=os.getenv("DATABRICKS_CATALOG")
        )
        
        cursor = conn.cursor()
        
        # List tables in the schema
        catalog = os.getenv("DATABRICKS_CATALOG")
        schema = os.getenv("DATABRICKS_SCHEMA", "stihl_gold")
        
        cursor.execute(f"SHOW TABLES IN {catalog}.{schema}")
        tables = cursor.fetchall()
        
        print(f"✓ Connected to Databricks!")
        print(f"\nTables in {catalog}.{schema}:")
        for table in tables:
            print(f"  - {table[1]}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def print_next_steps():
    """Print instructions for next steps"""
    print("\n" + "=" * 60)
    print("Part 1 Setup Complete!")
    print("=" * 60)
    
    print("""
Next Steps:

1. TEST WITH MCP INSPECTOR (optional):
   cd databricks-mcp
   npx @modelcontextprotocol/inspector uv run unitycatalog-mcp -s ai_systems.stihl_gold

2. USE WITH CLAUDE DESKTOP:
   - Copy mcp_config.json content to Claude Desktop config
   - Location: %APPDATA%\\Claude\\claude_desktop_config.json

3. CONTINUE TO PART 2:
   - Build custom STIHL MCP server
   - cd ..\\part2-custom-mcp-server
   - python test_mcp_server.py
""")


if __name__ == "__main__":
    if not check_prerequisites():
        sys.exit(1)
    
    if not clone_databricks_mcp():
        sys.exit(1)
    
    if not install_dependencies():
        sys.exit(1)
    
    if not test_databricks_connection():
        sys.exit(1)
    
    generate_mcp_config()
    print_next_steps()