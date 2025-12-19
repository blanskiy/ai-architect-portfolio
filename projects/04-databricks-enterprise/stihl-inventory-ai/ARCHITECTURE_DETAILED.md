# STIHL Inventory AI - Data Architecture & Dependencies

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           STIHL INVENTORY AI SYSTEM                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │   SOURCE    │    │   BRONZE    │    │   SILVER    │    │    GOLD     │      │
│  │   SYSTEMS   │───▶│   (Raw)     │───▶│ (Processed) │───▶│(Aggregated) │      │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘      │
│                                               │                                 │
│                                               ▼                                 │
│                                    ┌─────────────────────┐                      │
│                                    │    TEXT TABLES      │                      │
│                                    │  (AI-Ready Format)  │                      │
│                                    └──────────┬──────────┘                      │
│                                               │                                 │
│                                               ▼                                 │
│                                    ┌─────────────────────┐                      │
│                                    │   VECTOR SEARCH     │                      │
│                                    │      INDEXES        │                      │
│                                    └──────────┬──────────┘                      │
│                                               │                                 │
│                                               ▼                                 │
│                                    ┌─────────────────────┐                      │
│                                    │    RAG AGENT        │                      │
│                                    │   (LLM + Retrieval) │                      │
│                                    └─────────────────────┘                      │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 2. Catalog & Schema Structure

```
ai_systems (Unity Catalog)
│
├── stihl_bronze/          ← Raw ingested data
│   ├── raw_products
│   ├── raw_inventory
│   └── raw_sales
│
├── stihl_silver/          ← Processed + AI-ready tables
│   ├── dim_products           (dimension table)
│   ├── fact_inventory_current (fact table)
│   ├── fact_sales             (fact table)
│   │
│   ├── product_details_text      ──▶ product_details_index
│   ├── inventory_status_text     ──▶ inventory_status_index
│   ├── sales_summary_text        ──▶ sales_summary_index
│   └── executive_insights_text   ──▶ executive_insights_index
│
└── stihl_gold/            ← Business aggregations
    ├── category_summary
    ├── product_performance
    └── monthly_trends
```

## 3. Table Structures & Dependencies

### BRONZE LAYER (Raw Data)

```sql
-- raw_products: Product master data from ERP
┌────────────────────────────────────────────────────────────┐
│ raw_products                                               │
├────────────────────────────────────────────────────────────┤
│ product_id        STRING (PK)                              │
│ product_name      STRING                                   │
│ model_number      STRING                                   │
│ category          STRING      (Chainsaws, Trimmers, etc.)  │
│ subcategory       STRING                                   │
│ power_type        STRING      (Gas, Battery, Electric)     │
│ engine_cc         DOUBLE                                   │
│ bar_length        DOUBLE                                   │
│ voltage           DOUBLE                                   │
│ weight_lbs        DOUBLE                                   │
│ msrp              DOUBLE                                   │
│ cost              DOUBLE                                   │
│ launch_date       DATE                                     │
│ is_active         BOOLEAN                                  │
│ ingested_at       TIMESTAMP                                │
└────────────────────────────────────────────────────────────┘
         │
         │ Dependency: Source system extract (daily)
         ▼

-- raw_inventory: Warehouse stock levels
┌────────────────────────────────────────────────────────────┐
│ raw_inventory                                              │
├────────────────────────────────────────────────────────────┤
│ inventory_id      STRING (PK)                              │
│ product_id        STRING (FK → raw_products)               │
│ warehouse_id      STRING                                   │
│ quantity_on_hand  INT                                      │
│ quantity_reserved INT                                      │
│ reorder_point     INT                                      │
│ snapshot_date     DATE                                     │
│ ingested_at       TIMESTAMP                                │
└────────────────────────────────────────────────────────────┘
         │
         │ Dependency: Warehouse management system (daily)
         ▼

-- raw_sales: Transaction history
┌────────────────────────────────────────────────────────────┐
│ raw_sales                                                  │
├────────────────────────────────────────────────────────────┤
│ sale_id           STRING (PK)                              │
│ product_id        STRING (FK → raw_products)               │
│ sale_date         DATE                                     │
│ units_sold        INT                                      │
│ unit_price        DOUBLE                                   │
│ channel           STRING      (Dealer, Online, Direct)     │
│ region            STRING                                   │
│ ingested_at       TIMESTAMP                                │
└────────────────────────────────────────────────────────────┘
```

