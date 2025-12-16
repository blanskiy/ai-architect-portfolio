# Databricks notebook source
# MAGIC %md
# MAGIC # STIHL Inventory AI - Text Generation for Vector Search
# MAGIC 
# MAGIC This notebook converts tabular data into natural language text representations
# MAGIC suitable for embedding and semantic search.
# MAGIC 
# MAGIC **Text Tables Generated:**
# MAGIC 1. `product_details_text` - Static product info (WEEKLY sync)
# MAGIC 2. `inventory_status_text` - Dynamic inventory + pricing (DAILY sync)
# MAGIC 3. `sales_summary_text` - Monthly sales records (DAILY sync)
# MAGIC 
# MAGIC **Key Design Decisions:**
# MAGIC - Static product specs separated from dynamic pricing/inventory
# MAGIC - Price lives in inventory_status_text (changes frequently)
# MAGIC - Text templates designed for semantic similarity matching

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from datetime import datetime, date
import uuid

spark = SparkSession.builder.getOrCreate()

CATALOG = "stihl"
SCHEMA = "silver"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Product Details Text (Static - Weekly Sync)
# MAGIC 
# MAGIC Contains specifications, features, description - rarely changes.
# MAGIC Does NOT include price (that's in inventory_status_text).

# COMMAND ----------

# Text template for product details
PRODUCT_DETAIL_TEMPLATE = """Product: {product_name}
Model Number: {model_number}
Category: {category} > {subcategory}
Power Type: {power_type}
Target User: {user_segment}
{specs_section}
Description: {description}
Key Features: {features}
Product Status: {status_text}
Launch Date: {launch_date}"""

def generate_product_specs(row):
    """Generate specifications section based on product type"""
    specs = []
    
    if row.engine_displacement_cc:
        specs.append(f"Engine: {row.engine_displacement_cc}cc")
    if row.bar_length_inches:
        specs.append(f"Bar Length: {row.bar_length_inches} inches")
    if row.cutting_width_inches:
        specs.append(f"Cutting Width: {row.cutting_width_inches} inches")
    if row.weight_lbs:
        specs.append(f"Weight: {row.weight_lbs} lbs")
    
    if specs:
        return "Specifications: " + ", ".join(specs)
    return "Specifications: See product manual"

def generate_product_status(row):
    """Generate status text"""
    if not row.is_active:
        return f"Discontinued as of {row.discontinue_date}"
    return "Currently Active"

# Create UDF for text generation
@udf(StringType())
def generate_product_text(
    product_name, model_number, category, subcategory, power_type,
    user_segment, engine_cc, bar_length, cutting_width, weight,
    description, features, is_active, launch_date, discontinue_date
):
    # Build specs section
    specs = []
    if engine_cc:
        specs.append(f"Engine: {engine_cc}cc")
    if bar_length:
        specs.append(f"Bar Length: {bar_length} inches")
    if cutting_width:
        specs.append(f"Cutting Width: {cutting_width} inches")
    if weight:
        specs.append(f"Weight: {weight} lbs")
    
    specs_section = "Specifications: " + ", ".join(specs) if specs else ""
    
    # Status text
    status_text = "Currently Active" if is_active else f"Discontinued"
    
    # Format features
    features_text = features if features else "Standard features"
    
    text = f"""Product: {product_name}
Model Number: {model_number}
Category: {category} > {subcategory}
Power Type: {power_type}
Target User: {user_segment}
{specs_section}
Description: {description}
Key Features: {features_text}
Product Status: {status_text}
Launch Date: {launch_date}"""
    
    return text.strip()

# Generate product details text
product_text_df = spark.sql(f"""
    SELECT 
        product_id,
        model_number,
        product_name,
        category,
        subcategory,
        power_type,
        user_segment,
        engine_displacement_cc,
        bar_length_inches,
        cutting_width_inches,
        weight_lbs,
        description,
        features,
        is_active,
        launch_date,
        discontinue_date,
        updated_at
    FROM {CATALOG}.{SCHEMA}.dim_products
""")

product_text_df = product_text_df.withColumn(
    "text_content",
    generate_product_text(
        col("product_name"),
        col("model_number"),
        col("category"),
        col("subcategory"),
        col("power_type"),
        col("user_segment"),
        col("engine_displacement_cc"),
        col("bar_length_inches"),
        col("cutting_width_inches"),
        col("weight_lbs"),
        col("description"),
        col("features"),
        col("is_active"),
        col("launch_date"),
        col("discontinue_date")
    )
).withColumn(
    "text_id",
    concat(lit("prod_"), col("product_id"))
).withColumn(
    "source_updated_at",
    col("updated_at")
).withColumn(
    "text_generated_at",
    current_timestamp()
).select(
    "text_id",
    "product_id",
    "text_content",
    "category",
    "subcategory",
    "power_type",
    "user_segment",
    "is_active",
    "source_updated_at",
    "text_generated_at"
)

