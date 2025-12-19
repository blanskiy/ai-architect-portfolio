-- =============================================================================
-- STIHL INVENTORY AI - UNITY CATALOG SETUP
-- =============================================================================
-- Using existing ai_systems catalog with STIHL-specific schemas
-- 
-- Architecture: Medallion (Bronze -> Silver -> Gold) + Vector Search
-- =============================================================================

-- -----------------------------------------------------------------------------
-- CATALOG AND SCHEMA SETUP
-- -----------------------------------------------------------------------------

-- Use existing catalog (no need to create new one)
USE CATALOG ai_systems;

-- Create schemas for STIHL project within ai_systems
CREATE SCHEMA IF NOT EXISTS stihl_bronze
COMMENT 'Raw data ingestion layer - data as received from source systems';

CREATE SCHEMA IF NOT EXISTS stihl_silver
COMMENT 'Cleaned and transformed data - includes text representations for AI';

CREATE SCHEMA IF NOT EXISTS stihl_gold
COMMENT 'Aggregated business metrics - reports and dashboards';

-- Verify schemas created
SHOW SCHEMAS IN ai_systems LIKE 'stihl*';

-- -----------------------------------------------------------------------------
-- BRONZE LAYER: Raw Data Ingestion
-- -----------------------------------------------------------------------------
-- Purpose: Store raw data exactly as received from source systems
-- Update frequency: Daily batch loads
-- Retention: 90 days (for replay capability)

-- Raw products from ERP system
CREATE TABLE IF NOT EXISTS ai_systems.stihl_bronze.raw_products (
    ingestion_id STRING COMMENT 'Unique identifier for this ingestion batch',
    ingestion_date DATE COMMENT 'Date of data load',
    source_system STRING COMMENT 'Source system identifier (ERP)',
    raw_data STRING COMMENT 'Raw JSON payload from source',
    file_path STRING COMMENT 'Source file location',
    ingestion_timestamp TIMESTAMP COMMENT 'Exact time of ingestion'
)
USING DELTA
COMMENT 'Raw product master data from ERP system'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

-- Raw inventory snapshots from Warehouse Management System
CREATE TABLE IF NOT EXISTS ai_systems.stihl_bronze.raw_inventory (
    ingestion_id STRING,
    ingestion_date DATE,
    source_system STRING,
    raw_data STRING,
    file_path STRING,
    ingestion_timestamp TIMESTAMP
)
USING DELTA
COMMENT 'Raw daily inventory snapshots from WMS';

-- Raw sales transactions from POS/Order systems
CREATE TABLE IF NOT EXISTS ai_systems.stihl_bronze.raw_sales (
    ingestion_id STRING,
    ingestion_date DATE,
    source_system STRING,
    raw_data STRING,
    file_path STRING,
    ingestion_timestamp TIMESTAMP
)
USING DELTA
COMMENT 'Raw daily sales transactions from POS systems';

-- -----------------------------------------------------------------------------
-- SILVER LAYER: Cleaned Dimensional Data
-- -----------------------------------------------------------------------------
-- Purpose: Validated, deduplicated, type-cast data
-- Update frequency: Daily (after bronze load)

-- Products dimension (Slowly Changing Dimension Type 2)
CREATE TABLE IF NOT EXISTS ai_systems.stihl_silver.dim_products (
    product_id STRING NOT NULL COMMENT 'Unique product identifier',
    model_number STRING NOT NULL COMMENT 'STIHL model number (e.g., MS 271)',
    product_name STRING COMMENT 'Product display name (e.g., Farm Boss)',
    category STRING NOT NULL COMMENT 'Primary category (Chainsaws, Trimmers, etc.)',
    subcategory STRING COMMENT 'Subcategory (Gas, Battery, Electric)',
    power_type STRING COMMENT 'Power source: Gas, Battery, Electric, Manual',
    user_segment STRING COMMENT 'Target user: Homeowner, Professional',
    
    -- Specifications (static, rarely change)
    engine_displacement_cc DECIMAL(5,1) COMMENT 'Engine size in cubic centimeters',
    bar_length_inches DECIMAL(4,1) COMMENT 'Guide bar length for chainsaws',
    cutting_width_inches DECIMAL(4,1) COMMENT 'Cutting width for trimmers/mowers',
    weight_lbs DECIMAL(5,2) COMMENT 'Product weight in pounds',
    
    -- Pricing (changes periodically - tracked separately for freshness)
    msrp DECIMAL(10,2) COMMENT 'Manufacturer suggested retail price',
    cost DECIMAL(10,2) COMMENT 'Product cost',
    margin_pct DECIMAL(5,2) COMMENT 'Calculated margin percentage',
    price_effective_date DATE COMMENT 'Date current pricing became effective',
    
    -- Product information
    description STRING COMMENT 'Product description for customers',
    features STRING COMMENT 'Key features as comma-separated list',
    
    -- Lifecycle
    is_active BOOLEAN COMMENT 'Currently sold product',
    launch_date DATE COMMENT 'Product launch date',
    discontinue_date DATE COMMENT 'Discontinuation date if applicable',
    
    -- Metadata
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    
    CONSTRAINT pk_products PRIMARY KEY (product_id)
)
USING DELTA
COMMENT 'Product master data - cleaned and validated'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.enableChangeDataFeed' = 'true'
);

