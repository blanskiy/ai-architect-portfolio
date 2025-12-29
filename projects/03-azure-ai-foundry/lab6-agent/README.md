# Lab 6: STIHL Sales Analytics Agent

## Overview
Built an AI agent using Azure OpenAI with function calling to query Databricks SQL Warehouse.

## Architecture
`
User Question  GPT-4o Agent  Function Calling  Databricks SQL  Synthesized Response
`

## Tools Implemented

| Function | Purpose | Databricks Table |
|----------|---------|------------------|
| query_monthly_trends | Time-based analysis | stihl_gold.monthly_trends |
| query_product_performance | Product/category analysis | stihl_gold.product_performance |
| query_sales_data | Transaction details | stihl_silver.fact_sales |

## Sample Interactions

**Q: "What were our sales trends in Q4 2024?"**
- Tool: query_monthly_trends(year=2024, quarter=4)
- Result: .2M December revenue, category breakdowns, YoY growth

**Q: "Which products are Stars?"**
- Tool: query_product_performance(performance_tier='Star')
- Result: 10 Star products identified, battery tools dominating

**Q: "How did the West region perform?"**
- Tool: query_sales_data(region='West')
- Result: .7M revenue, 38K units, 50.1% margin

## Key Features
- Multi-turn conversation with context retention
- Automatic tool selection based on question intent
- Rich markdown responses with insights and recommendations
- Error handling for Databricks connectivity

## Files
- `stihl_agent.py` - Main agent with function calling
- `debug_tables.py` - Schema inspection utility
- `.env` - Configuration (not committed)

## Tech Stack
- Azure OpenAI (GPT-4o)
- Databricks SQL Connector
- Python OpenAI SDK

## Interview Talking Point
> "I built a sales analytics agent using Azure OpenAI with function calling to Databricks. The agent understands natural language questions, selects the appropriate data tool, executes SQL queries against our lakehouse, and synthesizes insights with recommendations. It handles multi-turn conversations and can chain multiple tool calls for complex questions."