### SILVER LAYER (Processed Data)

```sql
-- dim_products: Cleansed product dimension
┌────────────────────────────────────────────────────────────┐
│ dim_products                                               │
├────────────────────────────────────────────────────────────┤
│ product_id        STRING (PK)                              │
│ product_name      STRING                                   │
│ model_number      STRING                                   │
│ category          STRING                                   │
│ subcategory       STRING                                   │
│ power_type        STRING                                   │
│ user_segment      STRING      (Homeowner, Farm, Pro)       │
│ engine_displacement_cc  DOUBLE                             │
│ bar_length_inches      DOUBLE                              │
│ battery_voltage        DOUBLE                              │
│ weight_lbs             DOUBLE                              │
│ msrp                   DOUBLE                              │
│ dealer_cost            DOUBLE                              │
│ margin_pct             DOUBLE   (calculated)               │
│ launch_date            DATE                                │
│ discontinue_date       DATE                                │
│ is_active              BOOLEAN                             │
│ updated_at             TIMESTAMP                           │
└────────────────────────────────────────────────────────────┘
         │
         │ Source: raw_products (transformed)
         │ Refresh: Daily
         ▼

-- fact_inventory_current: Current stock snapshot
┌────────────────────────────────────────────────────────────┐
│ fact_inventory_current                                     │
├────────────────────────────────────────────────────────────┤
│ product_id            STRING (PK, FK → dim_products)       │
│ total_on_hand         INT                                  │
│ total_reserved        INT                                  │
│ total_available       INT        (calculated)              │
│ total_reorder_point   INT                                  │
│ days_of_supply        DOUBLE     (calculated)              │
│ is_low_stock          BOOLEAN    (available < reorder)     │
│ is_out_of_stock       BOOLEAN    (available = 0)           │
│ warehouse_count       INT                                  │
│ snapshot_date         DATE                                 │
│ updated_at            TIMESTAMP                            │
└────────────────────────────────────────────────────────────┘
         │
         │ Source: raw_inventory (aggregated by product)
         │ Refresh: Daily
         ▼

-- fact_sales: Historical sales transactions
┌────────────────────────────────────────────────────────────┐
│ fact_sales                                                 │
├────────────────────────────────────────────────────────────┤
│ sale_id               STRING (PK)                          │
│ product_id            STRING (FK → dim_products)           │
│ sale_date             DATE                                 │
│ year_month            STRING     (YYYY-MM)                 │
│ units_sold            INT                                  │
│ revenue               DOUBLE                               │
│ cost_of_goods         DOUBLE                               │
│ gross_margin          DOUBLE     (calculated)              │
│ channel               STRING                               │
│ region                STRING                               │
│ updated_at            TIMESTAMP                            │
└────────────────────────────────────────────────────────────┘
```

### TEXT TABLES (AI-Ready Format)

These tables convert structured data into natural language for vector embedding.

