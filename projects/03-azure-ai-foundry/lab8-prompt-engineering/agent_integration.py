"""
Lab 8: Prompt Engineering - Agent Integration
Wraps Lab 6 STIHL Sales Agent for prompt engineering experiments.

UPDATED: December 29, 2025 - Fixed schema to match actual Databricks tables

Actual Schema:
- product_performance: last_90_days_revenue, last_90_days_units, yoy_growth_pct, overall_revenue_rank
- monthly_trends: year_month, total_revenue, total_units_sold, category
"""

import json
from typing import Optional
from dataclasses import dataclass
from openai import AzureOpenAI

from config import azure_config, databricks_config, TEST_SCENARIOS

# Attempt to import Databricks connector
try:
    from databricks import sql as databricks_sql
    DATABRICKS_AVAILABLE = True
except ImportError:
    DATABRICKS_AVAILABLE = False
    print("⚠️  databricks-sql-connector not installed. Install with: pip install databricks-sql-connector")


@dataclass
class AgentResponse:
    """Captures agent response with metadata for evaluation."""
    query: str
    response: str
    context: str  # Retrieved data used for response
    tool_calls: list[dict]  # Record of function calls made
    prompt_variant: str
    system_prompt: str
    tokens_used: int


class DatabricksConnector:
    """Handles Databricks SQL queries for the agent."""
    
    def __init__(self):
        if not DATABRICKS_AVAILABLE:
            raise ImportError("databricks-sql-connector required")
        self.config = databricks_config
        self._connection = None
    
    def _get_connection(self):
        """Get or create Databricks connection."""
        if self._connection is None:
            self._connection = databricks_sql.connect(
                server_hostname=self.config.host,
                http_path=self.config.http_path,
                access_token=self.config.token
            )
        return self._connection
    
    def execute_query(self, query: str) -> list[dict]:
        """Execute SQL query and return results as list of dicts."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        finally:
            cursor.close()
    
    def close(self):
        """Close the connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


# =============================================================================
# TOOL DEFINITIONS - UPDATED TO MATCH ACTUAL SCHEMA
# =============================================================================

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_monthly_trends",
            "description": """Query monthly sales trends from ai_systems.stihl_gold.monthly_trends.

AVAILABLE COLUMNS:
- year_month (string): Month in YYYY-MM format
- category (string): Product category
- total_revenue (double): Total revenue for the month
- total_units_sold (bigint): Units sold
- total_margin (double): Gross margin
- margin_pct (double): Margin percentage
- mom_growth_pct (double): Month-over-month growth
- yoy_growth_pct (double): Year-over-year growth
- top_product_name (string): Best selling product that month

USE FOR: Trend analysis, seasonality, month-over-month comparisons, category performance over time.

CANNOT: Access daily data, individual transactions, or customer details.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "months_back": {
                        "type": "integer",
                        "description": "Number of months of history to retrieve (default 6, max 24)"
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by category (e.g., 'Chainsaws', 'Blowers', 'Trimmers')"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_product_performance",
            "description": """Query product performance from ai_systems.stihl_gold.product_performance.

AVAILABLE COLUMNS:
- product_name (string): Product name
- category (string): Product category  
- subcategory (string): Product subcategory
- power_type (string): Power source type
- last_30_days_revenue (double): Revenue in last 30 days
- last_30_days_units (bigint): Units sold in last 30 days
- last_90_days_revenue (double): Revenue in last quarter (90 days)
- last_90_days_units (bigint): Units sold in last quarter
- last_12_months_revenue (double): Annual revenue
- yoy_growth_pct (double): Year-over-year growth percentage
- mom_growth_pct (double): Month-over-month growth percentage
- overall_revenue_rank (int): Rank by revenue across all products
- category_revenue_rank (int): Rank within category
- performance_tier (string): Performance classification
- recommendation (string): Business recommendation

USE FOR: Product rankings, top performers, category comparisons, growth analysis.

