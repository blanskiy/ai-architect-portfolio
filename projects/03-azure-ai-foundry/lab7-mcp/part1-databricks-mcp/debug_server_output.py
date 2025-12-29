"""Capture MCP server stderr to see why it crashes"""

import os
import subprocess
import time
from pathlib import Path

# Load project-level .env
from dotenv import load_dotenv
project_root = Path(__file__).resolve().parents[4]
load_dotenv(project_root / ".env")


def capture_server_output():
    """Run the MCP server and capture its output"""
    print("=" * 60)
    print("Debug: Capturing MCP Server Output")
    print("=" * 60)
    
    catalog = os.getenv("DATABRICKS_CATALOG", "ai_systems")
    schema = os.getenv("DATABRICKS_SCHEMA", "stihl_gold")
    mcp_dir = Path(__file__).parent / "databricks-mcp"
    
    env = os.environ.copy()
    env["DATABRICKS_HOST"] = os.getenv("DATABRICKS_HOST")
    env["DATABRICKS_TOKEN"] = os.getenv("DATABRICKS_TOKEN")
    
    cmd = [
        "uv", "--directory", str(mcp_dir),
        "run", "unitycatalog-mcp",
        "-s", f"{catalog}.{schema}"
    ]
    
    print(f"\nCommand: {' '.join(cmd)}")
    print(f"\nDATABRICKS_HOST: {env.get('DATABRICKS_HOST')}")
    print(f"DATABRICKS_TOKEN: {env.get('DATABRICKS_TOKEN')[:20]}...")
    print(f"\nRunning server (10 sec timeout)...\n")
    print("-" * 60)
    
    try:
        # Run and capture both stdout and stderr
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True
        )
        
        # Wait a bit for server to start/crash
        time.sleep(3)
        
        # Check if process is still running
        poll = process.poll()
        
        if poll is not None:
            # Process ended - likely crashed
            print(f"Server exited with code: {poll}\n")
            stdout, stderr = process.communicate()
            
            if stdout:
                print("STDOUT:")
                print(stdout)
            if stderr:
                print("\nSTDERR:")
                print(stderr)
        else:
            # Process still running - good, but let's see any early output
            print("Server is running (no crash)...")
            process.terminate()
            stdout, stderr = process.communicate(timeout=2)
            
            if stderr:
                print("\nSTDERR (startup messages):")
                print(stderr)
                
    except Exception as e:
        print(f"Error: {e}")
    
    print("-" * 60)


if __name__ == "__main__":
    capture_server_output()