-- Current inventory snapshot (daily)
CREATE TABLE IF NOT EXISTS ai_systems.stihl_silver.fact_inventory_current (
    snapshot_date DATE NOT NULL COMMENT 'Date of inventory snapshot',
    product_id STRING NOT NULL COMMENT 'FK to dim_products',
    
    -- Inventory quantities
    total_on_hand INT COMMENT 'Total units in all warehouses',
    total_in_transit INT COMMENT 'Units currently in transit',
    total_reserved INT COMMENT 'Units reserved for orders',
    total_available INT COMMENT 'Units available for sale (on_hand - reserved)',
    
    -- Inventory health metrics
    reorder_point INT COMMENT 'Minimum stock level before reorder',
    reorder_quantity INT COMMENT 'Standard reorder quantity',
    is_low_stock BOOLEAN COMMENT 'True if available < reorder_point',
    is_out_of_stock BOOLEAN COMMENT 'True if available = 0',
    
    -- Velocity metrics (calculated from recent sales)
    avg_daily_sales DECIMAL(8,2) COMMENT 'Average units sold per day (30-day)',
    days_of_supply INT COMMENT 'Estimated days until stockout',
    
    -- Metadata
    updated_at TIMESTAMP,
    
    CONSTRAINT pk_inventory PRIMARY KEY (snapshot_date, product_id)
)
USING DELTA
PARTITIONED BY (snapshot_date)
COMMENT 'Daily inventory snapshot - current stock levels'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.enableChangeDataFeed' = 'true'
);

-- Sales transactions (append-only fact table)
CREATE TABLE IF NOT EXISTS ai_systems.stihl_silver.fact_sales (
    sale_id STRING NOT NULL COMMENT 'Unique sale transaction ID',
    sale_date DATE NOT NULL COMMENT 'Date of sale',
    product_id STRING NOT NULL COMMENT 'FK to dim_products',
    
    -- Sale details
    units_sold INT NOT NULL COMMENT 'Number of units sold',
    unit_price DECIMAL(10,2) COMMENT 'Actual selling price per unit',
    revenue DECIMAL(12,2) COMMENT 'Total revenue (units * price)',
    cost_of_goods DECIMAL(12,2) COMMENT 'Total COGS',
    gross_margin DECIMAL(12,2) COMMENT 'Revenue - COGS',
    
    -- Dimensions
    region STRING COMMENT 'Sales region: East, Central, West, South',
    channel STRING COMMENT 'Sales channel: Retail, Pro Dealer, Online',
    
    -- Metadata
    created_at TIMESTAMP,
    
    CONSTRAINT pk_sales PRIMARY KEY (sale_id)
)
USING DELTA
PARTITIONED BY (sale_date)
COMMENT 'Daily sales transactions'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.enableChangeDataFeed' = 'true'
);

-- -----------------------------------------------------------------------------
-- SILVER LAYER: Text Representations for AI/Vector Search
-- -----------------------------------------------------------------------------
-- Purpose: Natural language representations of tabular data for embedding
-- These tables feed into Vector Search indexes