```sql
-- product_details_text: Product info as searchable text
┌────────────────────────────────────────────────────────────┐
│ product_details_text                                       │
├────────────────────────────────────────────────────────────┤
│ text_id         STRING (PK)    "product_{product_id}"      │
│ product_id      STRING (FK)                                │
│ text_content    STRING         ← NATURAL LANGUAGE TEXT     │
│ text_generated_at TIMESTAMP                                │
└────────────────────────────────────────────────────────────┘

Example text_content:
"The MS 271 Farm Boss is a Gas-powered Chainsaw in the Farm & Ranch 
segment. It features a 50.2cc engine displacement with an 18-inch 
bar length, weighing 12.3 lbs. Current MSRP is $429.99 with a dealer 
margin of 28.5%. The product launched on 2019-03-15 and is currently 
active in the catalog."

-- inventory_status_text: Current stock as searchable text
┌────────────────────────────────────────────────────────────┐
│ inventory_status_text                                      │
├────────────────────────────────────────────────────────────┤
│ text_id         STRING (PK)    "inv_{product_id}"          │
│ product_id      STRING (FK)                                │
│ text_content    STRING         ← NATURAL LANGUAGE TEXT     │
│ snapshot_date   DATE                                       │
│ text_generated_at TIMESTAMP                                │
└────────────────────────────────────────────────────────────┘

Example text_content:
"INVENTORY STATUS for MS 271 Farm Boss (Chainsaw):
Current Stock: 145 units available across 5 warehouses.
Stock Status: HEALTHY - 45 days of supply.
Reorder Point: 50 units. No immediate restocking needed.
Current MSRP: $429.99, Dealer Cost: $307.14, Margin: 28.5%"

-- sales_summary_text: Monthly sales as searchable text
┌────────────────────────────────────────────────────────────┐
│ sales_summary_text                                         │
├────────────────────────────────────────────────────────────┤
│ text_id         STRING (PK)    "sales_{product}_{month}"   │
│ product_id      STRING (FK)                                │
│ year_month      STRING                                     │
│ text_content    STRING         ← NATURAL LANGUAGE TEXT     │
│ text_generated_at TIMESTAMP                                │
└────────────────────────────────────────────────────────────┘

Example text_content:
"SALES PERFORMANCE for MS 271 Farm Boss - November 2024:
Units Sold: 234 (YoY: +12.5%)
Revenue: $100,517 (YoY: +15.2%)
Gross Margin: $28,647 (28.5% margin rate)
Top Channel: Dealer (78%), Top Region: Midwest (35%)
Trend: Strong growth, outperforming category average."

-- executive_insights_text: Aggregated summaries for strategy
┌────────────────────────────────────────────────────────────┐
│ executive_insights_text                                    │
├────────────────────────────────────────────────────────────┤
│ text_id         STRING (PK)    "exec_{type}_{category}"    │
│ insight_type    STRING         (category, trend, product)  │
│ category        STRING                                     │
│ text_content    STRING         ← NATURAL LANGUAGE TEXT     │
│ period_start    DATE                                       │
│ period_end      DATE                                       │
│ text_generated_at TIMESTAMP                                │
└────────────────────────────────────────────────────────────┘

Example text_content:
"EXECUTIVE SUMMARY - Chainsaws Category (Last 24 Months):
Total Revenue: $12.4M | Growth: +8.2% YoY
Top Performer: MS 271 Farm Boss ($2.1M revenue)
Underperformer: MS 170 (-15% YoY, consider phase-out)
Inventory Health: 92% in-stock rate
RECOMMENDATION: Increase MS 271 inventory by 20% for Q2 season."
```

### GOLD LAYER (Business Aggregations)

```sql
-- category_summary: Category-level KPIs
┌────────────────────────────────────────────────────────────┐
│ category_summary                                           │
├────────────────────────────────────────────────────────────┤
│ category            STRING (PK)                            │
│ subcategory         STRING (PK)                            │
│ total_products      INT                                    │
│ active_products     INT                                    │
│ total_inventory     INT                                    │
│ inventory_value     DOUBLE                                 │
│ low_stock_count     INT                                    │
│ mtd_revenue         DOUBLE                                 │
│ ytd_revenue         DOUBLE                                 │
│ avg_margin_pct      DOUBLE                                 │
│ mom_growth_pct      DOUBLE                                 │
│ yoy_growth_pct      DOUBLE                                 │
│ updated_at          TIMESTAMP                              │
└────────────────────────────────────────────────────────────┘

-- product_performance: Product-level analytics
┌────────────────────────────────────────────────────────────┐
│ product_performance                                        │
├────────────────────────────────────────────────────────────┤
│ product_id          STRING (PK)                            │
│ product_name        STRING                                 │
│ category            STRING                                 │
│ l30_units_sold      INT        (last 30 days)              │
│ l30_revenue         DOUBLE                                 │
│ l90_units_sold      INT        (last 90 days)              │
│ l90_revenue         DOUBLE                                 │
│ ytd_units_sold      INT                                    │
│ ytd_revenue         DOUBLE                                 │
│ current_inventory   INT                                    │
│ days_of_supply      DOUBLE                                 │
│ velocity_rank       INT        (within category)           │
│ margin_rank         INT        (within category)           │
│ updated_at          TIMESTAMP                              │
└────────────────────────────────────────────────────────────┘

-- monthly_trends: Time-series for trending
┌────────────────────────────────────────────────────────────┐
│ monthly_trends                                             │
├────────────────────────────────────────────────────────────┤
│ year_month          STRING (PK)                            │
│ category            STRING (PK)                            │
│ total_units_sold    BIGINT                                 │
│ total_revenue       DOUBLE                                 │
│ total_margin        DOUBLE                                 │
│ margin_pct          DOUBLE                                 │
│ inventory_value     DOUBLE                                 │
│ inventory_turnover  DOUBLE                                 │
│ mom_growth_pct      DOUBLE                                 │
│ yoy_growth_pct      DOUBLE                                 │
│ top_product_id      STRING                                 │
│ top_product_name    STRING                                 │
│ updated_at          TIMESTAMP                              │
└────────────────────────────────────────────────────────────┘
```

