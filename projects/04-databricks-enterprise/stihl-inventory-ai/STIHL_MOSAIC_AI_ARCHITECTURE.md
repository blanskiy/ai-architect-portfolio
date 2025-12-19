# STIHL Inventory AI - Mosaic AI Architecture

## Executive Summary

This document describes the architecture for STIHL's inventory analytics system using Databricks Mosaic AI. The system enables natural language queries against tabular inventory, sales, and product data through Vector Search and RAG (Retrieval Augmented Generation).

**Key Capabilities:**
- Natural language queries for inventory, sales, and product data
- Automatic query classification and routing
- Multiple specialized indexes for different query types
- Differential sync strategy based on data volatility

---

## Catalog Configuration

**Catalog:** `ai_systems` (existing Unity Catalog)

**Schemas:**
| Schema | Purpose |
|--------|---------|
| `ai_systems.stihl_bronze` | Raw data ingestion layer |
| `ai_systems.stihl_silver` | Cleaned data + text representations |
| `ai_systems.stihl_gold` | Aggregated business metrics |

---

## Architecture Overview

```
+------------------+     +------------------+     +------------------+
|   SOURCE SYSTEMS |     |    DATABRICKS    |     |   AI AGENT       |
+------------------+     +------------------+     +------------------+
                         |                  |
  ERP (Products) ------->| Bronze Layer     |
  WMS (Inventory) ------>|   raw_*          |
  POS (Sales) ---------->|                  |
                         |        |         |
                         |        v         |
                         | Silver Layer     |     +------------------+
                         |   dim_products   |     | Query Classifier |
                         |   fact_inventory |---->|        |         |
                         |   fact_sales     |     |        v         |
                         |   *_text tables  |     | Vector Search    |
                         |        |         |     |   4 Indexes      |
                         |        v         |     |        |         |
                         | Gold Layer       |     |        v         |
                         |   category_*     |     | LLM Generation   |
                         |   product_perf   |     |        |         |
                         |   monthly_trends |     |        v         |
                         +------------------+     |   Response       |
                                                  +------------------+
```

---

## Data Model

### Bronze Layer (`ai_systems.stihl_bronze`)

Raw data as received from source systems.

| Table | Source | Update Frequency |
|-------|--------|------------------|
| `raw_products` | ERP | Daily |
| `raw_inventory` | WMS | Daily |
| `raw_sales` | POS | Daily |

### Silver Layer (`ai_systems.stihl_silver`)

#### Dimensional Tables

| Table | Description | Key Columns |
|-------|-------------|-------------|
| `dim_products` | Product master (SCD Type 2) | product_id, model_number, category, power_type, specs, pricing |
| `fact_inventory_current` | Daily inventory snapshot | snapshot_date, product_id, on_hand, available, days_of_supply |
| `fact_sales` | Sales transactions | sale_id, sale_date, product_id, units_sold, revenue, region, channel |

#### Text Tables for Vector Search

| Table | Content | Sync Frequency | Index |
|-------|---------|----------------|-------|
| `product_details_text` | Specs, features, description (NO price) | Weekly | product_details_index |
| `inventory_status_text` | Pricing + stock levels + alerts | Daily | inventory_status_index |
| `sales_summary_text` | Monthly sales by product | Daily | sales_summary_index |
| `executive_insights_text` | Category summaries, trends, recommendations | Daily | executive_insights_index |

### Gold Layer (`ai_systems.stihl_gold`)

| Table | Description | Grain |
|-------|-------------|-------|
| `category_summary` | Category-level KPIs | Category x Date |
| `product_performance` | Product rankings, BCG classification | Product x Date |
| `monthly_trends` | Historical trend analysis | Month x Category |

---

## Vector Search Strategy

### Indexes

| Index | Source Table | Embedding Column | Sync Mode | Schedule |
|-------|--------------|------------------|-----------|----------|
| `product_details_index` | product_details_text | text_content | TRIGGERED | Weekly (Sunday 2AM) |
| `inventory_status_index` | inventory_status_text | text_content | TRIGGERED | Daily (3AM) |
| `sales_summary_index` | sales_summary_text | text_content | TRIGGERED | Daily (4AM) |
| `executive_insights_index` | executive_insights_text | text_content | TRIGGERED | Daily (5AM) |

### Why Differential Sync?

**Problem:** Original design would reindex all product data daily, wasting compute on static specs just because price changed.

**Solution:** Split static vs dynamic attributes across different indexes with different sync frequencies.

| Data Type | Change Frequency | Index | Sync |
|-----------|------------------|-------|------|
| Product specs, features | Rarely | product_details_index | Weekly |
| Pricing | Weekly/Monthly | inventory_status_index | Daily |
| Stock levels | Daily | inventory_status_index | Daily |
| Sales data | Daily | sales_summary_index | Daily |
| Summaries | Daily | executive_insights_index | Daily |

**Critical Decision:** Price lives in `inventory_status_text` (daily sync), NOT in `product_details_text` (weekly sync).

### Endpoint Configuration

```
Endpoint: stihl_inventory_endpoint
Type: STANDARD
Embedding Model: databricks-gte-large-en (1024 dimensions)
```

---

## Query Classification & Routing

### Automatic Classification

The agent automatically classifies queries using keyword patterns and routes to the appropriate index.

| Query Pattern | Index | Examples |
|---------------|-------|----------|
| Product specs/features | product_details_index | "What chainsaws have 50cc+ engine?" |
| Price/margin/stock | inventory_status_index | "Which products are low on stock?" |
| Sales performance | sales_summary_index | "Best selling battery products in Q4?" |
| Strategic/summary | executive_insights_index | "Company performance summary" |

### Classification Keywords

**Product Details:**
- specs, specifications, features, description
- engine, cc, bar length, weight
- what is, tell me about, describe

