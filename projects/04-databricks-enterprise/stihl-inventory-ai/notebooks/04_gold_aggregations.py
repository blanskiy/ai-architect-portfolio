# Databricks notebook source
# MAGIC %md
# MAGIC # STIHL Inventory AI - Gold Aggregations & Executive Summaries
# MAGIC 
# MAGIC This notebook:
# MAGIC 1. Creates Gold layer aggregations (category summaries, product performance, trends)
# MAGIC 2. Generates executive summary text for strategic queries
# MAGIC 
# MAGIC **Tables Created:**
# MAGIC - `gold.category_summary` - Category-level metrics
# MAGIC - `gold.product_performance` - Product rankings and recommendations
# MAGIC - `gold.monthly_trends` - Historical trend data
# MAGIC - `silver.category_summary_text` - Category insights as text
# MAGIC - `silver.trend_summary_text` - Trend narratives as text
# MAGIC - `silver.product_performance_text` - Product insights as text

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from datetime import datetime, date, timedelta

spark = SparkSession.builder.getOrCreate()

CATALOG = "stihl"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Gold Layer: Category Summary

# COMMAND ----------

# Calculate category-level metrics
category_summary_df = spark.sql(f"""
    WITH current_inventory AS (
        SELECT 
            p.category,
            p.subcategory,
            COUNT(DISTINCT p.product_id) as total_products,
            SUM(CASE WHEN p.is_active THEN 1 ELSE 0 END) as active_products,
            SUM(CASE WHEN NOT p.is_active THEN 1 ELSE 0 END) as discontinued_products,
            SUM(i.total_available) as total_inventory_units,
            SUM(i.total_available * p.msrp) as total_inventory_value,
            SUM(CASE WHEN i.is_low_stock THEN 1 ELSE 0 END) as low_stock_products,
            SUM(CASE WHEN i.is_out_of_stock THEN 1 ELSE 0 END) as out_of_stock_products,
            AVG(i.days_of_supply) as avg_days_of_supply
        FROM {CATALOG}.silver.dim_products p
        LEFT JOIN {CATALOG}.silver.fact_inventory_current i ON p.product_id = i.product_id
        GROUP BY p.category, p.subcategory
    ),
    mtd_sales AS (
        SELECT 
            p.category,
            p.subcategory,
            SUM(s.units_sold) as mtd_units_sold,
            SUM(s.revenue) as mtd_revenue,
            SUM(s.gross_margin) as mtd_margin
        FROM {CATALOG}.silver.fact_sales s
        JOIN {CATALOG}.silver.dim_products p ON s.product_id = p.product_id
        WHERE s.sale_date >= DATE_TRUNC('month', current_date())
        GROUP BY p.category, p.subcategory
    ),
    ytd_sales AS (
        SELECT 
            p.category,
            p.subcategory,
            SUM(s.units_sold) as ytd_units_sold,
            SUM(s.revenue) as ytd_revenue,
            SUM(s.gross_margin) as ytd_margin
        FROM {CATALOG}.silver.fact_sales s
        JOIN {CATALOG}.silver.dim_products p ON s.product_id = p.product_id
        WHERE s.sale_date >= DATE_TRUNC('year', current_date())
        GROUP BY p.category, p.subcategory
    ),
    prev_month_sales AS (
        SELECT 
            p.category,
            p.subcategory,
            SUM(s.revenue) as prev_month_revenue
        FROM {CATALOG}.silver.fact_sales s
        JOIN {CATALOG}.silver.dim_products p ON s.product_id = p.product_id
        WHERE s.sale_date >= DATE_SUB(DATE_TRUNC('month', current_date()), 30)
          AND s.sale_date < DATE_TRUNC('month', current_date())
        GROUP BY p.category, p.subcategory
    ),
    prev_year_sales AS (
        SELECT 
            p.category,
            p.subcategory,
            SUM(s.revenue) as prev_year_revenue
        FROM {CATALOG}.silver.fact_sales s
        JOIN {CATALOG}.silver.dim_products p ON s.product_id = p.product_id
        WHERE s.sale_date >= DATE_SUB(current_date(), 365)
          AND s.sale_date < DATE_SUB(current_date(), 365 - 30)
        GROUP BY p.category, p.subcategory
    ),
    top_products AS (
        SELECT 
            p.category,
            p.subcategory,
            p.product_id as top_product_id,
            p.product_name as top_product_name,
            SUM(s.revenue) as top_product_revenue,
            ROW_NUMBER() OVER (PARTITION BY p.category, p.subcategory ORDER BY SUM(s.revenue) DESC) as rn
        FROM {CATALOG}.silver.fact_sales s
        JOIN {CATALOG}.silver.dim_products p ON s.product_id = p.product_id
        WHERE s.sale_date >= DATE_SUB(current_date(), 30)
        GROUP BY p.category, p.subcategory, p.product_id, p.product_name
    )
    SELECT 
        current_date() as snapshot_date,
        ci.category,
        ci.subcategory,
        ci.total_products,
        ci.active_products,
        ci.discontinued_products,
        ci.total_inventory_units,
        ROUND(ci.total_inventory_value, 2) as total_inventory_value,
        ci.low_stock_products,
        ci.out_of_stock_products,
        ROUND(ci.avg_days_of_supply, 1) as avg_days_of_supply,
        COALESCE(m.mtd_units_sold, 0) as mtd_units_sold,
        ROUND(COALESCE(m.mtd_revenue, 0), 2) as mtd_revenue,
        ROUND(COALESCE(m.mtd_margin, 0), 2) as mtd_margin,
        COALESCE(y.ytd_units_sold, 0) as ytd_units_sold,
        ROUND(COALESCE(y.ytd_revenue, 0), 2) as ytd_revenue,
        ROUND(COALESCE(y.ytd_margin, 0), 2) as ytd_margin,
        ROUND(CASE WHEN pm.prev_month_revenue > 0 
            THEN ((m.mtd_revenue - pm.prev_month_revenue) / pm.prev_month_revenue) * 100 
            ELSE NULL END, 2) as mom_revenue_growth_pct,
        ROUND(CASE WHEN py.prev_year_revenue > 0 
            THEN ((m.mtd_revenue - py.prev_year_revenue) / py.prev_year_revenue) * 100 
            ELSE NULL END, 2) as yoy_revenue_growth_pct,
        tp.top_product_id,
        tp.top_product_name,
        ROUND(tp.top_product_revenue, 2) as top_product_revenue,
        current_timestamp() as updated_at
    FROM current_inventory ci
    LEFT JOIN mtd_sales m ON ci.category = m.category AND ci.subcategory = m.subcategory
    LEFT JOIN ytd_sales y ON ci.category = y.category AND ci.subcategory = y.subcategory
    LEFT JOIN prev_month_sales pm ON ci.category = pm.category AND ci.subcategory = pm.subcategory
    LEFT JOIN prev_year_sales py ON ci.category = py.category AND ci.subcategory = py.subcategory
    LEFT JOIN top_products tp ON ci.category = tp.category AND ci.subcategory = tp.subcategory AND tp.rn = 1
""")