## 4. Vector Search Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VECTOR SEARCH ENDPOINT                              │
│                      stihl_inventory_endpoint                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    EMBEDDING MODEL                                   │   │
│  │              databricks-gte-large-en (1024 dims)                    │   │
│  │                                                                      │   │
│  │    text_content → [0.12, -0.45, 0.78, ..., 0.33] (1024 floats)     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│         ┌──────────────────────────┼──────────────────────────┐            │
│         ▼                          ▼                          ▼            │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐        │
│  │ product_details │    │inventory_status │    │  sales_summary  │        │
│  │     _index      │    │     _index      │    │     _index      │        │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────────┤        │
│  │ 61 vectors      │    │ 61 vectors      │    │ 1,204 vectors   │        │
│  │ Sync: WEEKLY    │    │ Sync: DAILY     │    │ Sync: DAILY     │        │
│  │ Source: product_│    │ Source: inv_    │    │ Source: sales_  │        │
│  │ details_text    │    │ status_text     │    │ summary_text    │        │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘        │
│                                                                             │
│                          ┌─────────────────┐                               │
│                          │executive_insight│                               │
│                          │     _index      │                               │
│                          ├─────────────────┤                               │
│                          │ 54 vectors      │                               │
│                          │ Sync: DAILY     │                               │
│                          │ Source: exec_   │                               │
│                          │ insights_text   │                               │
│                          └─────────────────┘                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Index Configuration

| Index | Source Table | Primary Key | Embedding Column | Sync Mode | Use Case |
|-------|--------------|-------------|------------------|-----------|----------|
| product_details_index | product_details_text | text_id | text_content | TRIGGERED (Weekly) | Product specs, features |
| inventory_status_index | inventory_status_text | text_id | text_content | TRIGGERED (Daily) | Stock levels, pricing |
| sales_summary_index | sales_summary_text | text_id | text_content | TRIGGERED (Daily) | Sales performance |
| executive_insights_index | executive_insights_text | text_id | text_content | TRIGGERED (Daily) | Strategic summaries |

### How Vector Search Works

```
User Query: "What chainsaws have 50cc engines?"
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. EMBED QUERY                                                  │
│    "What chainsaws have 50cc engines?"                          │
│              ↓                                                  │
│    [0.15, -0.32, 0.67, ..., 0.21]  (1024-dim vector)           │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. SIMILARITY SEARCH                                            │
│    Compare query vector against all vectors in index            │
│    Using cosine similarity                                      │
│                                                                 │
│    Query ──┬── Doc1: 0.89 similarity (MS 271, 50.2cc) ✓        │
│            ├── Doc2: 0.85 similarity (MS 261, 50.2cc) ✓        │
│            ├── Doc3: 0.72 similarity (MS 500i, 79.2cc)         │
│            └── Doc4: 0.45 similarity (FSA 130, battery)        │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. RETURN TOP-K RESULTS                                         │
│    [                                                            │
│      {"text_id": "product_ms271", "score": 0.89, ...},         │
│      {"text_id": "product_ms261", "score": 0.85, ...},         │
│      {"text_id": "product_ms500i", "score": 0.72, ...}         │
│    ]                                                            │
└─────────────────────────────────────────────────────────────────┘
```

## 5. Complete Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                              STIHL INVENTORY AI - DATA FLOW                              │
└──────────────────────────────────────────────────────────────────────────────────────────┘

SOURCE SYSTEMS                    BRONZE                    SILVER                    
━━━━━━━━━━━━━━                    ━━━━━━                    ━━━━━━                    
                                                                                       
┌──────────┐                   ┌─────────────┐           ┌─────────────────┐          
│   ERP    │──── Extract ────▶│ raw_products│─── ETL ──▶│  dim_products   │          
│ (SAP)    │     (Daily)      └─────────────┘           └────────┬────────┘          
└──────────┘                                                     │                    
                                                                 │                    
