"""Debug script to find the actual MCP error"""

import os
import subprocess
import sys
from pathlib import Path

# Load project-level .env
from dotenv import load_dotenv
project_root = Path(__file__).resolve().parents[4]
load_dotenv(project_root / ".env")

def test_uv_command():
    """Test if we can run the MCP server directly"""
    print("=" * 60)
    print("Debug: Testing MCP Server Launch")
    print("=" * 60)
    
    mcp_dir = Path(__file__).parent / "databricks-mcp"
    catalog = os.getenv("DATABRICKS_CATALOG", "ai_systems")
    schema = os.getenv("DATABRICKS_SCHEMA", "stihl_gold")
    
    print(f"\n1. MCP Directory: {mcp_dir}")
    print(f"   Exists: {mcp_dir.exists()}")
    
    # Check what entry points are available
    print(f"\n2. Checking available entry points...")
    try:
        result = subprocess.run(
            ["uv", "--directory", str(mcp_dir), "run", "--help"],
            capture_output=True,
            text=True,
            cwd=str(mcp_dir)
        )
        print(f"   uv run --help works: {result.returncode == 0}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # List what's in the databricks-mcp folder
    print(f"\n3. Contents of databricks-mcp:")
    if mcp_dir.exists():
        for item in list(mcp_dir.iterdir())[:10]:
            print(f"   - {item.name}")
    
    # Check pyproject.toml for entry points
    pyproject = mcp_dir / "pyproject.toml"
    if pyproject.exists():
        print(f"\n4. Checking pyproject.toml for scripts...")
        with open(pyproject) as f:
            content = f.read()
            if "[project.scripts]" in content:
                # Find the scripts section
                lines = content.split("\n")
                in_scripts = False
                for line in lines:
                    if "[project.scripts]" in line:
                        in_scripts = True
                    elif in_scripts:
                        if line.startswith("["):
                            break
                        if "=" in line:
                            print(f"   Found script: {line.strip()}")
    
    # Try running the server directly
    print(f"\n5. Testing server launch (will timeout after 5 sec)...")
    
    env = os.environ.copy()
    env["DATABRICKS_HOST"] = os.getenv("DATABRICKS_HOST")
    env["DATABRICKS_TOKEN"] = os.getenv("DATABRICKS_TOKEN")
    
    # Try different possible entry points
    entry_points = [
        ["uv", "--directory", str(mcp_dir), "run", "unitycatalog-mcp", "-s", f"{catalog}.{schema}"],
        ["uv", "--directory", str(mcp_dir), "run", "databricks-mcp"],
        ["uv", "--directory", str(mcp_dir), "run", "python", "-m", "databricks_mcp"],
    ]
    
    for cmd in entry_points:
        print(f"\n   Trying: {' '.join(cmd[:5])}...")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                env=env,
                cwd=str(mcp_dir)
            )
            print(f"   Return code: {result.returncode}")
            if result.stdout:
                print(f"   Stdout: {result.stdout[:200]}")
            if result.stderr:
                print(f"   Stderr: {result.stderr[:500]}")
        except subprocess.TimeoutExpired:
            print(f"   ✓ Server started (timed out waiting - this is good!)")
        except Exception as e:
            print(f"   Error: {e}")


if __name__ == "__main__":
    test_uv_command()