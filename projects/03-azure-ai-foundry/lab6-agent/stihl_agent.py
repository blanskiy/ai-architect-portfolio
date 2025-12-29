"""
Lab 6: STIHL Sales Analytics Agent
Azure AI Foundry Agent with Databricks Function Calling
"""

import os
import json
from dotenv import load_dotenv
from openai import AzureOpenAI
from databricks import sql as databricks_sql

load_dotenv()

# Configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
MODEL_DEPLOYMENT = "gpt-4o"

DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_CATALOG = os.getenv("DATABRICKS_CATALOG", "ai_systems")


# =============================================================================
# DATABRICKS QUERY FUNCTIONS
# =============================================================================

def get_databricks_connection():
    """Create Databricks SQL connection"""
    return databricks_sql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN,
        catalog=DATABRICKS_CATALOG
    )


def query_monthly_trends(year: int = None, quarter: int = None, year_month: str = None) -> str:
    """
    Query monthly sales trends from stihl_gold.monthly_trends
    
    Args:
        year: Filter by year (e.g., 2024)
        quarter: Filter by quarter (1-4)
        year_month: Filter by specific month (e.g., '2024-06')
    
    Returns:
        JSON string with monthly trend data
    """
    try:
        conn = get_databricks_connection()
        cursor = conn.cursor()
        
        query = f"""
        SELECT 
            year_month,
            category,
            total_units_sold,
            total_revenue,
            total_margin,
            margin_pct,
            mom_growth_pct,
            yoy_growth_pct,
            top_product_name
        FROM {DATABRICKS_CATALOG}.stihl_gold.monthly_trends
        WHERE 1=1
        """
        
        if year_month:
            query += f" AND year_month = '{year_month}'"
        elif year:
            query += f" AND year_month LIKE '{year}%'"
            if quarter:
                # Q1: 01-03, Q2: 04-06, Q3: 07-09, Q4: 10-12
                months = {
                    1: ['01', '02', '03'],
                    2: ['04', '05', '06'],
                    3: ['07', '08', '09'],
                    4: ['10', '11', '12']
                }
                month_list = months.get(quarter, [])
                if month_list:
                    month_conditions = " OR ".join([f"year_month LIKE '%-{m}'" for m in month_list])
                    query += f" AND ({month_conditions})"
        
        query += " ORDER BY year_month DESC LIMIT 12"
        
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        results = [dict(zip(columns, row)) for row in rows]
        
        cursor.close()
        conn.close()
        
        return json.dumps(results, indent=2, default=str)
    
    except Exception as e:
        return json.dumps({"error": str(e)})


def query_product_performance(
    category: str = None, 
    performance_tier: str = None,
    top_n: int = 10
) -> str:
    """
    Query product performance from stihl_gold.product_performance
    
    Args:
        category: Filter by product category (e.g., 'Chainsaws', 'Blowers', 'Trimmers')
        performance_tier: Filter by tier ('Star', 'Cash Cow', 'Question Mark', 'Dog')
        top_n: Number of results to return (default 10)
    
    Returns:
        JSON string with product performance data
    """
    try:
        conn = get_databricks_connection()
        cursor = conn.cursor()
        
        query = f"""
        SELECT 
            product_name,
            model_number,
            category,
            subcategory,
            power_type,
            user_segment,
            current_msrp,
            current_margin_pct,
            last_12_months_units,
            last_12_months_revenue,
            yoy_growth_pct,
            mom_growth_pct,
            overall_revenue_rank,
            overall_units_rank,
            performance_tier,
            recommendation
        FROM {DATABRICKS_CATALOG}.stihl_gold.product_performance
        WHERE 1=1
        """
        
        if category:
            query += f" AND LOWER(category) LIKE LOWER('%{category}%')"
        if performance_tier:
            query += f" AND LOWER(performance_tier) LIKE LOWER('%{performance_tier}%')"
        
        query += f" ORDER BY last_12_months_revenue DESC LIMIT {top_n}"
        
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        results = [dict(zip(columns, row)) for row in rows]
        
        cursor.close()
        conn.close()
        
        return json.dumps(results, indent=2, default=str)
    
    except Exception as e:
        return json.dumps({"error": str(e)})


