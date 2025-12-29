# Lab 7: MCP (Model Context Protocol) Integration

## Overview
Implemented Model Context Protocol pattern for standardized tool integration between Azure AI agents and Databricks data.

## Architecture
```
┌─────────────────────────────────────────────────────────────┐
│              Azure OpenAI Agent (MCP Client)                 │
│                                                              │
│   1. Tool Discovery: list_tools()                           │
│   2. Schema Conversion: MCP → OpenAI function format        │
│   3. Unified Execution: call_tool(name, args)               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    MCP Tool Registry                         │
│                                                              │
│   ┌─────────────────┐  ┌─────────────────────────────────┐  │
│   │ Tool Metadata   │  │ Tool Implementations            │  │
│   │ - name          │  │ - query_monthly_trends()        │  │
│   │ - description   │  │ - query_product_performance()   │  │
│   │ - parameters    │  │ - query_sales_transactions()    │  │
│   └─────────────────┘  │ - get_sales_summary()           │  │
│                        └─────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Databricks Lakehouse                            │
│              ai_systems.stihl_gold / stihl_silver           │
└─────────────────────────────────────────────────────────────┘
```

## Parts Completed

### Part 1: Databricks MCP Server Setup
- Cloned official `databrickslabs/mcp` repository
- Tested Databricks connection via Unity Catalog
- Generated MCP configuration for Claude Desktop/VS Code
- **Note**: stdio transport has Windows compatibility issues

### Part 2: Custom STIHL MCP Server ✅
- Built custom MCP server exposing 4 tools:
  - `query_monthly_trends` - Time-based analysis
  - `query_product_performance` - BCG matrix analysis
  - `query_sales_transactions` - Regional breakdown
  - `get_sales_summary` - Executive overview
- Standardized tool registry with discovery (`list_tools()`)
- Unified execution interface (`call_tool()`)

### Part 3: Azure OpenAI + MCP Agent ✅
- Integrated MCP tools with Azure OpenAI GPT-4o
- Dynamic tool discovery and schema conversion
- Multi-turn conversation with tool chaining
- **Key fix**: Explicit tool limitations to prevent hallucination

## MCP Concepts Demonstrated

| Concept | Implementation |
|---------|----------------|
| Tool Discovery | `list_tools()` returns available tools dynamically |
| Standardized Schema | Consistent parameter definitions across tools |
| Protocol Bridge | MCP → OpenAI function format conversion |
| Unified Execution | `call_tool(name, args)` executes any tool |
| Capability Boundaries | System prompt defines what tools CAN and CANNOT do |

## Key Learning: Preventing Hallucination

Initial implementation had the agent offering "deeper dives" and "granular breakdowns" that tools couldn't provide. Fixed by:
```python
# Each tool now has explicit CANNOT section:
2. **query_product_performance**
   - Returns: product_name, category, performance_tier...
   - Filters: category, performance_tier, top_n
   - CANNOT: filter by region or time period  # ← Prevents hallucination
```

## Sample Interactions

**Working query:**
```
You: Which products are Stars?
Agent: [calls query_product_performance(performance_tier="Star")]
       Here are 10 Star products...
```

**Graceful limitation:**
```
You: Break down Star products by region
Agent: That breakdown is not available in my current tools.
       I cannot analyze Star products based on regional data.
```

## Files
```
lab7-mcp/
├── part1-databricks-mcp/
│   ├── setup_databricks_mcp.py    # Official MCP server setup
│   ├── test_mcp_server.py         # MCP protocol test
│   └── databricks-mcp/            # Cloned repo
├── part2-custom-mcp-server/
│   ├── stihl_mcp_server.py        # Custom MCP tool implementations
│   └── test_mcp_tools.py          # Direct tool testing
├── part3-multi-mcp-agent/
│   └── mcp_agent.py               # Azure OpenAI + MCP integration
└── README.md
```

## Interview Talking Points

### MCP Value Proposition
> "MCP is becoming the 'USB-C for AI integrations' - you define tools once with standardized schemas, and any MCP-compatible client can discover and use them. Microsoft, Google, and AWS are all adopting it."

### Custom vs Official MCP Servers
> "I explored both: the official Databricks MCP server for Unity Catalog, and built a custom MCP server for business-specific analytics. Custom servers give you precise control over tool capabilities and error handling."

### Hallucination Prevention
> "I discovered the agent was offering capabilities the tools couldn't provide. I fixed this by adding explicit CANNOT sections to each tool description in the system prompt. This is critical for production agents - LLMs will confidently promise things they can't deliver."

### Production Architecture
> "For production, MCP servers should run in Databricks Apps or Azure Container Apps - close to the data source to minimize credential exposure and latency. Local development lets you iterate quickly before deploying."

## Tech Stack
- Azure OpenAI (GPT-4o)
- MCP SDK (Model Context Protocol)
- Databricks SQL Connector
- Python async/await