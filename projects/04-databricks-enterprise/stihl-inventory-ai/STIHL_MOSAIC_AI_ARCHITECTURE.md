# STIHL Inventory Analytics with Databricks Mosaic AI
## Complete Architecture & Implementation Guide

---

# Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Data Model Design](#3-data-model-design)
4. [Embedding Strategy for Tabular Data](#4-embedding-strategy-for-tabular-data)
5. [Pipeline Design](#5-pipeline-design)
6. [Implementation Notebooks](#6-implementation-notebooks)
7. [Agent Design](#7-agent-design)
8. [Sample Queries by Persona](#8-sample-queries-by-persona)

---

# 1. Executive Summary

## Business Context
STIHL is a global manufacturer of outdoor power equipment (chainsaws, trimmers, blowers, etc.). The data engineering team maintains inventory and sales data in Azure Databricks. Management wants to query this data using natural language via LLM/AI Agents.

## Solution Overview
We'll extend the existing Medallion architecture to support **semantic search over tabular data** using Databricks Mosaic AI Vector Search.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SOLUTION AT A GLANCE                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  EXISTING PIPELINE (Traditional Analytics)                                  │
│  ══════════════════════════════════════════                                 │
│                                                                              │
│  Bronze ──▶ Silver ──▶ Gold ──▶ Dashboards/Reports                         │
│  (raw)     (clean)    (agg)                                                 │
│                                                                              │
│  NEW ADDITION (AI/LLM Analytics)                                            │
│  ══════════════════════════════                                             │
│                                                                              │
│  Silver ──▶ Silver (Text Representations) ──▶ Vector Index ──▶ AI Agent    │
│  (clean)   (product_text, inventory_text)     (embeddings)    (LLM queries)│
│                                                                              │
│            Gold ──▶ Silver (Aggregated Summaries) ──▶ Vector Index         │
│            (agg)   (category_summaries, trends)       (embeddings)         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Embedding location | Silver layer | Text representations are transformations, not aggregations |
| Two index types | Row-level + Aggregated | Different query patterns need different granularity |
| Snapshot vs Historical | Separate tables | Enables both "now" and "trend" questions |
| Query approach | Semantic search + context | More flexible than Text-to-SQL for complex questions |

---

# 2. Architecture Overview

## 2.1 Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STIHL MOSAIC AI ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         DATA SOURCES                                 │   │
│  │                                                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│  │  │ ERP System  │  │ POS Systems │  │ Warehouse   │                 │   │
│  │  │ (Products)  │  │ (Sales)     │  │ Management  │                 │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                 │   │
│  │         │                │                │                         │   │
│  │         └────────────────┴────────────────┘                         │   │
│  │                          │                                           │   │
│  │                          ▼ Daily ETL                                │   │
│  └──────────────────────────┼───────────────────────────────────────────┘   │
│                             │                                               │
│  ╔═══════════════════════════════════════════════════════════════════════╗ │
│  ║                    BRONZE LAYER (Raw Ingestion)                        ║ │
│  ╠═══════════════════════════════════════════════════════════════════════╣ │
│  ║                                                                        ║ │
│  ║  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐         ║ │
│  ║  │ bronze_products │ │ bronze_inventory│ │ bronze_sales    │         ║ │
│  ║  │ (daily dump)    │ │ (daily snapshot)│ │ (daily txns)    │         ║ │
│  ║  └────────┬────────┘ └────────┬────────┘ └────────┬────────┘         ║ │
│  ║           │                   │                   │                   ║ │
│  ╚═══════════╪═══════════════════╪═══════════════════╪═══════════════════╝ │
│              │                   │                   │                     │
│              ▼                   ▼                   ▼                     │
│  ╔═══════════════════════════════════════════════════════════════════════╗ │
│  ║                    SILVER LAYER (Cleaned + Transformed)                ║ │
│  ╠═══════════════════════════════════════════════════════════════════════╣ │
│  ║                                                                        ║ │
│  ║  CLEANED TABLES                      TEXT REPRESENTATIONS              ║ │
│  ║  ┌─────────────────┐                 ┌─────────────────────────────┐  ║ │
│  ║  │ silver_products │ ─────────────▶ │ silver_product_text         │  ║ │
│  ║  │ (dedupe, valid) │                 │ (row → text conversion)     │  ║ │
│  ║  └─────────────────┘                 └──────────────┬──────────────┘  ║ │
│  ║                                                      │                 ║ │
│  ║  ┌─────────────────┐                 ┌─────────────────────────────┐  ║ │
│  ║  │silver_inventory │ ─────────────▶ │ silver_inventory_text       │  ║ │
│  ║  │ (current state) │                 │ (snapshot text)             │  ║ │
│  ║  └─────────────────┘                 └──────────────┬──────────────┘  ║ │
│  ║                                                      │                 ║ │
│  ║  ┌─────────────────┐                 ┌─────────────────────────────┐  ║ │
│  ║  │ silver_sales    │ ─────────────▶ │ silver_sales_text           │  ║ │
│  ║  │ (transactions)  │                 │ (sales records text)        │  ║ │
│  ║  └─────────────────┘                 └──────────────┬──────────────┘  ║ │
│  ║                                                      │                 ║ │
│  ║                                                      │ CDF Enabled     ║ │
│  ╚══════════════════════════════════════════════════════╪═════════════════╝ │
│              │                                          │                   │
│              ▼                                          ▼                   │
│  ╔═══════════════════════════════════════════════════════════════════════╗ │
│  ║                    GOLD LAYER (Aggregations)                           ║ │
│  ╠═══════════════════════════════════════════════════════════════════════╣ │
│  ║                                                                        ║ │
│  ║  AGGREGATED TABLES                   SUMMARY TEXT REPRESENTATIONS     ║ │
│  ║  ┌─────────────────────┐             ┌─────────────────────────────┐  ║ │
│  ║  │gold_inventory_summary│ ─────────▶│silver_category_summary_text │  ║ │
│  ║  │(by category, region) │            │(aggregated insights text)   │  ║ │
│  ║  └─────────────────────┘             └──────────────┬──────────────┘  ║ │
│  ║                                                      │                 ║ │
│  ║  ┌─────────────────────┐             ┌─────────────────────────────┐  ║ │
│  ║  │gold_sales_monthly   │ ─────────▶│silver_trend_summary_text    │  ║ │
│  ║  │(monthly trends)     │            │(historical trends text)     │  ║ │
│  ║  └─────────────────────┘             └──────────────┬──────────────┘  ║ │
│  ║                                                      │                 ║ │
│  ║  ┌─────────────────────┐             ┌─────────────────────────────┐  ║ │
│  ║  │gold_product_perf    │ ─────────▶│silver_product_perf_text     │  ║ │
│  ║  │(product performance)│            │(product insights text)      │  ║ │
│  ║  └─────────────────────┘             └──────────────┬──────────────┘  ║ │
│  ║                                                      │ CDF Enabled     ║ │
│  ╚══════════════════════════════════════════════════════╪═════════════════╝ │
│                                                         │                   │
│                    ┌────────────────────────────────────┘                   │
│                    │                                                        │
│                    ▼                                                        │
│  ╔═══════════════════════════════════════════════════════════════════════╗ │
│  ║                    VECTOR SEARCH LAYER                                 ║ │
│  ╠═══════════════════════════════════════════════════════════════════════╣ │
│  ║                                                                        ║ │
│  ║  ┌───────────────────────────┐  ┌───────────────────────────┐        ║ │
│  ║  │  INDEX: product_details   │  │  INDEX: inventory_status  │        ║ │
│  ║  │  Source: product_text     │  │  Source: inventory_text   │        ║ │
│  ║  │  Use: Product questions   │  │  Use: Stock questions     │        ║ │
│  ║  └───────────────────────────┘  └───────────────────────────┘        ║ │
│  ║                                                                        ║ │
│  ║  ┌───────────────────────────┐  ┌───────────────────────────┐        ║ │
│  ║  │  INDEX: sales_records     │  │  INDEX: executive_summary │        ║ │
│  ║  │  Source: sales_text       │  │  Source: *_summary_text   │        ║ │
│  ║  │  Use: Sales questions     │  │  Use: High-level insights │        ║ │
│  ║  └───────────────────────────┘  └───────────────────────────┘        ║ │
│  ║                                                                        ║ │
│  ╚═══════════════════════════════════════════════════════════════════════╝ │
│                                          │                                  │
│                                          ▼                                  │
│  ╔═══════════════════════════════════════════════════════════════════════╗ │
│  ║                    AI AGENT LAYER                                      ║ │
│  ╠═══════════════════════════════════════════════════════════════════════╣ │
│  ║                                                                        ║ │
│  ║  ┌─────────────────────────────────────────────────────────────────┐  ║ │
│  ║  │                    STIHL INVENTORY AGENT                         │  ║ │
│  ║  │                                                                   │  ║ │
│  ║  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │  ║ │
│  ║  │  │   Query     │  │   Vector    │  │    LLM      │              │  ║ │
│  ║  │  │   Router    │─▶│   Search    │─▶│  Generator  │              │  ║ │
│  ║  │  │             │  │  (Retrieval)│  │  (Response) │              │  ║ │
│  ║  │  └─────────────┘  └─────────────┘  └─────────────┘              │  ║ │
│  ║  │                                                                   │  ║ │
│  ║  │  Routes to appropriate index based on query type                 │  ║ │
│  ║  └─────────────────────────────────────────────────────────────────┘  ║ │
│  ║                                                                        ║ │
│  ╚═══════════════════════════════════════════════════════════════════════╝ │
│                                          │                                  │
│                                          ▼                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         USER INTERFACES                              │   │
│  │                                                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │   │
│  │  │ AI         │  │ Slack Bot   │  │ REST API    │  │ Power BI   │ │   │
│  │  │ Playground │  │             │  │             │  │ Copilot    │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2.2 Why This Architecture?

| Design Choice | Rationale |
|---------------|-----------|
| **Text representations in Silver** | Follows Medallion semantics - transformations belong in Silver |
| **Summary text from Gold** | Aggregations computed in Gold, then converted to text in Silver for embedding |
| **Multiple Vector Indexes** | Different query patterns need different data granularity |
| **Query Router** | Directs questions to the most relevant index |
| **Semantic search over SQL** | More natural for business users, handles complex questions better |

---

# 3. Data Model Design

## 3.1 Bronze Layer (Raw Ingestion)

### bronze_products
```sql
CREATE TABLE stihl.bronze.products (
    ingestion_date DATE,
    raw_data STRING,  -- JSON from ERP
    source_system STRING,
    ingestion_timestamp TIMESTAMP
);
```

### bronze_inventory
```sql
CREATE TABLE stihl.bronze.inventory (
    ingestion_date DATE,
    raw_data STRING,  -- JSON from WMS
    source_system STRING,
    ingestion_timestamp TIMESTAMP
);
```

### bronze_sales
```sql
CREATE TABLE stihl.bronze.sales (
    ingestion_date DATE,
    raw_data STRING,  -- JSON from POS
    source_system STRING,
    ingestion_timestamp TIMESTAMP
);
```

## 3.2 Silver Layer (Cleaned + Text Representations)

### silver_products (Cleaned)
```sql
CREATE TABLE stihl.silver.products (
    product_id STRING PRIMARY KEY,
    model_number STRING,
    product_name STRING,
    category STRING,           -- Chainsaws, Trimmers, Blowers, etc.
    subcategory STRING,        -- Gas, Battery, Electric
    power_type STRING,         -- Gas, Battery, Electric, Manual
    user_segment STRING,       -- Homeowner, Professional
    engine_displacement_cc DECIMAL(5,1),
    bar_length_inches DECIMAL(4,1),
    weight_lbs DECIMAL(5,2),
    msrp DECIMAL(10,2),
    cost DECIMAL(10,2),
    margin_pct DECIMAL(5,2),
    description STRING,
    features ARRAY<STRING>,
    is_active BOOLEAN,
    launch_date DATE,
    updated_at TIMESTAMP
);
```

### silver_inventory_current (Current Snapshot)
```sql
CREATE TABLE stihl.silver.inventory_current (
    snapshot_date DATE,
    product_id STRING,
    total_on_hand INT,
    total_in_transit INT,
    total_reserved INT,
    total_available INT,       -- on_hand - reserved
    reorder_point INT,
    is_low_stock BOOLEAN,      -- available < reorder_point
    days_of_supply INT,        -- based on avg daily sales
    updated_at TIMESTAMP,
    CONSTRAINT pk PRIMARY KEY (snapshot_date, product_id)
);
```

### silver_sales (Transactions)
```sql
CREATE TABLE stihl.silver.sales (
    sale_id STRING PRIMARY KEY,
    sale_date DATE,
    product_id STRING,
    units_sold INT,
    revenue DECIMAL(12,2),
    region STRING,
    channel STRING,            -- Retail, Pro Dealer, Online
    updated_at TIMESTAMP
);
```

### silver_product_text (Text Representation for Embedding)
```sql
CREATE TABLE stihl.silver.product_text (
    text_id STRING PRIMARY KEY,
    product_id STRING,
    text_type STRING,          -- 'product_detail'
    text_content STRING,       -- Natural language description
    metadata MAP<STRING, STRING>,
    created_at TIMESTAMP
)
TBLPROPERTIES (delta.enableChangeDataFeed = true);
```

**Example text_content:**
```
Product: MS 271 Farm Boss
Model Number: MS 271
Category: Chainsaws > Gas Chainsaws
Power Type: Gas
User Segment: Professional
Specifications: 50.2cc engine, 20-inch bar, 12.3 lbs
Price: MSRP $429.99, Cost $215.00, Margin 50%
Description: The Farm Boss MS 271 is a powerful mid-range chainsaw 
designed for demanding cutting tasks. Features include IntelliCarb 
compensating carburetor and side-access chain tensioner.
Status: Active, Launched 2019-03-15
```

### silver_inventory_text (Inventory Status Text)
```sql
CREATE TABLE stihl.silver.inventory_text (
    text_id STRING PRIMARY KEY,
    product_id STRING,
    snapshot_date DATE,
    text_type STRING,          -- 'inventory_status'
    text_content STRING,
    metadata MAP<STRING, STRING>,
    created_at TIMESTAMP
)
TBLPROPERTIES (delta.enableChangeDataFeed = true);
```

**Example text_content:**
```
Inventory Status for MS 271 Farm Boss as of 2024-12-15:
Total On Hand: 375 units across all warehouses
In Transit: 150 units arriving within 7 days
Reserved: 45 units for pending orders
Available for Sale: 330 units
Reorder Point: 200 units
Stock Status: HEALTHY (165% of reorder point)
Days of Supply: 23 days based on current sales velocity
30-Day Sales: 432 units
Trend: Stock levels are adequate for projected demand.
```

### silver_sales_text (Sales Records Text)
```sql
CREATE TABLE stihl.silver.sales_text (
    text_id STRING PRIMARY KEY,
    product_id STRING,
    period STRING,             -- 'monthly', 'quarterly'
    period_start DATE,
    period_end DATE,
    text_type STRING,          -- 'sales_record'
    text_content STRING,
    metadata MAP<STRING, STRING>,
    created_at TIMESTAMP
)
TBLPROPERTIES (delta.enableChangeDataFeed = true);
```

**Example text_content (Monthly):**
```
Sales Record for MS 271 Farm Boss - November 2024:
Units Sold: 1,247 units
Revenue: $535,753
Average Selling Price: $429.99
Sales by Region:
  - East: 412 units ($177,156)
  - Central: 389 units ($167,266)
  - West: 298 units ($128,137)
  - South: 148 units ($63,194)
Sales by Channel:
  - Retail: 748 units (60%)
  - Pro Dealer: 374 units (30%)
  - Online: 125 units (10%)
Month-over-Month Change: +8.3% units, +7.9% revenue
Year-over-Year Change: +12.1% units, +15.2% revenue
```

## 3.3 Gold Layer (Aggregations)

### gold_category_summary
```sql
CREATE TABLE stihl.gold.category_summary (
    snapshot_date DATE,
    category STRING,
    subcategory STRING,
    total_products INT,
    active_products INT,
    total_inventory_units INT,
    total_inventory_value DECIMAL(15,2),
    low_stock_products INT,
    avg_days_of_supply DECIMAL(5,1),
    mtd_units_sold INT,
    mtd_revenue DECIMAL(15,2),
    ytd_units_sold INT,
    ytd_revenue DECIMAL(15,2),
    updated_at TIMESTAMP
);
```

### gold_product_performance
```sql
CREATE TABLE stihl.gold.product_performance (
    product_id STRING,
    model_number STRING,
    product_name STRING,
    category STRING,
    -- Current State
    current_inventory INT,
    current_stock_status STRING,
    -- Sales Performance
    last_30_days_units INT,
    last_30_days_revenue DECIMAL(12,2),
    last_90_days_units INT,
    last_90_days_revenue DECIMAL(12,2),
    last_12_months_units INT,
    last_12_months_revenue DECIMAL(12,2),
    last_24_months_units INT,
    last_24_months_revenue DECIMAL(12,2),
    -- Trends
    mom_growth_pct DECIMAL(5,2),
    yoy_growth_pct DECIMAL(5,2),
    -- Profitability
    total_margin_dollars DECIMAL(12,2),
    margin_pct DECIMAL(5,2),
    -- Ranking
    category_rank INT,
    overall_rank INT,
    -- Recommendations
    performance_tier STRING,   -- 'Star', 'Cash Cow', 'Question Mark', 'Dog'
    recommendation STRING,     -- 'Invest', 'Maintain', 'Harvest', 'Divest'
    updated_at TIMESTAMP
);
```

### gold_monthly_trends
```sql
CREATE TABLE stihl.gold.monthly_trends (
    year_month STRING,         -- '2024-11'
    category STRING,
    total_units_sold INT,
    total_revenue DECIMAL(15,2),
    total_margin DECIMAL(15,2),
    avg_inventory_units INT,
    inventory_turnover DECIMAL(5,2),
    top_product_id STRING,
    top_product_name STRING,
    yoy_growth_pct DECIMAL(5,2),
    updated_at TIMESTAMP
);
```

## 3.4 Silver Layer (Summary Text from Gold)

### silver_category_summary_text
```sql
CREATE TABLE stihl.silver.category_summary_text (
    text_id STRING PRIMARY KEY,
    category STRING,
    snapshot_date DATE,
    text_type STRING,          -- 'category_summary'
    text_content STRING,
    metadata MAP<STRING, STRING>,
    created_at TIMESTAMP
)
TBLPROPERTIES (delta.enableChangeDataFeed = true);
```

**Example text_content:**
```
Category Summary: Chainsaws as of 2024-12-15

Product Portfolio:
- Total Products: 24 models (18 active, 6 discontinued)
- Power Types: 12 Gas, 8 Battery, 4 Electric
- User Segments: 10 Professional, 14 Homeowner

Inventory Status:
- Total Units: 8,450 units valued at $2.8M
- Low Stock Alert: 3 products below reorder point
- Average Days of Supply: 28 days

Sales Performance (Current Month):
- Units Sold: 2,847
- Revenue: $1.12M
- Month-over-Month: +5.2%
- Year-over-Year: +11.8%

Top Performer: MS 271 Farm Boss (412 units, $177K)
Needs Attention: MSA 220 C-B (low stock, high demand)

Key Insight: Battery chainsaw sales growing 23% YoY, 
outpacing gas chainsaws (+8% YoY). Consider increasing 
battery inventory allocation.
```

### silver_trend_summary_text
```sql
CREATE TABLE stihl.silver.trend_summary_text (
    text_id STRING PRIMARY KEY,
    period STRING,             -- 'Q4-2024', '2024', 'Last24Months'
    category STRING,           -- NULL for company-wide
    text_type STRING,          -- 'trend_summary'
    text_content STRING,
    metadata MAP<STRING, STRING>,
    created_at TIMESTAMP
)
TBLPROPERTIES (delta.enableChangeDataFeed = true);
```

**Example text_content (Company-wide Last 24 Months):**
```
STIHL Performance Summary: Last 24 Months (Dec 2022 - Nov 2024)

Overall Performance:
- Total Revenue: $487M (+14.2% vs prior 24 months)
- Total Units Sold: 1.24M units (+11.8%)
- Gross Margin: $195M (40.1%)

Category Breakdown:
1. Chainsaws: $156M revenue, 32% of total, +9.2% growth
2. Trimmers: $112M revenue, 23% of total, +18.4% growth
3. Blowers: $89M revenue, 18% of total, +22.1% growth
4. Hedge Trimmers: $58M revenue, 12% of total, +8.7% growth
5. Other: $72M revenue, 15% of total, +12.3% growth

Power Type Trends:
- Battery Products: +34% growth (fastest growing)
- Gas Products: +6% growth (stable)
- Electric Products: -3% growth (declining)

Top 5 Revenue Products (24 months):
1. MS 271 Farm Boss - $28.4M (Chainsaw, Gas)
2. FS 56 RC-E - $19.2M (Trimmer, Gas)
3. BGA 86 - $17.8M (Blower, Battery)
4. MS 250 - $15.9M (Chainsaw, Gas)
5. FSA 57 - $14.2M (Trimmer, Battery)

Products to Watch (Poor Performance):
- MS 170: -18% YoY, low margin, consider phase-out
- HS 45: -12% YoY, replaced by battery models
- BG 50: -22% YoY, outdated design

Recommendation: Shift inventory investment toward battery 
products. The battery segment shows consistent 30%+ growth 
while providing similar margins to gas products.
```

### silver_product_performance_text
```sql
CREATE TABLE stihl.silver.product_performance_text (
    text_id STRING PRIMARY KEY,
    product_id STRING,
    text_type STRING,          -- 'product_performance'
    text_content STRING,
    metadata MAP<STRING, STRING>,
    created_at TIMESTAMP
)
TBLPROPERTIES (delta.enableChangeDataFeed = true);
```

**Example text_content:**
```
Product Performance Analysis: MS 271 Farm Boss

Product Details:
- Category: Chainsaws > Gas Chainsaws
- User Segment: Professional
- MSRP: $429.99, Margin: 50%
- Launch Date: March 2019

Current Inventory:
- On Hand: 375 units
- Stock Status: Healthy
- Days of Supply: 23 days

Sales Performance:
- Last 30 Days: 432 units, $185,756 revenue
- Last 90 Days: 1,247 units, $536,256 revenue
- Last 12 Months: 14,892 units, $6.4M revenue
- Last 24 Months: 28,456 units, $12.2M revenue

Growth Trends:
- Month-over-Month: +8.3%
- Year-over-Year: +12.1%
- 2-Year CAGR: +11.4%

Profitability:
- 24-Month Gross Margin: $6.1M
- Margin Contribution: 3.1% of company total

Performance Tier: STAR
- High growth, high market share
- Recommendation: INVEST
- Continue marketing support, maintain inventory levels,
  consider premium accessories bundle

Rank: #1 in Chainsaws, #3 Overall
```

---

# 4. Embedding Strategy for Tabular Data

## 4.1 The Challenge

Tabular data doesn't naturally fit embedding models designed for text. We need to convert structured rows into meaningful text representations.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TABULAR → TEXT → EMBEDDING FLOW                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ORIGINAL TABLE ROW                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ product_id | model    | category  | price  | inventory | 30d_sales │   │
│  │ P001       | MS 271   | Chainsaws | 429.99 | 375       | 432       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  TEXT REPRESENTATION (Template-based conversion)                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ "Product MS 271 Farm Boss is a gas chainsaw in the professional     │   │
│  │  segment. Price $429.99 with 50% margin. Current inventory 375      │   │
│  │  units, stock status healthy. Last 30 days: 432 units sold,         │   │
│  │  revenue $185,756. Performance tier: Star product, ranked #1        │   │
│  │  in chainsaws category. Recommendation: Continue investment."       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  EMBEDDING VECTOR                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ [0.123, -0.456, 0.789, ..., 0.234]  (1024 dimensions)               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  WHY THIS WORKS:                                                             │
│  • Embedding model understands "chainsaw", "professional", "low stock"      │
│  • Semantic similarity: "low inventory" ≈ "needs restocking"               │
│  • Query "products running low" finds rows mentioning stock issues          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 4.2 Two-Level Embedding Strategy

### Level 1: Row-Level (Detailed Queries)

| Table | Text Type | Use Case |
|-------|-----------|----------|
| silver_product_text | Product details | "Tell me about MS 271" |
| silver_inventory_text | Current stock status | "What products are low on stock?" |
| silver_sales_text | Sales transactions | "Best selling battery products" |

### Level 2: Aggregated (Executive Queries)

| Table | Text Type | Use Case |
|-------|-----------|----------|
| silver_category_summary_text | Category insights | "How is the chainsaw category doing?" |
| silver_trend_summary_text | Historical trends | "What's our 24-month performance?" |
| silver_product_performance_text | Product deep-dive | "Which products should we discontinue?" |

## 4.3 Text Template Design

### Product Detail Template
```python
PRODUCT_TEMPLATE = """
Product: {product_name}
Model Number: {model_number}
Category: {category} > {subcategory}
Power Type: {power_type}
User Segment: {user_segment}
Specifications: {engine_cc}cc engine, {bar_length}-inch bar, {weight} lbs
Price: MSRP ${msrp}, Cost ${cost}, Margin {margin_pct}%
Description: {description}
Features: {features}
Status: {'Active' if is_active else 'Discontinued'}, Launched {launch_date}
"""
```

### Inventory Status Template
```python
INVENTORY_TEMPLATE = """
Inventory Status for {product_name} as of {snapshot_date}:
Total On Hand: {on_hand} units
In Transit: {in_transit} units
Reserved: {reserved} units
Available for Sale: {available} units
Reorder Point: {reorder_point} units
Stock Status: {stock_status} ({pct_of_reorder}% of reorder point)
Days of Supply: {days_of_supply} days
30-Day Sales Velocity: {sales_velocity} units/day
Alert: {alert_message}
"""
```

### Sales Summary Template
```python
SALES_TEMPLATE = """
Sales Record for {product_name} - {period}:
Units Sold: {units} units
Revenue: ${revenue:,.2f}
Average Selling Price: ${asp:,.2f}

Sales by Region:
{region_breakdown}

Sales by Channel:
{channel_breakdown}

Period-over-Period Change: {pop_change}
Year-over-Year Change: {yoy_change}
"""
```

## 4.4 Vector Index Configuration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    VECTOR INDEX STRATEGY                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  INDEX 1: stihl_product_details                                             │
│  ═══════════════════════════════                                            │
│  Source: silver_product_text                                                │
│  Records: ~500 (one per product)                                            │
│  Queries: Product specs, features, pricing                                  │
│  Example: "Which chainsaws have more than 50cc engine?"                    │
│                                                                              │
│  INDEX 2: stihl_inventory_status                                            │
│  ═══════════════════════════════                                            │
│  Source: silver_inventory_text                                              │
│  Records: ~500 (one per product, daily refresh)                            │
│  Queries: Stock levels, availability, restocking                           │
│  Example: "What products are low on stock?"                                │
│                                                                              │
│  INDEX 3: stihl_sales_monthly                                               │
│  ═══════════════════════════════                                            │
│  Source: silver_sales_text                                                  │
│  Records: ~6,000 (500 products × 12 months)                                │
│  Queries: Sales performance, trends, comparisons                           │
│  Example: "What were the best selling battery products in Q4?"            │
│                                                                              │
│  INDEX 4: stihl_executive_insights                                          │
│  ═════════════════════════════════                                          │
│  Source: category_summary_text + trend_summary_text + product_perf_text    │
│  Records: ~100 (categories + periods + top products)                       │
│  Queries: High-level summaries, strategic questions                        │
│  Example: "Give me a summary of company performance"                       │
│  Example: "What products should we discontinue?"                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# 5. Pipeline Design

## 5.1 Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PIPELINE ORCHESTRATION                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  DAILY PIPELINE (Runs at 2 AM)                                              │
│  ═════════════════════════════                                              │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                      │   │
│  │  Step 1: Bronze Ingestion                                           │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐                       │   │
│  │  │ Ingest    │  │ Ingest    │  │ Ingest    │                       │   │
│  │  │ Products  │  │ Inventory │  │ Sales     │                       │   │
│  │  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘                       │   │
│  │        │              │              │                              │   │
│  │        └──────────────┼──────────────┘                              │   │
│  │                       ▼                                              │   │
│  │  Step 2: Silver Transformation                                      │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐                       │   │
│  │  │ Clean     │  │ Clean     │  │ Clean     │                       │   │
│  │  │ Products  │  │ Inventory │  │ Sales     │                       │   │
│  │  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘                       │   │
│  │        │              │              │                              │   │
│  │        └──────────────┼──────────────┘                              │   │
│  │                       ▼                                              │   │
│  │  Step 3: Gold Aggregation                                           │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │   │
│  │  │ Category      │  │ Product       │  │ Monthly       │           │   │
│  │  │ Summary       │  │ Performance   │  │ Trends        │           │   │
│  │  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘           │   │
│  │          │                  │                  │                    │   │
│  │          └──────────────────┼──────────────────┘                    │   │
│  │                             ▼                                        │   │
│  │  Step 4: Text Generation (For AI)                                   │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │   │
│  │  │ Product Text  │  │ Inventory     │  │ Summary Text  │           │   │
│  │  │ Generation    │  │ Text Gen      │  │ Generation    │           │   │
│  │  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘           │   │
│  │          │                  │                  │                    │   │
│  │          └──────────────────┼──────────────────┘                    │   │
│  │                             ▼                                        │   │
│  │  Step 5: Vector Index Sync                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ Trigger sync on all Vector Search indexes                   │   │   │
│  │  │ (CDF automatically captures changes)                        │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  MONTHLY PIPELINE (Runs 1st of month at 4 AM)                              │
│  ════════════════════════════════════════════                              │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  • Regenerate 24-month trend summaries                             │   │
│  │  • Update product performance tiers                                 │   │
│  │  • Generate executive summary for previous month                   │   │
│  │  • Archive old text representations (keep last 13 months)          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 5.2 Notebook Structure

```
stihl_inventory_ai/
├── 01_setup/
│   ├── 01_unity_catalog_setup.sql       # Create catalog, schema, tables
│   └── 02_vector_search_setup.py        # Create endpoints and indexes
│
├── 02_bronze/
│   ├── 01_ingest_products.py            # Load product master data
│   ├── 02_ingest_inventory.py           # Load daily inventory snapshot
│   └── 03_ingest_sales.py               # Load daily sales transactions
│
├── 03_silver/
│   ├── 01_clean_products.py             # Dedupe, validate products
│   ├── 02_clean_inventory.py            # Process inventory snapshot
│   ├── 03_clean_sales.py                # Aggregate daily sales
│   ├── 04_generate_product_text.py      # Convert products to text
│   ├── 05_generate_inventory_text.py    # Convert inventory to text
│   └── 06_generate_sales_text.py        # Convert sales to text
│
├── 04_gold/
│   ├── 01_category_summary.py           # Aggregate by category
│   ├── 02_product_performance.py        # Calculate product metrics
│   └── 03_monthly_trends.py             # Calculate trends
│
├── 05_gold_to_silver_text/
│   ├── 01_category_summary_text.py      # Generate category summaries
│   ├── 02_trend_summary_text.py         # Generate trend narratives
│   └── 03_product_performance_text.py   # Generate product insights
│
├── 06_vector_search/
│   ├── 01_sync_indexes.py               # Trigger index sync
│   └── 02_test_search.py                # Validate search quality
│
├── 07_agent/
│   ├── 01_build_agent.py                # Create RAG agent
│   ├── 02_deploy_agent.py               # Deploy to Model Serving
│   └── 03_evaluate_agent.py             # Quality evaluation
│
├── 08_sample_data/
│   └── generate_sample_data.py          # Create realistic test data
│
└── workflows/
    ├── daily_pipeline.yml               # Databricks Workflow definition
    └── monthly_pipeline.yml
```

---

# 6. Implementation Notebooks

## Notebook Structure for This Project

The notebooks will be implemented in the following order:

| # | Notebook | Purpose |
|---|----------|---------|
| 01 | unity_catalog_setup.sql | Create all tables |
| 02 | generate_sample_data.py | Create realistic STIHL data |
| 03 | silver_text_generation.py | Convert tables to text |
| 04 | gold_aggregations.py | Calculate summaries |
| 05 | gold_to_silver_text.py | Generate insight narratives |
| 06 | vector_search_setup.py | Create indexes |
| 07 | stihl_agent.py | Build and deploy agent |
| 08 | agent_evaluation.py | Test with sample queries |

---

# 7. Agent Design

## 7.1 Multi-Index Query Router

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AGENT QUERY ROUTING                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  USER QUERY                                                                  │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    QUERY CLASSIFIER                                  │   │
│  │                                                                      │   │
│  │  Analyzes query to determine:                                       │   │
│  │  • Query type (detail, status, trend, executive)                   │   │
│  │  • Time frame (current, historical, trend)                         │   │
│  │  • Entity focus (product, category, company)                       │   │
│  │                                                                      │   │
│  └──────────────────────────┬──────────────────────────────────────────┘   │
│                             │                                               │
│           ┌─────────────────┼─────────────────┐                            │
│           │                 │                 │                            │
│           ▼                 ▼                 ▼                            │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐              │
│  │ PRODUCT         │ │ OPERATIONAL     │ │ EXECUTIVE       │              │
│  │ QUERIES         │ │ QUERIES         │ │ QUERIES         │              │
│  │                 │ │                 │ │                 │              │
│  │ • Product specs │ │ • Stock levels  │ │ • Summaries     │              │
│  │ • Features      │ │ • Low inventory │ │ • Trends        │              │
│  │ • Pricing       │ │ • Sales data    │ │ • Recommendations│             │
│  │                 │ │                 │ │                 │              │
│  │ Index:          │ │ Index:          │ │ Index:          │              │
│  │ product_details │ │ inventory +     │ │ executive_      │              │
│  │                 │ │ sales_monthly   │ │ insights        │              │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘              │
│           │                 │                 │                            │
│           └─────────────────┼─────────────────┘                            │
│                             │                                               │
│                             ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    CONTEXT BUILDER                                   │   │
│  │                                                                      │   │
│  │  Combines retrieved chunks into coherent context                    │   │
│  │  May query multiple indexes for complex questions                   │   │
│  │                                                                      │   │
│  └──────────────────────────┬──────────────────────────────────────────┘   │
│                             │                                               │
│                             ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    LLM RESPONSE GENERATOR                            │   │
│  │                                                                      │   │
│  │  Prompt: "You are a STIHL inventory analyst. Use the following      │   │
│  │  context to answer the question. Include specific numbers and       │   │
│  │  actionable insights."                                               │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 7.2 Query Classification Rules

| Query Pattern | Classification | Index(es) to Search |
|--------------|----------------|---------------------|
| "Tell me about [product]" | Product Detail | product_details |
| "What are the specs of" | Product Detail | product_details |
| "Which products are low on stock" | Operational | inventory_status |
| "Inventory turnover for" | Operational | inventory_status + sales |
| "Best selling in [period]" | Operational | sales_monthly |
| "Compare [X] vs [Y]" | Operational | Multiple |
| "Summary of [category/company]" | Executive | executive_insights |
| "Trends over [period]" | Executive | executive_insights |
| "What should we discontinue" | Executive | executive_insights |
| "Company performance" | Executive | executive_insights |

---

# 8. Sample Queries by Persona

## Supply Chain Manager

| Query | Index | Expected Context |
|-------|-------|------------------|
| "Which products are low on stock?" | inventory_status | Products with is_low_stock = true |
| "What's our inventory turnover for chainsaws?" | inventory + sales | Category summary with turnover calc |
| "Which products need restocking urgently?" | inventory_status | Low stock + high velocity products |

## Sales Director

| Query | Index | Expected Context |
|-------|-------|------------------|
| "What are the best-selling battery products in Q4?" | sales_monthly | Q4 sales filtered by power_type |
| "Compare trimmer sales across regions" | sales_monthly | Regional breakdown for trimmers |
| "Which channel is growing fastest?" | executive_insights | Channel trend analysis |

## Product Manager

| Query | Index | Expected Context |
|-------|-------|------------------|
| "Which chainsaw models have highest margins?" | product_details | Products sorted by margin_pct |
| "What professional products need restocking?" | inventory_status | Low stock + user_segment=Professional |
| "How is the MS 271 performing?" | executive_insights | Product performance text |

## Executive

| Query | Index | Expected Context |
|-------|-------|------------------|
| "Give me a summary of current company progress" | executive_insights | Trend summary (company-wide) |
| "What products bring most revenue?" | executive_insights | Top products from trend summary |
| "What products should we discontinue?" | executive_insights | Products with 'Dog' tier + 'Divest' rec |
| "How does battery vs gas compare?" | executive_insights | Power type trend comparison |

---

# Summary

## Architecture Decisions Recap

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Text tables location | Silver layer | Transformations, not aggregations |
| Embedding granularity | Two levels (row + summary) | Different query needs |
| Number of indexes | 4 specialized indexes | Better search precision |
| Query approach | Semantic search + routing | Natural language, flexible |
| Sync mode | Triggered (daily) | Cost-effective for batch updates |

## Key Files to Create

1. **SQL**: Table definitions for all layers
2. **Python**: Sample data generation
3. **Python**: Text generation from tables
4. **Python**: Vector Search setup
5. **Python**: Agent implementation
6. **YAML**: Workflow orchestration

Ready to implement the notebooks?
