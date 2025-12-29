"""Test raw MCP protocol communication"""

import os
import subprocess
import json
import time
from pathlib import Path

# Load project-level .env
from dotenv import load_dotenv
project_root = Path(__file__).resolve().parents[4]
load_dotenv(project_root / ".env")


def test_raw_mcp():
    """Send raw MCP protocol messages to server"""
    print("=" * 60)
    print("Debug: Raw MCP Protocol Test")
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
    
    print(f"Starting MCP server...")
    
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        bufsize=0
    )
    
    # MCP initialize request (JSON-RPC 2.0)
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    message = json.dumps(init_request)
    # MCP uses Content-Length header like LSP
    full_message = f"Content-Length: {len(message)}\r\n\r\n{message}"
    
    print(f"\nSending initialize request...")
    print(f"Message: {message[:100]}...")
    
    try:
        process.stdin.write(full_message)
        process.stdin.flush()
        
        print("\nWaiting for response (5 sec)...")
        time.sleep(2)
        
        # Try to read response
        import select
        import sys
        
        # On Windows, we can't use select on pipes, so just try to read
        process.stdout.flush() if hasattr(process.stdout, 'flush') else None
        
        # Check if there's any stderr output
        stderr_output = ""
        try:
            process.stderr.flush()
            # Non-blocking read attempt
            import threading
            
            def read_stderr():
                nonlocal stderr_output
                stderr_output = process.stderr.read()
            
            t = threading.Thread(target=read_stderr)
            t.daemon = True
            t.start()
            t.join(timeout=1)
        except:
            pass
        
        if stderr_output:
            print(f"\nServer STDERR:\n{stderr_output}")
        
        # Kill and get remaining output
        process.terminate()
        stdout, stderr = process.communicate(timeout=2)
        
        print(f"\nServer STDOUT:\n{stdout if stdout else '(empty)'}")
        print(f"\nServer STDERR:\n{stderr if stderr else '(empty)'}")
        
    except Exception as e:
        print(f"Error: {e}")
        process.kill()


if __name__ == "__main__":
    test_raw_mcp()