"""
Lab 7 Part 2: Custom STIHL Sales Analytics MCP Server
"""

import os
import json
import asyncio
from typing import Any
from pathlib import Path

# Load project-level .env
from dotenv import load_dotenv
project_root = Path(__file__).resolve().parents[4]
load_dotenv(project_root / ".env")

from databricks import sql as databricks_sql

# Configuration
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_CATALOG = os.getenv("DATABRICKS_CATALOG", "ai_systems")


def get_databricks_connection():
    """Create Databricks SQL connection"""
    return databricks_sql.connect(
        server_hostname=DATABRICKS_HOST,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN,
        catalog=DATABRICKS_CATALOG
    )


# =============================================================================
# MCP TOOL IMPLEMENTATIONS (These are the actual business logic)
# =============================================================================

async def query_monthly_trends(
    year: int = None, 
    quarter: int = None,
    category: str = None
) -> dict:
    """Query monthly sales trends"""
    
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
    
    if year:
        query += f" AND year_month LIKE '{year}%'"
        if quarter:
            months = {1: ['01','02','03'], 2: ['04','05','06'], 
                     3: ['07','08','09'], 4: ['10','11','12']}
            month_list = months.get(quarter, [])
            if month_list:
                conditions = " OR ".join([f"year_month LIKE '%-{m}'" for m in month_list])
                query += f" AND ({conditions})"
    
    if category:
        query += f" AND LOWER(category) LIKE LOWER('%{category}%')"
    
    query += " ORDER BY year_month DESC LIMIT 24"
    
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    results = [dict(zip(columns, row)) for row in rows]
    
    cursor.close()
    conn.close()
    
    return {
        "tool": "query_monthly_trends",
        "filters": {"year": year, "quarter": quarter, "category": category},
        "row_count": len(results),
        "data": results
    }


async def query_product_performance(
    category: str = None,
    performance_tier: str = None,
    top_n: int = 10
) -> dict:
    """Query product performance metrics"""
    
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
    
    return {
        "tool": "query_product_performance",
        "filters": {"category": category, "performance_tier": performance_tier, "top_n": top_n},
        "row_count": len(results),
        "data": results
    }


async def query_sales_transactions(
    start_date: str = None,
    end_date: str = None,
    region: str = None,
    channel: str = None
) -> dict:
    """Query sales transactions with summary"""
    
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
    
    # Summary stats
    summary_query = f"""
    SELECT 
        COUNT(*) as total_transactions,
        SUM(units_sold) as total_units,
        SUM(revenue) as total_revenue,
        SUM(gross_margin) as total_margin,
        AVG(revenue) as avg_transaction_value
    FROM {DATABRICKS_CATALOG}.stihl_silver.fact_sales
    {where_clause}
    """
    
    cursor.execute(summary_query)
    summary_cols = [desc[0] for desc in cursor.description]
    summary_row = cursor.fetchone()
    summary = dict(zip(summary_cols, summary_row)) if summary_row else {}
    
    # Regional breakdown
    region_query = f"""
    SELECT region, SUM(revenue) as revenue, SUM(units_sold) as units
    FROM {DATABRICKS_CATALOG}.stihl_silver.fact_sales
    {where_clause}
    GROUP BY region ORDER BY revenue DESC
    """
    
    cursor.execute(region_query)
    region_cols = [desc[0] for desc in cursor.description]
    region_rows = cursor.fetchall()
    by_region = [dict(zip(region_cols, row)) for row in region_rows]
    
    cursor.close()
    conn.close()
    
    return {
        "tool": "query_sales_transactions",
        "filters": {"start_date": start_date, "end_date": end_date, "region": region, "channel": channel},
        "summary": summary,
        "by_region": by_region
    }


async def get_sales_summary() -> dict:
    """Get high-level sales summary"""
    
    conn = get_databricks_connection()
    cursor = conn.cursor()
    
    cursor.execute(f"""
    SELECT 
        COUNT(*) as total_transactions,
        SUM(revenue) as total_revenue,
        SUM(units_sold) as total_units,
        AVG(revenue) as avg_transaction_value,
        COUNT(DISTINCT region) as regions,
        MIN(sale_date) as earliest_date,
        MAX(sale_date) as latest_date
    FROM {DATABRICKS_CATALOG}.stihl_silver.fact_sales
    """)
    
    cols = [desc[0] for desc in cursor.description]
    row = cursor.fetchone()
    overall = dict(zip(cols, row)) if row else {}
    
    cursor.execute(f"""
    SELECT category, SUM(last_12_months_revenue) as revenue
    FROM {DATABRICKS_CATALOG}.stihl_gold.product_performance
    GROUP BY category ORDER BY revenue DESC LIMIT 5
    """)
    
    cat_cols = [desc[0] for desc in cursor.description]
    cat_rows = cursor.fetchall()
    top_categories = [dict(zip(cat_cols, row)) for row in cat_rows]
    
    cursor.close()
    conn.close()
    
    return {
        "tool": "get_sales_summary",
        "overall": overall,
        "top_categories": top_categories
    }


# =============================================================================
# MCP TOOL REGISTRY (Metadata for tool discovery)
# =============================================================================

MCP_TOOLS = {
    "query_monthly_trends": {
        "function": query_monthly_trends,
        "description": "Query STIHL monthly sales trends including revenue, units sold, margins, and growth rates.",
        "parameters": {
            "year": {"type": "integer", "description": "Filter by year (e.g., 2024)"},
            "quarter": {"type": "integer", "description": "Filter by quarter (1-4)"},
            "category": {"type": "string", "description": "Product category filter"}
        }
    },
    "query_product_performance": {
        "function": query_product_performance,
        "description": "Query product performance metrics including BCG matrix classification.",
        "parameters": {
            "category": {"type": "string", "description": "Product category"},
            "performance_tier": {"type": "string", "description": "BCG tier: Star, Cash Cow, Question Mark, Dog"},
            "top_n": {"type": "integer", "description": "Number of products to return"}
        }
    },
    "query_sales_transactions": {
        "function": query_sales_transactions,
        "description": "Query sales transactions with summary statistics and regional breakdowns.",
        "parameters": {
            "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
            "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
            "region": {"type": "string", "description": "Region filter"},
            "channel": {"type": "string", "description": "Sales channel filter"}
        }
    },
    "get_sales_summary": {
        "function": get_sales_summary,
        "description": "Get high-level summary of STIHL sales performance.",
        "parameters": {}
    }
}


def list_tools():
    """List all available MCP tools"""
    return [
        {
            "name": name,
            "description": info["description"],
            "parameters": info["parameters"]
        }
        for name, info in MCP_TOOLS.items()
    ]


async def call_tool(name: str, arguments: dict = None) -> dict:
    """Call an MCP tool by name"""
    if name not in MCP_TOOLS:
        return {"error": f"Unknown tool: {name}"}
    
    func = MCP_TOOLS[name]["function"]
    return await func(**(arguments or {}))