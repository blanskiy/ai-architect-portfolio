"""
Test the STIHL MCP Server tools directly (without MCP protocol)
"""

import asyncio
from pathlib import Path

# Load project-level .env
from dotenv import load_dotenv
project_root = Path(__file__).resolve().parents[4]
load_dotenv(project_root / ".env")

from stihl_mcp_server import (
    query_monthly_trends,
    query_product_performance,
    query_sales_transactions,
    get_sales_summary
)


async def test_tools():
    print("=" * 60)
    print("Testing STIHL MCP Server Tools")
    print("=" * 60)
    
    # Test 1: Monthly Trends
    print("\n📊 Test 1: Monthly Trends (Q4 2024)")
    result = await query_monthly_trends(year=2024, quarter=4)
    print(f"   Rows returned: {result['row_count']}")
    if result['data']:
        print(f"   Sample: {result['data'][0]['year_month']} - ${result['data'][0]['total_revenue']:,.2f}")
    
    # Test 2: Product Performance
    print("\n📊 Test 2: Star Products")
    result = await query_product_performance(performance_tier="Star", top_n=5)
    print(f"   Rows returned: {result['row_count']}")
    for p in result['data'][:3]:
        print(f"   - {p['product_name']}: ${p['last_12_months_revenue']:,.2f}")
    
    # Test 3: Sales Transactions
    print("\n📊 Test 3: West Region Sales")
    result = await query_sales_transactions(region="West")
    print(f"   Total Revenue: ${result['summary']['total_revenue']:,.2f}")
    print(f"   Total Units: {result['summary']['total_units']:,}")
    
    # Test 4: Sales Summary
    print("\n📊 Test 4: Overall Summary")
    result = await get_sales_summary()
    print(f"   Total Revenue: ${result['overall']['total_revenue']:,.2f}")
    print(f"   Date Range: {result['overall']['earliest_date']} to {result['overall']['latest_date']}")
    print(f"   Top Categories:")
    for cat in result['top_categories'][:3]:
        print(f"     - {cat['category']}: ${cat['revenue']:,.2f}")
    
    print("\n" + "=" * 60)
    print("✅ All MCP tools working correctly!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_tools())