-- Product details text (STATIC info - weekly sync)
CREATE TABLE IF NOT EXISTS ai_systems.stihl_silver.product_details_text (
    text_id STRING NOT NULL COMMENT 'Unique text record ID',
    product_id STRING NOT NULL COMMENT 'FK to dim_products',
    
    -- Text content for embedding
    text_content STRING NOT NULL COMMENT 'Natural language product description',
    
    -- Metadata for filtering
    category STRING COMMENT 'Product category for filtering',
    subcategory STRING COMMENT 'Product subcategory for filtering',
    power_type STRING COMMENT 'Power type for filtering',
    user_segment STRING COMMENT 'User segment for filtering',
    is_active BOOLEAN COMMENT 'Active product flag',
    
    -- Change tracking
    source_updated_at TIMESTAMP COMMENT 'When source product was last updated',
    text_generated_at TIMESTAMP COMMENT 'When text was generated',
    
    CONSTRAINT pk_product_text PRIMARY KEY (text_id)
)
USING DELTA
COMMENT 'Product details as natural language text for Vector Search (WEEKLY sync)'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.enableChangeDataFeed' = 'true'
);

-- Inventory status text (DYNAMIC info - daily sync)
-- Includes current pricing since it changes frequently
CREATE TABLE IF NOT EXISTS ai_systems.stihl_silver.inventory_status_text (
    text_id STRING NOT NULL COMMENT 'Unique text record ID',
    product_id STRING NOT NULL COMMENT 'FK to dim_products',
    snapshot_date DATE NOT NULL COMMENT 'Date of inventory snapshot',
    
    -- Text content for embedding
    text_content STRING NOT NULL COMMENT 'Natural language inventory status with pricing',
    
    -- Metadata for filtering
    category STRING COMMENT 'Product category for filtering',
    is_low_stock BOOLEAN COMMENT 'Low stock flag for filtering',
    is_out_of_stock BOOLEAN COMMENT 'Out of stock flag for filtering',
    stock_status STRING COMMENT 'Stock status: Healthy, Low, Critical, Out',
    
    -- Key metrics for hybrid search
    current_msrp DECIMAL(10,2) COMMENT 'Current price',
    current_margin_pct DECIMAL(5,2) COMMENT 'Current margin',
    days_of_supply INT COMMENT 'Days of supply',
    
    -- Change tracking
    text_generated_at TIMESTAMP,
    
    CONSTRAINT pk_inventory_text PRIMARY KEY (text_id)
)
USING DELTA
PARTITIONED BY (snapshot_date)
COMMENT 'Inventory status with pricing as natural language text (DAILY sync)'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.enableChangeDataFeed' = 'true'
);

-- Sales summary text (monthly aggregates - daily sync)
CREATE TABLE IF NOT EXISTS ai_systems.stihl_silver.sales_summary_text (
    text_id STRING NOT NULL COMMENT 'Unique text record ID',
    product_id STRING NOT NULL COMMENT 'FK to dim_products',
    period_type STRING NOT NULL COMMENT 'Period type: monthly, quarterly',
    period_start DATE NOT NULL COMMENT 'Period start date',
    period_end DATE NOT NULL COMMENT 'Period end date',
    
    -- Text content for embedding
    text_content STRING NOT NULL COMMENT 'Natural language sales summary',
    
    -- Metadata for filtering
    category STRING COMMENT 'Product category',
    year_month STRING COMMENT 'Year-month for filtering (YYYY-MM)',
    
    -- Key metrics for hybrid search
    total_units INT COMMENT 'Total units sold in period',
    total_revenue DECIMAL(12,2) COMMENT 'Total revenue in period',
    yoy_growth_pct DECIMAL(5,2) COMMENT 'Year-over-year growth',
    
    -- Change tracking
    text_generated_at TIMESTAMP,
    
    CONSTRAINT pk_sales_text PRIMARY KEY (text_id)
)
USING DELTA
COMMENT 'Sales summaries as natural language text (DAILY sync)'
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.enableChangeDataFeed' = 'true'
);

-- -----------------------------------------------------------------------------
-- GOLD LAYER: Aggregated Business Metrics
-- -----------------------------------------------------------------------------
-- Purpose: Pre-computed aggregations for reports and dashboards
-- Also feeds into executive summary text generation