# Write to table
product_text_df.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.product_details_text")

print("Product details text generated:")
display(spark.table(f"{CATALOG}.{SCHEMA}.product_details_text").limit(3))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Inventory Status Text (Dynamic - Daily Sync)
# MAGIC 
# MAGIC Contains current pricing, inventory levels, stock status.
# MAGIC This is where PRICE lives since it changes frequently.

# COMMAND ----------

@udf(StringType())
def generate_inventory_text(
    product_name, model_number, category, snapshot_date,
    msrp, cost, margin_pct, 
    on_hand, in_transit, reserved, available,
    reorder_point, is_low_stock, is_out_of_stock,
    avg_daily_sales, days_of_supply
):
    # Stock status text
    if is_out_of_stock:
        stock_status = "OUT OF STOCK - Urgent restocking needed"
        pct_of_reorder = 0
    elif is_low_stock:
        pct_of_reorder = int((available / reorder_point * 100)) if reorder_point > 0 else 0
        stock_status = f"LOW STOCK - Below reorder point ({pct_of_reorder}% of target)"
    else:
        pct_of_reorder = int((available / reorder_point * 100)) if reorder_point > 0 else 100
        if pct_of_reorder > 150:
            stock_status = f"OVERSTOCKED - {pct_of_reorder}% of reorder point"
        else:
            stock_status = f"HEALTHY - {pct_of_reorder}% of reorder point"
    
    # Alert message
    if is_out_of_stock:
        alert = "CRITICAL: Product unavailable for sale. Expedite reorder."
    elif is_low_stock:
        alert = "WARNING: Stock below reorder point. Place order soon."
    elif days_of_supply and days_of_supply < 14:
        alert = f"ATTENTION: Only {days_of_supply} days of supply remaining."
    else:
        alert = "No alerts - inventory levels adequate."
    
    # Velocity description
    if avg_daily_sales:
        if avg_daily_sales > 20:
            velocity_desc = f"High velocity: {avg_daily_sales:.1f} units/day"
        elif avg_daily_sales > 5:
            velocity_desc = f"Medium velocity: {avg_daily_sales:.1f} units/day"
        else:
            velocity_desc = f"Low velocity: {avg_daily_sales:.1f} units/day"
    else:
        velocity_desc = "Velocity data unavailable"
    
    text = f"""{product_name} ({model_number}) - Inventory & Pricing Status
Category: {category}
Snapshot Date: {snapshot_date}

CURRENT PRICING:
- MSRP: ${msrp:,.2f}
- Cost: ${cost:,.2f}
- Margin: {margin_pct:.1f}%

INVENTORY LEVELS:
- On Hand: {on_hand:,} units
- In Transit: {in_transit:,} units arriving soon
- Reserved: {reserved:,} units for pending orders
- Available for Sale: {available:,} units

STOCK STATUS: {stock_status}
- Reorder Point: {reorder_point:,} units
- Days of Supply: {days_of_supply if days_of_supply else 'N/A'} days
- Sales Velocity: {velocity_desc}

ALERT: {alert}"""
    
    return text

# Join products with inventory for current snapshot
inventory_text_df = spark.sql(f"""
    SELECT 
        p.product_id,
        p.product_name,
        p.model_number,
        p.category,
        p.msrp,
        p.cost,
        p.margin_pct,
        i.snapshot_date,
        i.total_on_hand,
        i.total_in_transit,
        i.total_reserved,
        i.total_available,
        i.reorder_point,
        i.is_low_stock,
        i.is_out_of_stock,
        i.avg_daily_sales,
        i.days_of_supply
    FROM {CATALOG}.{SCHEMA}.dim_products p
    JOIN {CATALOG}.{SCHEMA}.fact_inventory_current i
        ON p.product_id = i.product_id
    WHERE p.is_active = true
""")