def query_sales_data(
    start_date: str = None,
    end_date: str = None,
    region: str = None,
    channel: str = None,
    limit: int = 100
) -> str:
    """
    Query sales transactions from stihl_silver.fact_sales
    
    Args:
        start_date: Filter by start date (YYYY-MM-DD)
        end_date: Filter by end date (YYYY-MM-DD)
        region: Filter by region (e.g., 'West', 'East', 'Central')
        channel: Filter by channel (e.g., 'Retail', 'Online')
        limit: Max rows to return (default 100)
    
    Returns:
        JSON string with sales data and summary stats
    """
    try:
        conn = get_databricks_connection()
        cursor = conn.cursor()
        
        where_clause = "WHERE 1=1"
        if start_date:
            where_clause += f" AND sale_date >= '{start_date}'"
        if end_date:
            where_clause += f" AND sale_date <= '{end_date}'"
        if region:
            where_clause += f" AND LOWER(region) LIKE LOWER('%{region}%')"
        if channel:
            where_clause += f" AND LOWER(channel) LIKE LOWER('%{channel}%')"
        
        # Get summary stats
        summary_query = f"""
        SELECT 
            COUNT(*) as total_transactions,
            SUM(units_sold) as total_units,
            SUM(revenue) as total_revenue,
            SUM(gross_margin) as total_margin,
            AVG(revenue) as avg_transaction_value,
            COUNT(DISTINCT product_id) as unique_products,
            COUNT(DISTINCT region) as regions_count
        FROM {DATABRICKS_CATALOG}.stihl_silver.fact_sales
        {where_clause}
        """
        
        cursor.execute(summary_query)
        summary_cols = [desc[0] for desc in cursor.description]
        summary_row = cursor.fetchone()
        summary = dict(zip(summary_cols, summary_row)) if summary_row else {}
        
        # Get breakdown by region
        region_query = f"""
        SELECT 
            region,
            SUM(revenue) as revenue,
            SUM(units_sold) as units,
            COUNT(*) as transactions
        FROM {DATABRICKS_CATALOG}.stihl_silver.fact_sales
        {where_clause}
        GROUP BY region
        ORDER BY revenue DESC
        """
        
        cursor.execute(region_query)
        region_cols = [desc[0] for desc in cursor.description]
        region_rows = cursor.fetchall()
        by_region = [dict(zip(region_cols, row)) for row in region_rows]
        
        # Get recent transactions sample
        detail_query = f"""
        SELECT 
            sale_date,
            product_id,
            region,
            channel,
            units_sold,
            revenue,
            gross_margin
        FROM {DATABRICKS_CATALOG}.stihl_silver.fact_sales
        {where_clause}
        ORDER BY sale_date DESC 
        LIMIT {min(limit, 10)}
        """
        
        cursor.execute(detail_query)
        detail_cols = [desc[0] for desc in cursor.description]
        detail_rows = cursor.fetchall()
        transactions = [dict(zip(detail_cols, row)) for row in detail_rows]
        
        cursor.close()
        conn.close()
        
        return json.dumps({
            "summary": summary,
            "by_region": by_region,
            "sample_transactions": transactions
        }, indent=2, default=str)
    
    except Exception as e:
        return json.dumps({"error": str(e)})


# =============================================================================
# FUNCTION DEFINITIONS FOR OPENAI
# =============================================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_monthly_trends",
            "description": "Query monthly sales trends including revenue, units sold, margins, and growth rates. Use for questions about sales over time, seasonal patterns, monthly/quarterly comparisons. Data uses year_month format like '2024-06'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "Filter by year (e.g., 2024)"
                    },
                    "quarter": {
                        "type": "integer",
                        "description": "Filter by quarter (1-4). Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec"
                    },
                    "year_month": {
                        "type": "string",
                        "description": "Filter by specific month in YYYY-MM format (e.g., '2024-06')"
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
            "description": "Query product performance metrics including revenue, units, growth rates, and strategic classification. Performance tiers are: 'Star' (high growth leaders), 'Cash Cow' (stable performers), 'Question Mark' (growth potential), 'Dog' (underperformers). Use for product analysis and strategic recommendations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product category (e.g., 'Chainsaws', 'Blowers', 'Trimmers')"
                    },
                    "performance_tier": {
                        "type": "string",
                        "description": "Strategic tier: 'Star', 'Cash Cow', 'Question Mark', or 'Dog'"
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Number of products to return (default 10)"
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
            "description": "Query detailed sales transactions with summary statistics and regional breakdowns. Use for specific time periods, regional analysis, or transaction-level details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format"
                    },
                    "region": {
                        "type": "string",
                        "description": "Region filter (e.g., 'West', 'East', 'Central')"
                    },
                    "channel": {
                        "type": "string",
                        "description": "Sales channel filter (e.g., 'Retail', 'Online')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum transactions to return (default 100)"
                    }
                },
                "required": []
            }
        }
    }
]