-- Category-level summary (daily)
CREATE TABLE IF NOT EXISTS ai_systems.stihl_gold.category_summary (
    snapshot_date DATE NOT NULL,
    category STRING NOT NULL,
    subcategory STRING,
    
    -- Product counts
    total_products INT,
    active_products INT,
    discontinued_products INT,
    
    -- Inventory metrics
    total_inventory_units INT,
    total_inventory_value DECIMAL(15,2),
    low_stock_products INT,
    out_of_stock_products INT,
    avg_days_of_supply DECIMAL(5,1),
    
    -- Sales metrics (MTD)
    mtd_units_sold INT,
    mtd_revenue DECIMAL(15,2),
    mtd_margin DECIMAL(15,2),
    
    -- Sales metrics (YTD)
    ytd_units_sold INT,
    ytd_revenue DECIMAL(15,2),
    ytd_margin DECIMAL(15,2),
    
    -- Trends
    mom_revenue_growth_pct DECIMAL(5,2),
    yoy_revenue_growth_pct DECIMAL(5,2),
    
    -- Top performers
    top_product_id STRING,
    top_product_name STRING,
    top_product_revenue DECIMAL(12,2),
    
    -- Metadata
    updated_at TIMESTAMP,
    
    CONSTRAINT pk_category_summary PRIMARY KEY (snapshot_date, category, subcategory)
)
USING DELTA
COMMENT 'Daily category-level performance summary';

-- Product performance analysis (daily)
CREATE TABLE IF NOT EXISTS ai_systems.stihl_gold.product_performance (
    snapshot_date DATE NOT NULL,
    product_id STRING NOT NULL,
    model_number STRING,
    product_name STRING,
    category STRING,
    subcategory STRING,
    power_type STRING,
    user_segment STRING,
    
    -- Current state
    current_msrp DECIMAL(10,2),
    current_margin_pct DECIMAL(5,2),
    current_inventory INT,
    current_stock_status STRING,
    
    -- Sales performance (various windows)
    last_30_days_units INT,
    last_30_days_revenue DECIMAL(12,2),
    last_90_days_units INT,
    last_90_days_revenue DECIMAL(12,2),
    last_12_months_units INT,
    last_12_months_revenue DECIMAL(12,2),
    last_24_months_units INT,
    last_24_months_revenue DECIMAL(12,2),
    
    -- Growth metrics
    mom_growth_pct DECIMAL(5,2),
    qoq_growth_pct DECIMAL(5,2),
    yoy_growth_pct DECIMAL(5,2),
    
    -- Profitability
    last_12_months_margin DECIMAL(12,2),
    margin_contribution_pct DECIMAL(5,2),
    
    -- Rankings
    category_revenue_rank INT,
    category_units_rank INT,
    overall_revenue_rank INT,
    overall_units_rank INT,
    
    -- BCG Matrix style classification
    performance_tier STRING COMMENT 'Star, Cash Cow, Question Mark, Dog',
    recommendation STRING COMMENT 'Invest, Maintain, Harvest, Divest',
    
    -- Metadata
    updated_at TIMESTAMP,
    
    CONSTRAINT pk_product_perf PRIMARY KEY (snapshot_date, product_id)
)
USING DELTA
COMMENT 'Daily product performance analysis with rankings and recommendations';

-- Monthly trends (historical)
CREATE TABLE IF NOT EXISTS ai_systems.stihl_gold.monthly_trends (
    year_month STRING NOT NULL COMMENT 'YYYY-MM format',
    category STRING,  -- NULL for company-wide
    
    -- Volume metrics
    total_units_sold INT,
    unique_products_sold INT,
    
    -- Revenue metrics
    total_revenue DECIMAL(15,2),
    total_cogs DECIMAL(15,2),
    total_margin DECIMAL(15,2),
    margin_pct DECIMAL(5,2),
    
    -- Inventory metrics (month-end)
    month_end_inventory_units INT,
    month_end_inventory_value DECIMAL(15,2),
    inventory_turnover DECIMAL(5,2),
    
    -- Growth metrics
    mom_growth_pct DECIMAL(5,2),
    yoy_growth_pct DECIMAL(5,2),
    
    -- Top performers
    top_product_id STRING,
    top_product_name STRING,
    
    -- Metadata
    updated_at TIMESTAMP,
    
    CONSTRAINT pk_monthly_trends PRIMARY KEY (year_month, category)
)
USING DELTA
COMMENT 'Monthly aggregated trends for historical analysis';

-- -----------------------------------------------------------------------------
-- SILVER LAYER: Executive Summary Text (from Gold aggregations)
-- -----------------------------------------------------------------------------
-- Purpose: High-level insights as text for executive queries
-- Generated from Gold layer aggregations