inventory_text_df = inventory_text_df.withColumn(
    "text_content",
    generate_inventory_text(
        col("product_name"),
        col("model_number"),
        col("category"),
        col("snapshot_date"),
        col("msrp"),
        col("cost"),
        col("margin_pct"),
        col("total_on_hand"),
        col("total_in_transit"),
        col("total_reserved"),
        col("total_available"),
        col("reorder_point"),
        col("is_low_stock"),
        col("is_out_of_stock"),
        col("avg_daily_sales"),
        col("days_of_supply")
    )
).withColumn(
    "text_id",
    concat(lit("inv_"), col("product_id"), lit("_"), col("snapshot_date"))
).withColumn(
    "stock_status",
    when(col("is_out_of_stock"), lit("Out of Stock"))
    .when(col("is_low_stock"), lit("Low Stock"))
    .otherwise(lit("Healthy"))
).withColumn(
    "current_msrp",
    col("msrp")
).withColumn(
    "current_margin_pct",
    col("margin_pct")
).withColumn(
    "text_generated_at",
    current_timestamp()
).select(
    "text_id",
    "product_id",
    "snapshot_date",
    "text_content",
    "category",
    "is_low_stock",
    "is_out_of_stock",
    "stock_status",
    "current_msrp",
    "current_margin_pct",
    "days_of_supply",
    "text_generated_at"
)

# Write to table (overwrite for current snapshot)
inventory_text_df.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.inventory_status_text")

print("Inventory status text generated:")
display(spark.table(f"{CATALOG}.{SCHEMA}.inventory_status_text").limit(3))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Sales Summary Text (Monthly Aggregates - Daily Sync)
# MAGIC 
# MAGIC Monthly sales performance by product for trend analysis.

# COMMAND ----------

@udf(StringType())
def generate_sales_text(
    product_name, model_number, category, year_month,
    period_start, period_end,
    total_units, total_revenue, total_margin,
    east_units, east_rev, central_units, central_rev,
    west_units, west_rev, south_units, south_rev,
    retail_units, pro_dealer_units, online_units,
    prev_month_units, prev_year_units
):
    # Calculate percentages
    total = east_units + central_units + west_units + south_units
    
    # Month-over-month change
    if prev_month_units and prev_month_units > 0:
        mom_change = ((total_units - prev_month_units) / prev_month_units) * 100
        mom_text = f"+{mom_change:.1f}%" if mom_change > 0 else f"{mom_change:.1f}%"
    else:
        mom_text = "N/A (no prior month)"
    
    # Year-over-year change
    if prev_year_units and prev_year_units > 0:
        yoy_change = ((total_units - prev_year_units) / prev_year_units) * 100
        yoy_text = f"+{yoy_change:.1f}%" if yoy_change > 0 else f"{yoy_change:.1f}%"
    else:
        yoy_text = "N/A (no prior year)"
    
    # Channel breakdown
    channel_total = retail_units + pro_dealer_units + online_units
    if channel_total > 0:
        retail_pct = retail_units / channel_total * 100
        pro_pct = pro_dealer_units / channel_total * 100
        online_pct = online_units / channel_total * 100
    else:
        retail_pct = pro_pct = online_pct = 0
    
    text = f"""Sales Record: {product_name} ({model_number})
Category: {category}
Period: {year_month} ({period_start} to {period_end})

SALES PERFORMANCE:
- Units Sold: {total_units:,} units
- Revenue: ${total_revenue:,.2f}
- Gross Margin: ${total_margin:,.2f}
- Average Selling Price: ${(total_revenue/total_units):,.2f}

REGIONAL BREAKDOWN:
- East: {east_units:,} units (${east_rev:,.2f})
- Central: {central_units:,} units (${central_rev:,.2f})
- West: {west_units:,} units (${west_rev:,.2f})
- South: {south_units:,} units (${south_rev:,.2f})

CHANNEL MIX:
- Retail: {retail_units:,} units ({retail_pct:.0f}%)
- Pro Dealer: {pro_dealer_units:,} units ({pro_pct:.0f}%)
- Online: {online_units:,} units ({online_pct:.0f}%)

GROWTH METRICS:
- Month-over-Month: {mom_text}
- Year-over-Year: {yoy_text}"""
    
    return text