# Map function names to actual functions
FUNCTION_MAP = {
    "query_monthly_trends": query_monthly_trends,
    "query_product_performance": query_product_performance,
    "query_sales_data": query_sales_data
}


# =============================================================================
# AGENT LOGIC
# =============================================================================

def get_openai_client():
    """Create Azure OpenAI client"""
    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version="2024-10-21"
    )


def process_tool_calls(tool_calls) -> list:
    """Execute tool calls and return results"""
    results = []
    
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        
        print(f"  📊 Calling: {function_name}({function_args})")
        
        if function_name in FUNCTION_MAP:
            result = FUNCTION_MAP[function_name](**function_args)
        else:
            result = json.dumps({"error": f"Unknown function: {function_name}"})
        
        results.append({
            "tool_call_id": tool_call.id,
            "role": "tool",
            "content": result
        })
    
    return results


def run_agent(user_question: str, conversation_history: list = None) -> str:
    """
    Run the STIHL Sales Analytics Agent
    """
    client = get_openai_client()
    
    system_prompt = """You are the STIHL Sales Analytics Agent, an expert assistant for analyzing sales data.

You have access to three data tools connected to Databricks:
1. query_monthly_trends - For time-based analysis (monthly/quarterly trends, YoY comparisons)
   - Data uses year_month format like '2024-06'
   - Returns: revenue, units, margins, growth rates
   
2. query_product_performance - For product analysis (categories, strategic tiers)
   - Performance tiers: Star, Cash Cow, Question Mark, Dog
   - Returns: product details, rankings, recommendations
   
3. query_sales_data - For transaction details and regional analysis
   - Returns: summary stats, regional breakdown, sample transactions

Guidelines:
- Always use the appropriate tool(s) to fetch real data before answering
- Provide specific numbers and insights from the data
- Format currency as $X,XXX.XX and percentages as X.X%
- Highlight key insights and actionable recommendations
- If data is unavailable or empty, explain what's missing

You're helping sales managers and executives make data-driven decisions about STIHL outdoor power equipment."""

    messages = [{"role": "system", "content": system_prompt}]
    
    if conversation_history:
        messages.extend(conversation_history)
    
    messages.append({"role": "user", "content": user_question})
    
    print(f"\n🤖 Agent processing: '{user_question}'")
    
    # First API call
    response = client.chat.completions.create(
        model=MODEL_DEPLOYMENT,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        max_tokens=2000
    )
    
    assistant_message = response.choices[0].message
    
    # Handle tool calls
    iteration = 0
    max_iterations = 5
    
    while assistant_message.tool_calls and iteration < max_iterations:
        iteration += 1
        print(f"\n  🔧 Tool calls detected (iteration {iteration})")
        
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
        
        tool_results = process_tool_calls(assistant_message.tool_calls)
        messages.extend(tool_results)
        
        response = client.chat.completions.create(
            model=MODEL_DEPLOYMENT,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=2000
        )
        
        assistant_message = response.choices[0].message
    
    print(f"\n✅ Agent response ready")
    return assistant_message.content


# =============================================================================
# INTERACTIVE CHAT
# =============================================================================

def main():
    """Run interactive chat with the agent"""
    print("=" * 60)
    print("🔧 STIHL Sales Analytics Agent")
    print("=" * 60)
    print("Ask questions about sales trends, products, and performance.")
    print("Type 'quit' to exit, 'clear' to reset conversation.\n")
    
    conversation_history = []
    
    # Test Databricks connection
    print("Testing Databricks connection...")
    try:
        conn = get_databricks_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        print("✅ Databricks connection successful!\n")
    except Exception as e:
        print(f"❌ Databricks connection failed: {e}")
        return
    
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
            
            response = run_agent(user_input, conversation_history)
            
            conversation_history.append({"role": "user", "content": user_input})
            conversation_history.append({"role": "assistant", "content": response})
            
            print(f"\nAgent: {response}\n")
            print("-" * 60)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()