┌──────────┐                   ┌─────────────┐           ┌───────▼─────────┐          
│Warehouse │──── Extract ────▶│raw_inventory│─── ETL ──▶│fact_inventory_  │          
│  (WMS)   │     (Daily)      └─────────────┘           │    current      │          
└──────────┘                                            └────────┬────────┘          
                                                                 │                    
┌──────────┐                   ┌─────────────┐           ┌───────▼─────────┐          
│  POS/    │──── Extract ────▶│  raw_sales  │─── ETL ──▶│   fact_sales    │          
│  Orders  │     (Daily)      └─────────────┘           └────────┬────────┘          
└──────────┘                                                     │                    
                                                                 │                    
                                                                 │                    
                    TEXT GENERATION                              │                    
                    ━━━━━━━━━━━━━━━                              │                    
                                                                 ▼                    
                              ┌─────────────────────────────────────────────┐        
                              │          TEXT GENERATION (UDFs)             │        
                              │                                             │        
                              │  dim_products ──────▶ product_details_text  │        
                              │  fact_inventory ────▶ inventory_status_text │        
                              │  fact_sales ────────▶ sales_summary_text    │        
                              │  gold tables ───────▶ executive_insights    │        
                              └──────────────────────────┬──────────────────┘        
                                                         │                            
                                                         ▼                            
                    VECTOR INDEXING                                                   
                    ━━━━━━━━━━━━━━━                                                   
                              ┌─────────────────────────────────────────────┐        
                              │        VECTOR SEARCH ENDPOINT               │        
                              │       stihl_inventory_endpoint              │        
                              │                                             │        
                              │  ┌───────────────┐   ┌───────────────┐     │        
                              │  │ product_      │   │ inventory_    │     │        
                              │  │ details_index │   │ status_index  │     │        
                              │  └───────────────┘   └───────────────┘     │        
                              │                                             │        
                              │  ┌───────────────┐   ┌───────────────┐     │        
                              │  │ sales_        │   │ executive_    │     │        
                              │  │ summary_index │   │ insights_index│     │        
                              │  └───────────────┘   └───────────────┘     │        
                              └──────────────────────────┬──────────────────┘        
                                                         │                            
                                                         ▼                            
                    RAG AGENT                                                         
                    ━━━━━━━━━                                                         
                              ┌─────────────────────────────────────────────┐        
                              │           STIHL INVENTORY AGENT             │        
                              │                                             │        
                              │  ┌─────────────┐     ┌─────────────┐       │        
                              │  │   Query     │────▶│  Classify   │       │        
                              │  │   Input     │     │   Query     │       │        
                              │  └─────────────┘     └──────┬──────┘       │        
                              │                             │              │        
                              │                             ▼              │        
                              │                      ┌─────────────┐       │        
                              │                      │  Retrieve   │       │        
                              │                      │  from Index │       │        
                              │                      └──────┬──────┘       │        
                              │                             │              │        
                              │                             ▼              │        
                              │  ┌─────────────┐     ┌─────────────┐       │        
                              │  │  Response   │◀────│  LLM Call   │       │        
                              │  │   Output    │     │ (Llama 3.3) │       │        
                              │  └─────────────┘     └─────────────┘       │        
                              └─────────────────────────────────────────────┘        


GOLD LAYER (Business Reporting)                                                       
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                                       
                                                                                       
        ┌─────────────┐         ┌─────────────┐         ┌─────────────┐              
        │  category_  │         │  product_   │         │  monthly_   │              
        │  summary    │         │ performance │         │   trends    │              
        └─────────────┘         └─────────────┘         └─────────────┘              
              │                       │                       │                       
              └───────────────────────┼───────────────────────┘                       
                                      │                                               
                                      ▼                                               
                            ┌─────────────────┐                                       
                            │    DASHBOARDS   │                                       
                            │    (BI Tools)   │                                       
                            └─────────────────┘                                       
