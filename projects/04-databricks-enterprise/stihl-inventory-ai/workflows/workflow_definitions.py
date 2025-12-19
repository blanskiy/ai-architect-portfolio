# Databricks Workflow Definitions
# ================================
# These YAML files define the orchestration workflows for the STIHL Inventory AI system.
# Import these into Databricks Workflows UI or use the Databricks CLI.
#
# Catalog: ai_systems
# Schemas: stihl_bronze, stihl_silver, stihl_gold

# =============================================================================
# WORKFLOW 1: DAILY DATA PIPELINE
# =============================================================================
# Runs daily at 2 AM to refresh inventory, sales, and text representations
# Then syncs Vector Search indexes

"""
name: stihl_daily_pipeline
description: Daily refresh of STIHL inventory data and Vector Search indexes

schedule:
  quartz_cron_expression: "0 0 2 * * ?"  # 2 AM daily
  timezone_id: "America/New_York"
  pause_status: UNPAUSED

tags:
  team: data-engineering
  project: stihl-inventory-ai
  environment: production
  catalog: ai_systems

tasks:
  # Step 1: Ingest raw data from source systems
  - task_key: ingest_bronze
    description: Load raw data from ERP, WMS, POS systems
    notebook_task:
      notebook_path: /Workspace/stihl_inventory_ai/notebooks/02_generate_sample_data
      base_parameters:
        catalog: ai_systems
        schema_bronze: stihl_bronze
        schema_silver: stihl_silver
    cluster_id: ${var.cluster_id}
    timeout_seconds: 1800
    
  # Step 2: Clean and transform to Silver
  - task_key: transform_silver
    description: Clean, dedupe, validate data and generate text representations
    depends_on:
      - task_key: ingest_bronze
    notebook_task:
      notebook_path: /Workspace/stihl_inventory_ai/notebooks/03_text_generation
      base_parameters:
        catalog: ai_systems
        schema_silver: stihl_silver
    cluster_id: ${var.cluster_id}
    timeout_seconds: 3600
    
  # Step 3: Build Gold aggregations
  - task_key: aggregate_gold
    description: Calculate category summaries, product performance, trends
    depends_on:
      - task_key: transform_silver
    notebook_task:
      notebook_path: /Workspace/stihl_inventory_ai/notebooks/04_gold_aggregations
      base_parameters:
        catalog: ai_systems
        schema_silver: stihl_silver
        schema_gold: stihl_gold
    cluster_id: ${var.cluster_id}
    timeout_seconds: 1800
    
  # Step 4: Sync daily Vector Search indexes
  - task_key: sync_inventory_index
    description: Sync inventory status index (includes pricing)
    depends_on:
      - task_key: aggregate_gold
    notebook_task:
      notebook_path: /Workspace/stihl_inventory_ai/notebooks/05_vector_search_setup
      base_parameters:
        action: sync_index
        index: inventory_status
        catalog: ai_systems
        schema: stihl_silver
    cluster_id: ${var.cluster_id}
    timeout_seconds: 900
    
  - task_key: sync_sales_index
    description: Sync sales summary index
    depends_on:
      - task_key: aggregate_gold
    notebook_task:
      notebook_path: /Workspace/stihl_inventory_ai/notebooks/05_vector_search_setup
      base_parameters:
        action: sync_index
        index: sales_summary
        catalog: ai_systems
        schema: stihl_silver
    cluster_id: ${var.cluster_id}
    timeout_seconds: 900
    
  - task_key: sync_executive_index
    description: Sync executive insights index
    depends_on:
      - task_key: aggregate_gold
    notebook_task:
      notebook_path: /Workspace/stihl_inventory_ai/notebooks/05_vector_search_setup
      base_parameters:
        action: sync_index
        index: executive_insights
        catalog: ai_systems
        schema: stihl_silver
    cluster_id: ${var.cluster_id}
    timeout_seconds: 900
    
  # Step 5: Run quality checks
  - task_key: quality_check
    description: Verify data quality and index health
    depends_on:
      - task_key: sync_inventory_index
      - task_key: sync_sales_index
      - task_key: sync_executive_index
    notebook_task:
      notebook_path: /Workspace/stihl_inventory_ai/notebooks/07_agent_evaluation
      base_parameters:
        quick_check: "true"
        catalog: ai_systems
    cluster_id: ${var.cluster_id}
    timeout_seconds: 600

email_notifications:
  on_failure:
    - data-engineering@stihl.com
  on_success: []
  no_alert_for_skipped_runs: true

max_concurrent_runs: 1
"""

# =============================================================================
# WORKFLOW 2: WEEKLY PRODUCT SYNC
# =============================================================================
# Runs weekly on Sunday at 2 AM to sync product details index
# (Product specs rarely change, so weekly is sufficient)