-- Category summary text
CREATE TABLE IF NOT EXISTS ai_systems.stihl_silver.category_summary_text (
    text_id STRING NOT NULL,
    category STRING NOT NULL,
    snapshot_date DATE NOT NULL,
    
    text_content STRING NOT NULL COMMENT 'Natural language category summary',
    
    -- Metadata for filtering
    has_low_stock_alert BOOLEAN,
    has_growth_opportunity BOOLEAN,
    
    text_generated_at TIMESTAMP,
    
    CONSTRAINT pk_cat_summary_text PRIMARY KEY (text_id)
)
USING DELTA
COMMENT 'Category summaries as natural language for executive queries (DAILY sync)'
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true'
);

-- Trend summary text (company-wide and by category)
CREATE TABLE IF NOT EXISTS ai_systems.stihl_silver.trend_summary_text (
    text_id STRING NOT NULL,
    period_type STRING NOT NULL COMMENT 'quarterly, annual, last_24_months',
    period_label STRING NOT NULL COMMENT 'Q4-2024, 2024, Last 24 Months',
    category STRING COMMENT 'NULL for company-wide',
    
    text_content STRING NOT NULL COMMENT 'Natural language trend summary',
    
    -- Metadata
    period_start DATE,
    period_end DATE,
    
    text_generated_at TIMESTAMP,
    
    CONSTRAINT pk_trend_text PRIMARY KEY (text_id)
)
USING DELTA
COMMENT 'Trend summaries for strategic/executive queries (DAILY sync)'
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true'
);

-- Product performance text (for investment/divestment recommendations)
CREATE TABLE IF NOT EXISTS ai_systems.stihl_silver.product_performance_text (
    text_id STRING NOT NULL,
    product_id STRING NOT NULL,
    snapshot_date DATE NOT NULL,
    
    text_content STRING NOT NULL COMMENT 'Natural language product performance analysis',
    
    -- Metadata for filtering
    category STRING,
    performance_tier STRING,
    recommendation STRING,
    
    text_generated_at TIMESTAMP,
    
    CONSTRAINT pk_prod_perf_text PRIMARY KEY (text_id)
)
USING DELTA
COMMENT 'Product performance insights for strategic queries (DAILY sync)'
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true'
);

-- Executive insights combined (for Vector Search)
CREATE TABLE IF NOT EXISTS ai_systems.stihl_silver.executive_insights_text (
    text_id STRING NOT NULL,
    text_content STRING NOT NULL,
    source_type STRING COMMENT 'category_summary, trend_summary, product_performance',
    category STRING,
    product_id STRING,
    text_generated_at TIMESTAMP,
    
    CONSTRAINT pk_exec_insights PRIMARY KEY (text_id)
)
USING DELTA
COMMENT 'Combined executive insights for Vector Search'
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true'
);

-- -----------------------------------------------------------------------------
-- HELPER VIEWS
-- -----------------------------------------------------------------------------

-- Current inventory with product details
CREATE OR REPLACE VIEW ai_systems.stihl_silver.v_current_inventory AS
SELECT 
    p.product_id,
    p.model_number,
    p.product_name,
    p.category,
    p.subcategory,
    p.power_type,
    p.user_segment,
    p.msrp,
    p.cost,
    p.margin_pct,
    i.total_on_hand,
    i.total_available,
    i.is_low_stock,
    i.is_out_of_stock,
    i.days_of_supply,
    i.avg_daily_sales,
    i.snapshot_date
FROM ai_systems.stihl_silver.dim_products p
LEFT JOIN ai_systems.stihl_silver.fact_inventory_current i 
    ON p.product_id = i.product_id
    AND i.snapshot_date = current_date();

-- Latest product performance
CREATE OR REPLACE VIEW ai_systems.stihl_gold.v_latest_product_performance AS
SELECT *
FROM ai_systems.stihl_gold.product_performance
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM ai_systems.stihl_gold.product_performance);

-- -----------------------------------------------------------------------------
-- VERIFICATION
-- -----------------------------------------------------------------------------

-- Show created tables
SHOW TABLES IN ai_systems.stihl_bronze;
SHOW TABLES IN ai_systems.stihl_silver;
SHOW TABLES IN ai_systems.stihl_gold;

-- Verify CDF is enabled on text tables (required for Vector Search)
DESCRIBE EXTENDED ai_systems.stihl_silver.product_details_text;