# Aggregate sales by product and month
sales_agg_df = spark.sql(f"""
    WITH monthly_sales AS (
        SELECT 
            product_id,
            DATE_FORMAT(sale_date, 'yyyy-MM') as year_month,
            MIN(sale_date) as period_start,
            MAX(sale_date) as period_end,
            SUM(units_sold) as total_units,
            SUM(revenue) as total_revenue,
            SUM(gross_margin) as total_margin,
            -- Regional breakdown
            SUM(CASE WHEN region = 'East' THEN units_sold ELSE 0 END) as east_units,
            SUM(CASE WHEN region = 'East' THEN revenue ELSE 0 END) as east_rev,
            SUM(CASE WHEN region = 'Central' THEN units_sold ELSE 0 END) as central_units,
            SUM(CASE WHEN region = 'Central' THEN revenue ELSE 0 END) as central_rev,
            SUM(CASE WHEN region = 'West' THEN units_sold ELSE 0 END) as west_units,
            SUM(CASE WHEN region = 'West' THEN revenue ELSE 0 END) as west_rev,
            SUM(CASE WHEN region = 'South' THEN units_sold ELSE 0 END) as south_units,
            SUM(CASE WHEN region = 'South' THEN revenue ELSE 0 END) as south_rev,
            -- Channel breakdown
            SUM(CASE WHEN channel = 'Retail' THEN units_sold ELSE 0 END) as retail_units,
            SUM(CASE WHEN channel = 'Pro Dealer' THEN units_sold ELSE 0 END) as pro_dealer_units,
            SUM(CASE WHEN channel = 'Online' THEN units_sold ELSE 0 END) as online_units
        FROM {CATALOG}.{SCHEMA}.fact_sales
        GROUP BY product_id, DATE_FORMAT(sale_date, 'yyyy-MM')
    ),
    with_prev AS (
        SELECT 
            m.*,
            LAG(total_units) OVER (PARTITION BY product_id ORDER BY year_month) as prev_month_units,
            LAG(total_units, 12) OVER (PARTITION BY product_id ORDER BY year_month) as prev_year_units
        FROM monthly_sales m
    )
    SELECT 
        w.*,
        p.product_name,
        p.model_number,
        p.category
    FROM with_prev w
    JOIN {CATALOG}.{SCHEMA}.dim_products p ON w.product_id = p.product_id
""")

sales_text_df = sales_agg_df.withColumn(
    "text_content",
    generate_sales_text(
        col("product_name"),
        col("model_number"),
        col("category"),
        col("year_month"),
        col("period_start"),
        col("period_end"),
        col("total_units"),
        col("total_revenue"),
        col("total_margin"),
        col("east_units"),
        col("east_rev"),
        col("central_units"),
        col("central_rev"),
        col("west_units"),
        col("west_rev"),
        col("south_units"),
        col("south_rev"),
        col("retail_units"),
        col("pro_dealer_units"),
        col("online_units"),
        col("prev_month_units"),
        col("prev_year_units")
    )
).withColumn(
    "text_id",
    concat(lit("sales_"), col("product_id"), lit("_"), col("year_month"))
).withColumn(
    "period_type",
    lit("monthly")
).withColumn(
    "yoy_growth_pct",
    when(col("prev_year_units") > 0,
         ((col("total_units") - col("prev_year_units")) / col("prev_year_units") * 100)
    ).otherwise(lit(None))
).withColumn(
    "text_generated_at",
    current_timestamp()
).select(
    "text_id",
    "product_id",
    "period_type",
    "period_start",
    "period_end",
    "text_content",
    "category",
    "year_month",
    "total_units",
    "total_revenue",
    "yoy_growth_pct",
    "text_generated_at"
)

# Write to table
sales_text_df.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA}.sales_summary_text")

print("Sales summary text generated:")
display(spark.table(f"{CATALOG}.{SCHEMA}.sales_summary_text").limit(3))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verification

# COMMAND ----------

print("=" * 60)
print("TEXT GENERATION SUMMARY")
print("=" * 60)

# Count records in each table
for table in ["product_details_text", "inventory_status_text", "sales_summary_text"]:
    count = spark.table(f"{CATALOG}.{SCHEMA}.{table}").count()
    print(f"\n{table}: {count:,} records")

# Sample text from each
print("\n" + "=" * 60)
print("SAMPLE TEXT: Product Details")
print("=" * 60)
sample_product = spark.table(f"{CATALOG}.{SCHEMA}.product_details_text").first()
print(sample_product.text_content)

print("\n" + "=" * 60)
print("SAMPLE TEXT: Inventory Status")
print("=" * 60)
sample_inv = spark.table(f"{CATALOG}.{SCHEMA}.inventory_status_text").first()
print(sample_inv.text_content)

print("\n" + "=" * 60)
print("SAMPLE TEXT: Sales Summary")
print("=" * 60)
sample_sales = spark.table(f"{CATALOG}.{SCHEMA}.sales_summary_text").first()
print(sample_sales.text_content)

# Verify CDF is enabled
print("\n" + "=" * 60)
print("CDF STATUS")
print("=" * 60)
for table in ["product_details_text", "inventory_status_text", "sales_summary_text"]:
    props = spark.sql(f"SHOW TBLPROPERTIES {CATALOG}.{SCHEMA}.{table}").filter("key = 'delta.enableChangeDataFeed'").collect()
    cdf_status = props[0].value if props else "Not set"
    print(f"{table}: CDF = {cdf_status}")

print("\n✅ Text generation complete!")