"""
name: stihl_weekly_product_sync
description: Weekly sync of product details Vector Search index

schedule:
  quartz_cron_expression: "0 0 2 ? * SUN"  # Sunday 2 AM
  timezone_id: "America/New_York"
  pause_status: UNPAUSED

tags:
  team: data-engineering
  project: stihl-inventory-ai
  environment: production
  catalog: ai_systems

tasks:
  # Step 1: Refresh product text representations
  - task_key: refresh_product_text
    description: Regenerate product details text from dimension table
    notebook_task:
      notebook_path: /Workspace/stihl_inventory_ai/notebooks/03_text_generation
      base_parameters:
        tables: "product_details_text"
        catalog: ai_systems
        schema_silver: stihl_silver
    cluster_id: ${var.cluster_id}
    timeout_seconds: 1800
    
  # Step 2: Sync product details index
  - task_key: sync_product_index
    description: Sync product details index (specs, features)
    depends_on:
      - task_key: refresh_product_text
    notebook_task:
      notebook_path: /Workspace/stihl_inventory_ai/notebooks/05_vector_search_setup
      base_parameters:
        action: sync_index
        index: product_details
        catalog: ai_systems
        schema: stihl_silver
    cluster_id: ${var.cluster_id}
    timeout_seconds: 900
    
  # Step 3: Verify index health
  - task_key: verify_index
    description: Test search queries against updated index
    depends_on:
      - task_key: sync_product_index
    notebook_task:
      notebook_path: /Workspace/stihl_inventory_ai/notebooks/07_agent_evaluation
      base_parameters:
        quick_check: "true"
        index: "product_details"
        catalog: ai_systems
    cluster_id: ${var.cluster_id}
    timeout_seconds: 300

email_notifications:
  on_failure:
    - data-engineering@stihl.com

max_concurrent_runs: 1
"""

# =============================================================================
# WORKFLOW 3: MONTHLY COMPREHENSIVE EVALUATION
# =============================================================================
# Runs monthly to do full agent evaluation and performance reporting

"""
name: stihl_monthly_evaluation
description: Monthly comprehensive agent evaluation and reporting

schedule:
  quartz_cron_expression: "0 0 4 1 * ?"  # 4 AM on 1st of month
  timezone_id: "America/New_York"
  pause_status: UNPAUSED

tags:
  team: data-engineering
  project: stihl-inventory-ai
  environment: production
  catalog: ai_systems

tasks:
  # Full evaluation suite
  - task_key: full_evaluation
    description: Run complete evaluation test suite
    notebook_task:
      notebook_path: /Workspace/stihl_inventory_ai/notebooks/07_agent_evaluation
      base_parameters:
        full_suite: "true"
        catalog: ai_systems
        schema_silver: stihl_silver
        schema_gold: stihl_gold
    cluster_id: ${var.cluster_id}
    timeout_seconds: 3600
    
  # Generate performance report
  - task_key: generate_report
    description: Create monthly performance summary
    depends_on:
      - task_key: full_evaluation
    notebook_task:
      notebook_path: /Workspace/stihl_inventory_ai/notebooks/08_monthly_report
      base_parameters:
        catalog: ai_systems
    cluster_id: ${var.cluster_id}
    timeout_seconds: 600

email_notifications:
  on_success:
    - analytics-team@stihl.com
  on_failure:
    - data-engineering@stihl.com

max_concurrent_runs: 1
"""

# =============================================================================
# CONFIGURATION SUMMARY
# =============================================================================
"""
CATALOG AND SCHEMA CONFIGURATION
================================

Catalog: ai_systems (existing Unity Catalog)

Schemas:
  - ai_systems.stihl_bronze  : Raw data ingestion layer
  - ai_systems.stihl_silver  : Cleaned data + text representations
  - ai_systems.stihl_gold    : Aggregated business metrics

Tables by Schema:
  
  stihl_bronze:
    - raw_products
    - raw_inventory
    - raw_sales
  
  stihl_silver:
    - dim_products
    - fact_inventory_current
    - fact_sales
    - product_details_text
    - inventory_status_text
    - sales_summary_text
    - category_summary_text
    - trend_summary_text
    - product_performance_text
    - executive_insights_text
  
  stihl_gold:
    - category_summary
    - product_performance
    - monthly_trends
    - agent_evaluation_history

Vector Search:
  - Endpoint: stihl_inventory_endpoint
  - Indexes:
    - ai_systems.stihl_silver.product_details_index
    - ai_systems.stihl_silver.inventory_status_index
    - ai_systems.stihl_silver.sales_summary_index
    - ai_systems.stihl_silver.executive_insights_index
"""

# =============================================================================
# SYNC SCHEDULE SUMMARY
# =============================================================================
"""
INDEX SYNC STRATEGY
===================

Based on data volatility analysis:

+-------------------------+---------------+---------------------------------+
| INDEX                   | SYNC SCHEDULE | RATIONALE                       |
+-------------------------+---------------+---------------------------------+
| product_details_index   | WEEKLY        | Specs/features rarely change    |
|                         | (Sunday 2 AM) | Only new products need sync     |
+-------------------------+---------------+---------------------------------+
| inventory_status_index  | DAILY         | Prices change frequently        |
|                         | (Daily 3 AM)  | Stock levels change daily       |
+-------------------------+---------------+---------------------------------+
| sales_summary_index     | DAILY         | New sales data every day        |
|                         | (Daily 4 AM)  | Monthly aggregates update       |
+-------------------------+---------------+---------------------------------+
| executive_insights_index| DAILY         | Summaries reflect latest data   |
|                         | (Daily 5 AM)  | Recommendations may change      |
+-------------------------+---------------+---------------------------------+

COST OPTIMIZATION:
- Product index syncs 4x/month instead of 30x/month (87% reduction)
- Staggered sync times to avoid compute spikes
- TRIGGERED mode (not CONTINUOUS) for all indexes

DATA FRESHNESS:
- Inventory/pricing: <24 hours old
- Sales data: <24 hours old
- Product specs: <7 days old (acceptable for static data)
"""