CANNOT: Access pricing history, inventory movements, or supplier information.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by product category (e.g., 'Chainsaws', 'Blowers', 'Trimmers')"
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Number of top products to return (default 10)"
                    },
                    "time_period": {
                        "type": "string",
                        "enum": ["30_days", "90_days", "12_months"],
                        "description": "Time period for revenue/units (default: 90_days for quarterly)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_sales_data",
            "description": """Query detailed sales from ai_systems.stihl_silver.fact_sales.

AVAILABLE COLUMNS:
- sale_date (date): Date of sale
- product_id (string): Product identifier
- product_name (string): Product name (if joined)
- category (string): Product category
- region (string): Sales region
- channel (string): Sales channel (Retail, Dealer, etc.)
- revenue (double): Sale revenue
- units_sold (int): Units in transaction
- gross_margin (double): Margin on sale

USE FOR: Regional analysis, channel analysis, date-range queries, detailed breakdowns.

CANNOT: Access customer PII, payment details, or return information.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_back": {
                        "type": "integer",
                        "description": "Number of days of history (default 30, max 365)"
                    },
                    "region": {
                        "type": "string",
                        "description": "Filter by region"
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by product category"
                    },
                    "aggregation": {
                        "type": "string",
                        "enum": ["daily", "weekly", "monthly", "none"],
                        "description": "Time aggregation level"
                    }
                },
                "required": []
            }
        }
    }
]


class STIHLSalesAgent:
    """
    STIHL Sales Analytics Agent with customizable prompts.
    Integrates with Databricks via function calling.
    """
    
    BASELINE_SYSTEM_PROMPT = """You are a sales analytics assistant for STIHL. 
Answer questions about sales data using the available tools.
Be helpful and accurate. If a query fails, explain the issue honestly."""

    def __init__(self, system_prompt: Optional[str] = None):
        self.client = AzureOpenAI(
            azure_endpoint=azure_config.endpoint,
            api_key=azure_config.api_key,
            api_version=azure_config.api_version
        )
        self.model = azure_config.deployment_name
        self.system_prompt = system_prompt or self.BASELINE_SYSTEM_PROMPT
        self.db = DatabricksConnector() if DATABRICKS_AVAILABLE else None
        self.tool_calls_log = []
    
    def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        """Execute a tool and return results as string."""
        
        if not self.db:
            return json.dumps({"error": "Databricks not connected"})
        
        catalog = databricks_config.catalog
        schema = databricks_config.schema
        
        try:
            if tool_name == "query_monthly_trends":
                months = arguments.get("months_back", 6)
                category_filter = ""
                if arguments.get("category"):
                    category_filter = f"AND category = '{arguments['category']}'"
                
                query = f"""
                    SELECT 
                        year_month,
                        category,
                        total_revenue,
                        total_units_sold,
                        total_margin,
                        margin_pct,
                        mom_growth_pct,
                        yoy_growth_pct,
                        top_product_name
                    FROM {catalog}.{schema}.monthly_trends
                    WHERE year_month >= DATE_FORMAT(ADD_MONTHS(CURRENT_DATE(), -{months}), 'yyyy-MM')
                    {category_filter}
                    ORDER BY year_month DESC, total_revenue DESC
                    LIMIT 50
                """
            
            elif tool_name == "query_product_performance":
                category_filter = ""
                if arguments.get("category"):
                    category_filter = f"WHERE category = '{arguments['category']}'"
                
                top_n = arguments.get("top_n", 10)
                time_period = arguments.get("time_period", "90_days")
                
                # Select appropriate revenue column based on time period
                revenue_col = {
                    "30_days": "last_30_days_revenue",
                    "90_days": "last_90_days_revenue",
                    "12_months": "last_12_months_revenue"
                }.get(time_period, "last_90_days_revenue")
                
                units_col = revenue_col.replace("revenue", "units")
                
                query = f"""
                    SELECT 
                        product_name,
                        category,
                        subcategory,
                        power_type,
                        {revenue_col} as revenue,
                        {units_col} as units_sold,
                        yoy_growth_pct,
                        mom_growth_pct,
                        overall_revenue_rank,
                        category_revenue_rank,
                        performance_tier,
                        recommendation
                    FROM {catalog}.{schema}.product_performance
                    {category_filter}
                    ORDER BY {revenue_col} DESC
                    LIMIT {top_n}
                """
            
            elif tool_name == "query_sales_data":
                days = arguments.get("days_back", 30)
                conditions = [f"sale_date >= DATE_ADD(CURRENT_DATE(), -{days})"]
                
                if arguments.get("region"):
                    conditions.append(f"region = '{arguments['region']}'")
                if arguments.get("category"):
                    conditions.append(f"category = '{arguments['category']}'")
                
                where_clause = " AND ".join(conditions)
                
                aggregation = arguments.get("aggregation", "none")
                if aggregation == "none":
                    query = f"""
                        SELECT 
                            sale_date,
                            product_id,
                            category,
                            region,
                            channel,
                            revenue,
                            units_sold,
                            gross_margin
                        FROM {catalog}.stihl_silver.fact_sales
                        WHERE {where_clause}
                        ORDER BY sale_date DESC
                        LIMIT 100
                    """
                else:
                    time_col = {
                        "daily": "sale_date",
                        "weekly": "DATE_TRUNC('week', sale_date)",
                        "monthly": "DATE_TRUNC('month', sale_date)"
                    }.get(aggregation, "sale_date")
                    
                    query = f"""
                        SELECT 
                            {time_col} as period,
                            SUM(revenue) as total_revenue,
                            SUM(units_sold) as total_units,
                            SUM(gross_margin) as total_margin,
                            COUNT(*) as transaction_count
                        FROM {catalog}.stihl_silver.fact_sales
                        WHERE {where_clause}
                        GROUP BY {time_col}
                        ORDER BY period DESC
                    """
            else:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})
            
            results = self.db.execute_query(query)
            return json.dumps(results, default=str)
            
        except Exception as e:
            return json.dumps({"error": str(e), "query": query if 'query' in locals() else "N/A"})
    
    def run(self, user_query: str, prompt_variant: str = "baseline") -> AgentResponse:
        """
        Run the agent with a user query.
        """
        self.tool_calls_log = []
        all_context = []
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_query}
        ]
        
        # Initial call
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=AGENT_TOOLS,
            tool_choice="auto"
        )
        
        total_tokens = response.usage.total_tokens if response.usage else 0
        
        # Process tool calls (up to 5 iterations)
        max_iterations = 5
        iteration = 0
        
        while response.choices[0].message.tool_calls and iteration < max_iterations:
            iteration += 1
            assistant_message = response.choices[0].message
            messages.append(assistant_message)
            
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                self.tool_calls_log.append({
                    "tool": tool_name,
                    "arguments": arguments
                })
                
                result = self._execute_tool(tool_name, arguments)
                all_context.append(f"[{tool_name}]: {result}")
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=AGENT_TOOLS,
                tool_choice="auto"
            )
            
            if response.usage:
                total_tokens += response.usage.total_tokens
        
        final_response = response.choices[0].message.content or ""
        
        return AgentResponse(
            query=user_query,
            response=final_response,
            context="\n\n".join(all_context),
            tool_calls=self.tool_calls_log,
            prompt_variant=prompt_variant,
            system_prompt=self.system_prompt,
            tokens_used=total_tokens
        )
    
    def close(self):
        """Clean up resources."""
        if self.db:
            self.db.close()


def run_baseline_test():
    """Run a quick baseline test to verify agent functionality."""
    from config import validate_config
    
    print("🔧 Testing STIHL Sales Agent (Updated Schema)")
    print("="*50)
    
    if not validate_config():
        print("\n⚠️  Fix configuration before testing")
        return None
    
    if not DATABRICKS_AVAILABLE:
        print("\n⚠️  Install databricks-sql-connector to test agent")
        return None
    
    agent = STIHLSalesAgent()
    
    try:
        scenario = TEST_SCENARIOS[0]
        print(f"\nQuery: {scenario['query']}")
        
        result = agent.run(scenario['query'], "baseline_test")
        
        print(f"\n📝 Response:\n{result.response}")
        print(f"\n🔧 Tool calls: {len(result.tool_calls)}")
        for tc in result.tool_calls:
            print(f"   - {tc['tool']}: {tc['arguments']}")
        print(f"\n💰 Tokens: {result.tokens_used}")
        
        return result
        
    finally:
        agent.close()


if __name__ == "__main__":
    run_baseline_test()