**Inventory Status:**
- stock, inventory, available, reorder
- price, pricing, cost, margin, msrp
- low stock, out of stock, days of supply

**Sales Performance:**
- sales, sold, revenue, best seller
- growth, yoy, mom, quarter
- region, channel, compare

**Executive Insights:**
- summary, overview, executive
- recommend, invest, discontinue
- strategy, overall, company

---

## Text Generation Templates

### Product Details Text (Weekly Sync)

```
Product: {product_name}
Model Number: {model_number}
Category: {category} > {subcategory}
Power Type: {power_type}
Target User: {user_segment}
Specifications: Engine: {cc}cc, Bar: {bar_length} inches, Weight: {weight} lbs
Description: {description}
Key Features: {features}
Product Status: {is_active}
Launch Date: {launch_date}
```

### Inventory Status Text (Daily Sync)

```
{product_name} ({model_number}) - Inventory & Pricing Status
Category: {category}
Snapshot Date: {snapshot_date}

CURRENT PRICING:
- MSRP: ${msrp}
- Cost: ${cost}
- Margin: {margin_pct}%

INVENTORY LEVELS:
- On Hand: {on_hand} units
- In Transit: {in_transit} units
- Available for Sale: {available} units

STOCK STATUS: {status}
- Reorder Point: {reorder_point} units
- Days of Supply: {days_of_supply} days
- Sales Velocity: {velocity} units/day

ALERT: {alert_message}
```

### Sales Summary Text (Daily Sync)

```
Sales Record: {product_name} ({model_number})
Category: {category}
Period: {year_month}

SALES PERFORMANCE:
- Units Sold: {units}
- Revenue: ${revenue}
- Gross Margin: ${margin}

REGIONAL BREAKDOWN:
- East: {east_units} units (${east_rev})
- Central: {central_units} units (${central_rev})
- West: {west_units} units (${west_rev})
- South: {south_units} units (${south_rev})

CHANNEL MIX:
- Retail: {retail_pct}%
- Pro Dealer: {pro_pct}%
- Online: {online_pct}%

GROWTH:
- Month-over-Month: {mom}%
- Year-over-Year: {yoy}%
```

---

## Personas Served

### Supply Chain Manager
**Typical Questions:**
- "Which products are low on stock?"
- "What's our days of supply for chainsaws?"
- "Which products need restocking urgently?"

**Primary Index:** inventory_status_index

### Sales Director
**Typical Questions:**
- "What are the best-selling battery products?"
- "Compare trimmer sales across regions"
- "What's our YoY growth by category?"

**Primary Index:** sales_summary_index

### Product Manager
**Typical Questions:**
- "Which products have the highest margins?"
- "Tell me about the MS 271 specifications"
- "Compare battery vs gas chainsaw features"

**Primary Indexes:** inventory_status_index, product_details_index

### Executive
**Typical Questions:**
- "Give me a company performance summary"
- "What products should we discontinue?"
- "What should we invest in?"

**Primary Index:** executive_insights_index

---

## BCG Matrix Classification

Products are classified into four quadrants based on growth and market position:

| Classification | Criteria | Recommendation |
|----------------|----------|----------------|
| **Star** | High growth + Top 3 in category | Invest |
| **Cash Cow** | Low growth + Top 3 in category | Maintain |
| **Question Mark** | High growth + Lower rank | Evaluate |
| **Dog** | Low growth + Lower rank | Divest |

---

## Workflow Orchestration

### Daily Pipeline (2 AM)
1. Ingest raw data from source systems
2. Transform to Silver layer
3. Generate text representations
4. Build Gold aggregations
5. Sync daily indexes (inventory, sales, executive)
6. Run quality checks

### Weekly Pipeline (Sunday 2 AM)
1. Refresh product text representations
2. Sync product_details_index
3. Verify index health

### Monthly Pipeline (1st of month, 4 AM)
1. Run full evaluation suite
2. Generate performance report
3. Archive evaluation metrics

---

## File Structure

```
stihl_inventory_ai/
├── STIHL_MOSAIC_AI_ARCHITECTURE.md
├── notebooks/
│   ├── 01_unity_catalog_setup.sql
│   ├── 02_generate_sample_data.py
│   ├── 03_text_generation.py
│   ├── 04_gold_aggregations.py
│   ├── 05_vector_search_setup.py
│   ├── 06_stihl_agent.py
│   └── 07_agent_evaluation.py
└── workflows/
    └── workflow_definitions.py
```

---

## Implementation Notes

### Change Data Feed (CDF)
All text tables have CDF enabled for efficient Vector Search sync:
```sql
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
```

### Partitioning Strategy
- `fact_inventory_current`: Partitioned by `snapshot_date`
- `fact_sales`: Partitioned by `sale_date`
- `inventory_status_text`: Partitioned by `snapshot_date`

### Auto-Optimization
All tables use Delta auto-optimization:
```sql
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
)
```

---

## Cost Optimization

| Optimization | Benefit |
|--------------|---------|
| Weekly sync for product_details | 87% reduction in sync compute |
| TRIGGERED vs CONTINUOUS mode | Pay only for batch updates |
| Staggered sync times | Avoid compute spikes |
| Specialized indexes | Better retrieval precision |

---

## Next Steps

1. **Deploy to Production**
   - Import notebooks to Databricks workspace
   - Configure workflows with actual cluster IDs
   - Set up alerting and monitoring

2. **Integration**
   - Connect to actual ERP/WMS/POS systems
   - Replace sample data with real data feeds

3. **Enhancement**
   - Add hybrid search (vector + metadata filters)
   - Implement conversation memory
   - Add more sophisticated query routing

4. **Monitoring**
   - Track query latency and accuracy
   - Monitor index freshness
   - Alert on sync failures
