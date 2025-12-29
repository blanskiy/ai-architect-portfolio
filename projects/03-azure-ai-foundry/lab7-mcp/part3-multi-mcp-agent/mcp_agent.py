"""
Lab 7 Part 3: Azure OpenAI Agent with MCP Tool Integration
Demonstrates MCP pattern: tool discovery + standardized execution
"""

import os
import json
import asyncio
import sys
from pathlib import Path

# Load project-level .env
from dotenv import load_dotenv
project_root = Path(__file__).resolve().parents[4]
load_dotenv(project_root / ".env")

# Add part2 to path for MCP tools
sys.path.insert(0, str(Path(__file__).parent.parent / "part2-custom-mcp-server"))

from openai import AzureOpenAI
from stihl_mcp_server import list_tools, call_tool, MCP_TOOLS

# Configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
MODEL_DEPLOYMENT = "gpt-4o"


class MCPAgent:
    """
    Azure OpenAI Agent using MCP (Model Context Protocol) pattern.
    
    MCP Concepts Demonstrated:
    1. Tool Discovery - list_tools() returns available tools dynamically
    2. Standardized Schema - Tools have consistent parameter definitions
    3. Tool Execution - call_tool(name, args) executes any registered tool
    """
    
    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version="2024-10-21"
        )
        
        # MCP Tool Discovery - get available tools dynamically
        self.mcp_tools = list_tools()
        
        # Convert MCP tools to OpenAI function format
        self.openai_tools = self._convert_mcp_to_openai_format()
        
        print(f"🔧 MCP Agent initialized with {len(self.mcp_tools)} tools:")
        for tool in self.mcp_tools:
            print(f"   - {tool['name']}")
    
    def _convert_mcp_to_openai_format(self) -> list:
        """
        Convert MCP tool definitions to OpenAI function calling format.
        This is the 'protocol bridge' between MCP and OpenAI.
        """
        openai_tools = []
        
        for tool in self.mcp_tools:
            # Build properties from MCP parameters
            properties = {}
            for param_name, param_info in tool["parameters"].items():
                properties[param_name] = {
                    "type": param_info["type"],
                    "description": param_info["description"]
                }
            
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": []
                    }
                }
            })
        
        return openai_tools
    
    async def execute_mcp_tool(self, tool_name: str, arguments: dict) -> str:
        """
        Execute an MCP tool using the standardized call_tool interface.
        This demonstrates MCP's 'execute once, works for any tool' pattern.
        """
        print(f"  📊 MCP Tool Call: {tool_name}({json.dumps(arguments)})")
        
        # MCP standardized execution
        result = await call_tool(tool_name, arguments)
        
        return json.dumps(result, indent=2, default=str)
    
    async def chat(self, user_message: str, conversation_history: list = None) -> str:
        """Run the agent with MCP tool access"""
        
        system_prompt = """You are the STIHL Sales Analytics Agent powered by MCP (Model Context Protocol).

## AVAILABLE TOOLS (use ONLY these):

1. **query_monthly_trends**
   - Returns: year_month, category, total_units_sold, total_revenue, total_margin, margin_pct, mom_growth_pct, yoy_growth_pct
   - Filters: year, quarter, category
   - CANNOT: break down by region or product

2. **query_product_performance**
   - Returns: product_name, category, subcategory, power_type, user_segment, current_msrp, last_12_months_revenue, yoy_growth_pct, performance_tier, recommendation
   - Filters: category, performance_tier (Star/Cash Cow/Question Mark/Dog), top_n
   - CANNOT: filter by region or time period

3. **query_sales_transactions**
   - Returns: summary stats (total_transactions, total_units, total_revenue, total_margin) + regional breakdown
   - Filters: start_date, end_date, region, channel
   - CANNOT: break down by product or category

4. **get_sales_summary**
   - Returns: overall totals + top 5 categories by revenue
   - No filters
   - CANNOT: filter by region or time

## STRICT RULES:
- ONLY offer analysis that your tools can actually provide
- If asked for data you cannot retrieve, say "That breakdown is not available in my current tools" 
- DO NOT promise "deeper dives" or "granular breakdowns" unless a tool supports it
- DO NOT hallucinate data or make up numbers
- Be honest about tool limitations

## RESPONSE FORMAT:
- Provide specific numbers: $X,XXX.XX and X.X%
- Highlight key insights from ACTUAL data returned
- If a query returns empty results, say so clearly

You help sales managers make data-driven decisions with REAL data only."""

        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": user_message})
        
        print(f"\n🤖 Processing: '{user_message}'")
        
        # Call OpenAI with MCP-derived tools
        response = self.client.chat.completions.create(
            model=MODEL_DEPLOYMENT,
            messages=messages,
            tools=self.openai_tools,
            tool_choice="auto",
            max_tokens=2000
        )
        
        assistant_message = response.choices[0].message
        
        # Handle tool calls (MCP execution loop)
        iteration = 0
        max_iterations = 5
        
        while assistant_message.tool_calls and iteration < max_iterations:
            iteration += 1
            print(f"\n  🔧 MCP tool calls (iteration {iteration})")
            
            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })
            
            # Execute each MCP tool
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                # MCP standardized execution
                result = await self.execute_mcp_tool(tool_name, tool_args)
                
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "content": result
                })
            
            # Get next response
            response = self.client.chat.completions.create(
                model=MODEL_DEPLOYMENT,
                messages=messages,
                tools=self.openai_tools,
                tool_choice="auto",
                max_tokens=2000
            )
            
            assistant_message = response.choices[0].message
        
        print(f"\n✅ Response ready")
        return assistant_message.content


async def main():
    """Interactive MCP Agent chat"""
    print("=" * 60)
    print("🔧 STIHL Sales Analytics Agent (MCP-Powered)")
    print("=" * 60)
    print("This agent uses Model Context Protocol for tool integration.")
    print("Type 'quit' to exit, 'clear' to reset conversation.\n")
    
    agent = MCPAgent()
    conversation_history = []
    
    print("\n" + "-" * 60)
    print("Ready! Ask questions about STIHL sales data.")
    print("-" * 60 + "\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            if user_input.lower() == 'quit':
                print("Goodbye!")
                break
            if user_input.lower() == 'clear':
                conversation_history = []
                print("Conversation cleared.\n")
                continue
            
            response = await agent.chat(user_input, conversation_history)
            
            conversation_history.append({"role": "user", "content": user_input})
            conversation_history.append({"role": "assistant", "content": response})
            
            print(f"\nAgent: {response}\n")
            print("-" * 60)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    asyncio.run(main())