```

## 6. Refresh Schedule & Dependencies

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            DAILY REFRESH WORKFLOW (3 AM)                            │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  Step 1: Bronze Ingestion                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                            │
│  │raw_products │    │raw_inventory│    │ raw_sales   │                            │
│  │  (refresh)  │    │  (refresh)  │    │  (refresh)  │                            │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                            │
│         │                  │                  │                                     │
│         └──────────────────┼──────────────────┘                                     │
│                            ▼                                                        │
│  Step 2: Silver Processing (depends on Bronze)                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                            │
│  │dim_products │    │fact_inv_curr│    │ fact_sales  │                            │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                            │
│         │                  │                  │                                     │
│         └──────────────────┼──────────────────┘                                     │
│                            ▼                                                        │
│  Step 3: Text Generation (depends on Silver)                                       │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │product_text │    │  inv_text   │    │ sales_text  │    │ exec_text   │         │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘         │
│         │                  │                  │                  │                  │
│         └──────────────────┼──────────────────┼──────────────────┘                  │
│                            ▼                  ▼                                     │
│  Step 4: Vector Index Sync (depends on Text tables)                                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                            │
│  │inv_idx.sync │    │sales_idx    │    │exec_idx     │                            │
│  │             │    │  .sync()    │    │  .sync()    │                            │
│  └─────────────┘    └─────────────┘    └─────────────┘                            │
│                                                                                     │
│  Step 5: Gold Aggregations (depends on Silver)                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                            │
│  │category_sum │    │product_perf │    │monthly_trend│                            │
│  └─────────────┘    └─────────────┘    └─────────────┘                            │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           WEEKLY REFRESH (Sunday 2 AM)                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  Product Details Index Sync                                                         │
│  (Product specs rarely change, weekly is sufficient)                               │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │  product_details_index.sync()                                               │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## 7. Query Classification → Index Routing

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              QUERY ROUTING LOGIC                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  USER QUERY                                                                         │
│      │                                                                              │
│      ▼                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                        QUERY CLASSIFIER                                      │   │
│  │                                                                              │   │
│  │   Keywords Detected              →  Query Type        →  Index              │   │
│  │   ─────────────────────────────────────────────────────────────────────     │   │
│  │   spec, feature, model, cc,      →  PRODUCT_DETAIL   →  product_details    │   │
│  │   engine, bar length, weight                                                 │   │
│  │                                                                              │   │
│  │   stock, inventory, price,       →  INVENTORY_STATUS →  inventory_status   │   │
│  │   available, low stock, reorder                                              │   │
│  │                                                                              │   │
│  │   sales, sold, revenue, Q1-Q4,   →  SALES_PERFORMANCE → sales_summary      │   │
│  │   growth, YoY, trend, compare                                                │   │
│  │                                                                              │   │
│  │   summary, recommend, strategy,  →  EXECUTIVE_INSIGHT → executive_insights │   │
│  │   discontinue, invest, overview                                              │   │
│  │                                                                              │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
│  EXAMPLES:                                                                          │
│                                                                                     │
│  "What are the specs of MS 271?"           → product_details_index                 │
│  "Which products are low on stock?"        → inventory_status_index                │
│  "Best selling battery products in Q4?"    → sales_summary_index                   │
│  "Give me a company performance summary"   → executive_insights_index              │
│  "What products should we discontinue?"    → executive_insights_index              │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## 8. Component Costs (Approximate)

| Component | Type | Cost | Notes |
|-----------|------|------|-------|
| Vector Search Endpoint | Compute | ~$0.50/hour | Always-on for queries |
| Embedding Model | API | Included | databricks-gte-large-en |
| LLM Endpoint | API | ~$0.001/query | Pay-per-use |
| Spark Cluster | Compute | ~$0.10-0.50/hour | Only during ETL jobs |
| Delta Storage | Storage | ~$0.02/GB/month | Very low cost |

## 9. Key Dependencies Summary

```
DEPENDENCY CHAIN:
━━━━━━━━━━━━━━━━━

Source Systems
     │
     ▼
Bronze Tables (raw_*)
     │
     ▼
Silver Tables (dim_*, fact_*)  ←── Required for AI
     │
     ├────────────────────────┐
     ▼                        ▼
Text Tables (*_text)     Gold Tables (aggregations)
     │                        │
     ▼                        ▼
Vector Indexes (*_index)  Dashboards
     │
     ▼
RAG Agent
     │
     ▼
User Queries
```

**Critical Path for AI:**
1. Silver tables must be populated → Text tables depend on them
2. Text tables must exist → Vector indexes read from them
3. Vector indexes must be synced → Agent searches them
4. LLM endpoint must be available → Agent generates responses