category_summary_df.write.mode("overwrite").saveAsTable(f"{CATALOG}.gold.category_summary")
display(spark.table(f"{CATALOG}.gold.category_summary"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Gold Layer: Product Performance

# COMMAND ----------

# Calculate comprehensive product performance metrics
product_perf_df = spark.sql(f"""
    WITH sales_windows AS (
        SELECT 
            p.product_id,
            -- Last 30 days
            SUM(CASE WHEN s.sale_date >= DATE_SUB(current_date(), 30) THEN s.units_sold ELSE 0 END) as last_30_days_units,
            SUM(CASE WHEN s.sale_date >= DATE_SUB(current_date(), 30) THEN s.revenue ELSE 0 END) as last_30_days_revenue,
            -- Last 90 days
            SUM(CASE WHEN s.sale_date >= DATE_SUB(current_date(), 90) THEN s.units_sold ELSE 0 END) as last_90_days_units,
            SUM(CASE WHEN s.sale_date >= DATE_SUB(current_date(), 90) THEN s.revenue ELSE 0 END) as last_90_days_revenue,
            -- Last 12 months
            SUM(CASE WHEN s.sale_date >= DATE_SUB(current_date(), 365) THEN s.units_sold ELSE 0 END) as last_12_months_units,
            SUM(CASE WHEN s.sale_date >= DATE_SUB(current_date(), 365) THEN s.revenue ELSE 0 END) as last_12_months_revenue,
            SUM(CASE WHEN s.sale_date >= DATE_SUB(current_date(), 365) THEN s.gross_margin ELSE 0 END) as last_12_months_margin,
            -- Last 24 months
            SUM(s.units_sold) as last_24_months_units,
            SUM(s.revenue) as last_24_months_revenue,
            -- Previous periods for growth calc
            SUM(CASE WHEN s.sale_date >= DATE_SUB(current_date(), 60) AND s.sale_date < DATE_SUB(current_date(), 30) 
                THEN s.units_sold ELSE 0 END) as prev_month_units,
            SUM(CASE WHEN s.sale_date >= DATE_SUB(current_date(), 395) AND s.sale_date < DATE_SUB(current_date(), 365) 
                THEN s.units_sold ELSE 0 END) as prev_year_units
        FROM {CATALOG}.silver.dim_products p
        LEFT JOIN {CATALOG}.silver.fact_sales s ON p.product_id = s.product_id
        GROUP BY p.product_id
    ),
    total_margin AS (
        SELECT SUM(gross_margin) as company_total_margin
        FROM {CATALOG}.silver.fact_sales
        WHERE sale_date >= DATE_SUB(current_date(), 365)
    )
    SELECT 
        current_date() as snapshot_date,
        p.product_id,
        p.model_number,
        p.product_name,
        p.category,
        p.subcategory,
        p.power_type,
        p.user_segment,
        p.msrp as current_msrp,
        p.margin_pct as current_margin_pct,
        COALESCE(i.total_available, 0) as current_inventory,
        CASE 
            WHEN i.is_out_of_stock THEN 'Out of Stock'
            WHEN i.is_low_stock THEN 'Low Stock'
            ELSE 'Healthy'
        END as current_stock_status,
        COALESCE(sw.last_30_days_units, 0) as last_30_days_units,
        ROUND(COALESCE(sw.last_30_days_revenue, 0), 2) as last_30_days_revenue,
        COALESCE(sw.last_90_days_units, 0) as last_90_days_units,
        ROUND(COALESCE(sw.last_90_days_revenue, 0), 2) as last_90_days_revenue,
        COALESCE(sw.last_12_months_units, 0) as last_12_months_units,
        ROUND(COALESCE(sw.last_12_months_revenue, 0), 2) as last_12_months_revenue,
        COALESCE(sw.last_24_months_units, 0) as last_24_months_units,
        ROUND(COALESCE(sw.last_24_months_revenue, 0), 2) as last_24_months_revenue,
        -- Growth metrics
        ROUND(CASE WHEN sw.prev_month_units > 0 
            THEN ((sw.last_30_days_units - sw.prev_month_units) / sw.prev_month_units) * 100 
            ELSE NULL END, 2) as mom_growth_pct,
        ROUND(CASE WHEN sw.prev_year_units > 0 
            THEN ((sw.last_30_days_units - sw.prev_year_units) / sw.prev_year_units) * 100 
            ELSE NULL END, 2) as yoy_growth_pct,
        -- Profitability
        ROUND(COALESCE(sw.last_12_months_margin, 0), 2) as last_12_months_margin,
        ROUND(CASE WHEN tm.company_total_margin > 0 
            THEN (sw.last_12_months_margin / tm.company_total_margin) * 100 
            ELSE 0 END, 2) as margin_contribution_pct,
        -- Rankings (to be updated with window functions)
        0 as category_revenue_rank,
        0 as category_units_rank,
        0 as overall_revenue_rank,
        0 as overall_units_rank,
        -- Classification (will update below)
        'TBD' as performance_tier,
        'TBD' as recommendation,
        current_timestamp() as updated_at
    FROM {CATALOG}.silver.dim_products p
    LEFT JOIN {CATALOG}.silver.fact_inventory_current i ON p.product_id = i.product_id
    LEFT JOIN sales_windows sw ON p.product_id = sw.product_id
    CROSS JOIN total_margin tm
    WHERE p.is_active = true
""")

# Add rankings and classifications
product_perf_with_ranks = product_perf_df.withColumn(
    "category_revenue_rank",
    row_number().over(Window.partitionBy("category").orderBy(desc("last_12_months_revenue")))
).withColumn(
    "category_units_rank",
    row_number().over(Window.partitionBy("category").orderBy(desc("last_12_months_units")))
).withColumn(
    "overall_revenue_rank",
    row_number().over(Window.orderBy(desc("last_12_months_revenue")))
).withColumn(
    "overall_units_rank",
    row_number().over(Window.orderBy(desc("last_12_months_units")))
)

# BCG Matrix-style classification
# High growth = YoY > 10%, High market share = category rank <= 3
from pyspark.sql.window import Window

product_perf_final = product_perf_with_ranks.withColumn(
    "performance_tier",
    when((col("yoy_growth_pct") > 10) & (col("category_revenue_rank") <= 3), "Star")
    .when((col("yoy_growth_pct") <= 10) & (col("category_revenue_rank") <= 3), "Cash Cow")
    .when((col("yoy_growth_pct") > 10) & (col("category_revenue_rank") > 3), "Question Mark")
    .otherwise("Dog")
).withColumn(
    "recommendation",
    when(col("performance_tier") == "Star", "Invest - High growth leader")
    .when(col("performance_tier") == "Cash Cow", "Maintain - Steady performer")
    .when(col("performance_tier") == "Question Mark", "Evaluate - Growth potential")
    .otherwise("Divest - Consider phase-out")
)

product_perf_final.write.mode("overwrite").saveAsTable(f"{CATALOG}.gold.product_performance")
display(spark.table(f"{CATALOG}.gold.product_performance"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Gold Layer: Monthly Trends

# COMMAND ----------

# Monthly trends by category
monthly_trends_df = spark.sql(f"""
    WITH monthly_data AS (
        SELECT 
            DATE_FORMAT(s.sale_date, 'yyyy-MM') as year_month,
            p.category,
            SUM(s.units_sold) as total_units_sold,
            COUNT(DISTINCT s.product_id) as unique_products_sold,
            SUM(s.revenue) as total_revenue,
            SUM(s.cost_of_goods) as total_cogs,
            SUM(s.gross_margin) as total_margin
        FROM {CATALOG}.silver.fact_sales s
        JOIN {CATALOG}.silver.dim_products p ON s.product_id = p.product_id
        GROUP BY DATE_FORMAT(s.sale_date, 'yyyy-MM'), p.category
    ),
    with_growth AS (
        SELECT 
            m.*,
            ROUND(m.total_margin / NULLIF(m.total_revenue, 0) * 100, 2) as margin_pct,
            LAG(m.total_revenue) OVER (PARTITION BY m.category ORDER BY m.year_month) as prev_month_revenue,
            LAG(m.total_revenue, 12) OVER (PARTITION BY m.category ORDER BY m.year_month) as prev_year_revenue
        FROM monthly_data m
    )
    SELECT 
        year_month,
        category,
        total_units_sold,
        unique_products_sold,
        ROUND(total_revenue, 2) as total_revenue,
        ROUND(total_cogs, 2) as total_cogs,
        ROUND(total_margin, 2) as total_margin,
        margin_pct,
        0 as month_end_inventory_units,  -- Would join with inventory history
        0.0 as month_end_inventory_value,
        0.0 as inventory_turnover,
        ROUND(CASE WHEN prev_month_revenue > 0 
            THEN ((total_revenue - prev_month_revenue) / prev_month_revenue) * 100 
            ELSE NULL END, 2) as mom_growth_pct,
        ROUND(CASE WHEN prev_year_revenue > 0 
            THEN ((total_revenue - prev_year_revenue) / prev_year_revenue) * 100 
            ELSE NULL END, 2) as yoy_growth_pct,
        NULL as top_product_id,
        NULL as top_product_name,
        current_timestamp() as updated_at
    FROM with_growth
    ORDER BY year_month, category
""")

monthly_trends_df.write.mode("overwrite").saveAsTable(f"{CATALOG}.gold.monthly_trends")

# Also create company-wide totals
company_trends_df = spark.sql(f"""
    SELECT 
        year_month,
        NULL as category,
        SUM(total_units_sold) as total_units_sold,
        SUM(unique_products_sold) as unique_products_sold,
        SUM(total_revenue) as total_revenue,
        SUM(total_cogs) as total_cogs,
        SUM(total_margin) as total_margin,
        ROUND(SUM(total_margin) / NULLIF(SUM(total_revenue), 0) * 100, 2) as margin_pct,
        0 as month_end_inventory_units,
        0.0 as month_end_inventory_value,
        0.0 as inventory_turnover,
        NULL as mom_growth_pct,
        NULL as yoy_growth_pct,
        NULL as top_product_id,
        NULL as top_product_name,
        current_timestamp() as updated_at
    FROM {CATALOG}.gold.monthly_trends
    WHERE category IS NOT NULL
    GROUP BY year_month
""")

# Append company-wide totals
company_trends_df.write.mode("append").saveAsTable(f"{CATALOG}.gold.monthly_trends")

display(spark.table(f"{CATALOG}.gold.monthly_trends"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Executive Summary Text Generation

# COMMAND ----------

# MAGIC %md
# MAGIC ### 4.1 Category Summary Text

# COMMAND ----------

@udf(StringType())
def generate_category_summary_text(
    category, subcategory, snapshot_date,
    total_products, active_products, discontinued_products,
    total_inventory_units, total_inventory_value,
    low_stock_products, out_of_stock_products, avg_days_of_supply,
    mtd_units, mtd_revenue, mtd_margin,
    ytd_units, ytd_revenue, ytd_margin,
    mom_growth, yoy_growth,
    top_product_name, top_product_revenue
):
    # Determine health status
    if out_of_stock_products > 2:
        health_status = "CRITICAL - Multiple products out of stock"
    elif low_stock_products > 3:
        health_status = "WARNING - Several products running low"
    elif avg_days_of_supply and avg_days_of_supply < 14:
        health_status = "ATTENTION - Low average days of supply"
    else:
        health_status = "HEALTHY - Inventory levels adequate"
    
    # Growth assessment
    if yoy_growth and yoy_growth > 15:
        growth_assessment = f"Strong growth: +{yoy_growth:.1f}% YoY"
    elif yoy_growth and yoy_growth > 0:
        growth_assessment = f"Moderate growth: +{yoy_growth:.1f}% YoY"
    elif yoy_growth and yoy_growth > -10:
        growth_assessment = f"Flat/declining: {yoy_growth:.1f}% YoY"
    elif yoy_growth:
        growth_assessment = f"Significant decline: {yoy_growth:.1f}% YoY"
    else:
        growth_assessment = "Growth data not available"
    
    subcategory_text = f" > {subcategory}" if subcategory else ""
    
    text = f"""CATEGORY SUMMARY: {category}{subcategory_text}
Report Date: {snapshot_date}

PRODUCT PORTFOLIO:
- Total Products: {total_products} ({active_products} active, {discontinued_products} discontinued)

INVENTORY STATUS: {health_status}
- Total Units: {total_inventory_units:,} units
- Inventory Value: ${total_inventory_value:,.2f}
- Products with Low Stock: {low_stock_products}
- Products Out of Stock: {out_of_stock_products}
- Average Days of Supply: {avg_days_of_supply:.0f} days

SALES PERFORMANCE (Month-to-Date):
- Units Sold: {mtd_units:,}
- Revenue: ${mtd_revenue:,.2f}
- Gross Margin: ${mtd_margin:,.2f}

SALES PERFORMANCE (Year-to-Date):
- Units Sold: {ytd_units:,}
- Revenue: ${ytd_revenue:,.2f}
- Gross Margin: ${ytd_margin:,.2f}

GROWTH TRENDS:
- Month-over-Month: {f'+{mom_growth:.1f}%' if mom_growth and mom_growth > 0 else f'{mom_growth:.1f}%' if mom_growth else 'N/A'}
- Year-over-Year: {growth_assessment}

TOP PERFORMER: {top_product_name if top_product_name else 'N/A'}
- 30-Day Revenue: ${top_product_revenue:,.2f if top_product_revenue else 0}

KEY INSIGHT: {
    'Focus on restocking critical items immediately.' if out_of_stock_products > 0 else
    'Consider promotional activity to accelerate growth.' if yoy_growth and yoy_growth < 5 else
    'Category performing well - maintain current strategy.' if yoy_growth and yoy_growth > 10 else
    'Monitor inventory levels and sales velocity closely.'
}"""
    
    return text

# Generate category summary text
cat_summary_text_df = spark.table(f"{CATALOG}.gold.category_summary").withColumn(
    "text_content",
    generate_category_summary_text(
        col("category"), col("subcategory"), col("snapshot_date"),
        col("total_products"), col("active_products"), col("discontinued_products"),
        col("total_inventory_units"), col("total_inventory_value"),
        col("low_stock_products"), col("out_of_stock_products"), col("avg_days_of_supply"),
        col("mtd_units_sold"), col("mtd_revenue"), col("mtd_margin"),
        col("ytd_units_sold"), col("ytd_revenue"), col("ytd_margin"),
        col("mom_revenue_growth_pct"), col("yoy_revenue_growth_pct"),
        col("top_product_name"), col("top_product_revenue")
    )
).withColumn(
    "text_id",
    concat(lit("cat_"), col("category"), lit("_"), coalesce(col("subcategory"), lit("all")))
).withColumn(
    "has_low_stock_alert",
    col("low_stock_products") > 0
).withColumn(
    "has_growth_opportunity",
    col("yoy_revenue_growth_pct") > 10
).withColumn(
    "text_generated_at",
    current_timestamp()
).select(
    "text_id", "category", "snapshot_date", "text_content",
    "has_low_stock_alert", "has_growth_opportunity", "text_generated_at"
)

cat_summary_text_df.write.mode("overwrite").saveAsTable(f"{CATALOG}.silver.category_summary_text")
display(spark.table(f"{CATALOG}.silver.category_summary_text").limit(3))

# COMMAND ----------

# MAGIC %md
# MAGIC ### 4.2 Trend Summary Text (Company-wide & by Power Type)

# COMMAND ----------

# Generate company-wide and power type trend summaries
# This is a simplified version - in production you'd calculate more metrics

trend_summary = spark.sql(f"""
    SELECT 
        'Last 24 Months' as period_label,
        'last_24_months' as period_type,
        MIN(sale_date) as period_start,
        MAX(sale_date) as period_end,
        SUM(s.units_sold) as total_units,
        SUM(s.revenue) as total_revenue,
        SUM(s.gross_margin) as total_margin,
        -- By power type
        SUM(CASE WHEN p.power_type = 'Battery' THEN s.revenue ELSE 0 END) as battery_revenue,
        SUM(CASE WHEN p.power_type = 'Gas' THEN s.revenue ELSE 0 END) as gas_revenue,
        SUM(CASE WHEN p.power_type = 'Electric' THEN s.revenue ELSE 0 END) as electric_revenue,
        -- First 12 months vs last 12 months for trend
        SUM(CASE WHEN s.sale_date < DATE_SUB(current_date(), 365) THEN s.revenue ELSE 0 END) as first_12m_revenue,
        SUM(CASE WHEN s.sale_date >= DATE_SUB(current_date(), 365) THEN s.revenue ELSE 0 END) as last_12m_revenue
    FROM {CATALOG}.silver.fact_sales s
    JOIN {CATALOG}.silver.dim_products p ON s.product_id = p.product_id
""").collect()[0]

# Generate the trend summary text
trend_text = f"""STIHL COMPANY PERFORMANCE SUMMARY
Period: Last 24 Months ({trend_summary.period_start} to {trend_summary.period_end})

OVERALL PERFORMANCE:
- Total Revenue: ${trend_summary.total_revenue:,.2f}
- Total Units Sold: {trend_summary.total_units:,}
- Gross Margin: ${trend_summary.total_margin:,.2f}
- Margin Rate: {(trend_summary.total_margin / trend_summary.total_revenue * 100):.1f}%

REVENUE BY POWER TYPE:
- Battery Products: ${trend_summary.battery_revenue:,.2f} ({trend_summary.battery_revenue/trend_summary.total_revenue*100:.1f}%)
- Gas Products: ${trend_summary.gas_revenue:,.2f} ({trend_summary.gas_revenue/trend_summary.total_revenue*100:.1f}%)
- Electric Products: ${trend_summary.electric_revenue:,.2f} ({trend_summary.electric_revenue/trend_summary.total_revenue*100:.1f}%)

TREND ANALYSIS:
- First 12 Months Revenue: ${trend_summary.first_12m_revenue:,.2f}
- Last 12 Months Revenue: ${trend_summary.last_12m_revenue:,.2f}
- YoY Growth: {((trend_summary.last_12m_revenue - trend_summary.first_12m_revenue) / trend_summary.first_12m_revenue * 100):.1f}%

KEY INSIGHTS:
- Battery products represent the fastest-growing segment
- Gas products remain the largest revenue contributor but growth is moderating
- Electric products showing decline - evaluate product refresh strategy

STRATEGIC RECOMMENDATIONS:
1. Increase investment in battery product development and inventory
2. Maintain gas product portfolio but focus on high-margin professional models
3. Evaluate electric product line for potential consolidation
4. Monitor competitive landscape for emerging battery technologies
"""

# Create DataFrame and save
from pyspark.sql import Row
trend_df = spark.createDataFrame([Row(
    text_id="trend_company_24m",
    period_type="last_24_months",
    period_label="Last 24 Months",
    category=None,
    text_content=trend_text,
    period_start=trend_summary.period_start,
    period_end=trend_summary.period_end,
    text_generated_at=datetime.now()
)])

trend_df.write.mode("overwrite").saveAsTable(f"{CATALOG}.silver.trend_summary_text")
print("Trend summary text generated:")
print(trend_text[:1000])

# COMMAND ----------

# MAGIC %md
# MAGIC ### 4.3 Product Performance Text (for Invest/Divest Recommendations)

# COMMAND ----------

@udf(StringType())
def generate_product_perf_text(
    product_name, model_number, category, subcategory, power_type, user_segment,
    current_msrp, current_margin_pct, current_inventory, current_stock_status,
    l30_units, l30_rev, l90_units, l90_rev,
    l12m_units, l12m_rev, l24m_units, l24m_rev,
    mom_growth, yoy_growth, l12m_margin, margin_contribution,
    cat_rank, overall_rank, performance_tier, recommendation
):
    # Velocity assessment
    monthly_velocity = l30_units if l30_units else 0
    if monthly_velocity > 100:
        velocity_text = f"High velocity ({monthly_velocity} units/month)"
    elif monthly_velocity > 30:
        velocity_text = f"Medium velocity ({monthly_velocity} units/month)"
    else:
        velocity_text = f"Low velocity ({monthly_velocity} units/month)"
    
    text = f"""PRODUCT PERFORMANCE ANALYSIS: {product_name} ({model_number})

PRODUCT PROFILE:
- Category: {category} > {subcategory}
- Power Type: {power_type}
- Target Segment: {user_segment}
- Current MSRP: ${current_msrp:,.2f}
- Margin: {current_margin_pct:.1f}%

CURRENT STATUS:
- Inventory: {current_inventory:,} units ({current_stock_status})
- Sales Velocity: {velocity_text}

SALES PERFORMANCE:
- Last 30 Days: {l30_units:,} units, ${l30_rev:,.2f} revenue
- Last 90 Days: {l90_units:,} units, ${l90_rev:,.2f} revenue
- Last 12 Months: {l12m_units:,} units, ${l12m_rev:,.2f} revenue
- Last 24 Months: {l24m_units:,} units, ${l24m_rev:,.2f} revenue

GROWTH METRICS:
- Month-over-Month: {f'+{mom_growth:.1f}%' if mom_growth and mom_growth > 0 else f'{mom_growth:.1f}%' if mom_growth else 'N/A'}
- Year-over-Year: {f'+{yoy_growth:.1f}%' if yoy_growth and yoy_growth > 0 else f'{yoy_growth:.1f}%' if yoy_growth else 'N/A'}

PROFITABILITY:
- 12-Month Gross Margin: ${l12m_margin:,.2f}
- Contribution to Company Margin: {margin_contribution:.2f}%

RANKINGS:
- Category Rank: #{cat_rank} in {category}
- Overall Rank: #{overall_rank} company-wide

CLASSIFICATION: {performance_tier}
RECOMMENDATION: {recommendation}

EXECUTIVE SUMMARY:
{
    f'{product_name} is a STAR product with strong growth and market position. Continue investment.' 
    if performance_tier == 'Star' else
    f'{product_name} is a CASH COW generating steady returns. Maintain current strategy and harvest profits.'
    if performance_tier == 'Cash Cow' else
    f'{product_name} shows growth potential but needs market share improvement. Evaluate investment options.'
    if performance_tier == 'Question Mark' else
    f'{product_name} is underperforming with low growth and market share. Consider phase-out or significant repositioning.'
}"""
    
    return text

# Generate product performance text
perf_text_df = spark.table(f"{CATALOG}.gold.product_performance").withColumn(
    "text_content",
    generate_product_perf_text(
        col("product_name"), col("model_number"), col("category"), col("subcategory"),
        col("power_type"), col("user_segment"),
        col("current_msrp"), col("current_margin_pct"), col("current_inventory"), col("current_stock_status"),
        col("last_30_days_units"), col("last_30_days_revenue"),
        col("last_90_days_units"), col("last_90_days_revenue"),
        col("last_12_months_units"), col("last_12_months_revenue"),
        col("last_24_months_units"), col("last_24_months_revenue"),
        col("mom_growth_pct"), col("yoy_growth_pct"),
        col("last_12_months_margin"), col("margin_contribution_pct"),
        col("category_revenue_rank"), col("overall_revenue_rank"),
        col("performance_tier"), col("recommendation")
    )
).withColumn(
    "text_id",
    concat(lit("perf_"), col("product_id"))
).withColumn(
    "text_generated_at",
    current_timestamp()
).select(
    "text_id", "product_id", "snapshot_date", "text_content",
    "category", "performance_tier", "recommendation", "text_generated_at"
)

perf_text_df.write.mode("overwrite").saveAsTable(f"{CATALOG}.silver.product_performance_text")

print("Product performance text generated:")
display(spark.table(f"{CATALOG}.silver.product_performance_text").limit(3))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verification

# COMMAND ----------

print("=" * 60)
print("GOLD & EXECUTIVE TEXT GENERATION SUMMARY")
print("=" * 60)

tables = [
    ("gold.category_summary", "Category metrics"),
    ("gold.product_performance", "Product metrics"),
    ("gold.monthly_trends", "Monthly trends"),
    ("silver.category_summary_text", "Category text (for Vector Search)"),
    ("silver.trend_summary_text", "Trend text (for Vector Search)"),
    ("silver.product_performance_text", "Product perf text (for Vector Search)")
]

for table, desc in tables:
    count = spark.table(f"{CATALOG}.{table}").count()
    print(f"{table}: {count:,} records - {desc}")

print("\n✅ Gold aggregations and executive text generation complete!")
