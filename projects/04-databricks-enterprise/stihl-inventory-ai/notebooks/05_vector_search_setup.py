# Databricks notebook source
# MAGIC %md
# MAGIC # STIHL Inventory AI - Vector Search Setup
# MAGIC 
# MAGIC This notebook creates and configures Vector Search indexes for the STIHL inventory system.
# MAGIC 
# MAGIC **Indexes Created:**
# MAGIC 1. `product_details_index` - Static product info (WEEKLY sync)
# MAGIC 2. `inventory_status_index` - Dynamic inventory + pricing (DAILY sync)
# MAGIC 3. `sales_summary_index` - Monthly sales records (DAILY sync)
# MAGIC 4. `executive_insights_index` - Combined summaries for executives (DAILY sync)
# MAGIC 
# MAGIC **Sync Strategy:**
# MAGIC - Product details: Weekly (specs rarely change)
# MAGIC - Inventory/Pricing: Daily (changes frequently)
# MAGIC - Sales: Daily (new data daily)
# MAGIC - Executive: Daily (reflects latest aggregations)

# COMMAND ----------

# MAGIC %pip install databricks-vectorsearch

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient
from databricks.sdk import WorkspaceClient
import time

# Initialize clients
vs_client = VectorSearchClient()
ws_client = WorkspaceClient()

# Configuration
CATALOG = "stihl"
SCHEMA = "silver"

# Endpoint configuration
ENDPOINT_NAME = "stihl_inventory_endpoint"

# Index configurations
INDEXES = {
    "product_details": {
        "source_table": f"{CATALOG}.{SCHEMA}.product_details_text",
        "index_name": f"{CATALOG}.{SCHEMA}.product_details_index",
        "primary_key": "text_id",
        "embedding_column": "text_content",
        "sync_mode": "TRIGGERED",  # Weekly manual sync
        "description": "Product specifications, features, descriptions (rarely changes)"
    },
    "inventory_status": {
        "source_table": f"{CATALOG}.{SCHEMA}.inventory_status_text",
        "index_name": f"{CATALOG}.{SCHEMA}.inventory_status_index",
        "primary_key": "text_id",
        "embedding_column": "text_content",
        "sync_mode": "TRIGGERED",  # Daily sync via workflow
        "description": "Current pricing and inventory levels (changes daily)"
    },
    "sales_summary": {
        "source_table": f"{CATALOG}.{SCHEMA}.sales_summary_text",
        "index_name": f"{CATALOG}.{SCHEMA}.sales_summary_index",
        "primary_key": "text_id",
        "embedding_column": "text_content",
        "sync_mode": "TRIGGERED",  # Daily sync via workflow
        "description": "Monthly sales performance (new data daily)"
    },
    "executive_insights": {
        "source_table": f"{CATALOG}.{SCHEMA}.category_summary_text",  # Primary source
        "index_name": f"{CATALOG}.{SCHEMA}.executive_insights_index",
        "primary_key": "text_id",
        "embedding_column": "text_content",
        "sync_mode": "TRIGGERED",  # Daily sync via workflow
        "description": "Category summaries, trends, product recommendations"
    }
}

print(f"Endpoint: {ENDPOINT_NAME}")
print(f"Indexes to create: {list(INDEXES.keys())}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Create Vector Search Endpoint

# COMMAND ----------

def create_endpoint(endpoint_name: str, endpoint_type: str = "STANDARD"):
    """Create Vector Search endpoint if it doesn't exist"""
    try:
        endpoint = vs_client.get_endpoint(endpoint_name)
        print(f"✅ Endpoint '{endpoint_name}' already exists")
        print(f"   Status: {endpoint.get('endpoint_status', {}).get('state', 'Unknown')}")
        return endpoint
    except Exception as e:
        if "NOT_FOUND" in str(e) or "does not exist" in str(e).lower():
            print(f"Creating endpoint '{endpoint_name}'...")
            vs_client.create_endpoint(
                name=endpoint_name,
                endpoint_type=endpoint_type
            )
            print(f"⏳ Endpoint creation initiated. This may take 10-20 minutes.")
            return wait_for_endpoint(endpoint_name)
        else:
            raise e

def wait_for_endpoint(endpoint_name: str, timeout: int = 1800):
    """Wait for endpoint to be ready"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            endpoint = vs_client.get_endpoint(endpoint_name)
            state = endpoint.get("endpoint_status", {}).get("state", "")
            print(f"   Endpoint state: {state}")
            if state == "ONLINE":
                print(f"✅ Endpoint '{endpoint_name}' is ONLINE")
                return endpoint
            elif state == "FAILED":
                raise Exception(f"Endpoint creation failed: {endpoint}")
        except Exception as e:
            print(f"   Waiting... ({str(e)[:50]})")
        time.sleep(60)
    raise TimeoutError(f"Endpoint not ready after {timeout} seconds")

# Create the endpoint
endpoint = create_endpoint(ENDPOINT_NAME)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Create Vector Search Indexes

# COMMAND ----------

def create_index(
    endpoint_name: str,
    source_table: str,
    index_name: str,
    primary_key: str,
    embedding_column: str,
    sync_mode: str = "TRIGGERED"
):
    """Create a Delta Sync Vector Search index with managed embeddings"""
    try:
        index = vs_client.get_index(index_name)
        print(f"✅ Index '{index_name}' already exists")
        status = index.describe()
        print(f"   Status: {status.get('status', {}).get('ready', False)}")
        return index
    except Exception as e:
        if "NOT_FOUND" in str(e) or "does not exist" in str(e).lower():
            print(f"Creating index '{index_name}'...")
            print(f"   Source table: {source_table}")
            print(f"   Embedding column: {embedding_column}")
            print(f"   Sync mode: {sync_mode}")
            
            vs_client.create_delta_sync_index(
                endpoint_name=endpoint_name,
                source_table_name=source_table,
                index_name=index_name,
                pipeline_type=sync_mode,
                primary_key=primary_key,
                embedding_source_column=embedding_column,
                embedding_model_endpoint_name="databricks-gte-large-en"
            )
            print(f"⏳ Index creation initiated. This may take 5-15 minutes.")
            return wait_for_index(index_name)
        else:
            raise e

def wait_for_index(index_name: str, timeout: int = 1200):
    """Wait for index to be ready"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            index = vs_client.get_index(index_name)
            status = index.describe().get("status", {})
            ready = status.get("ready", False)
            row_count = status.get("num_rows", 0)
            print(f"   Index ready: {ready}, rows: {row_count}")
            if ready:
                print(f"✅ Index '{index_name}' is READY with {row_count} rows")
                return index
        except Exception as e:
            print(f"   Waiting... ({str(e)[:50]})")
        time.sleep(30)
    raise TimeoutError(f"Index not ready after {timeout} seconds")

# COMMAND ----------

# Create all indexes
print("=" * 60)
print("CREATING VECTOR SEARCH INDEXES")
print("=" * 60)

created_indexes = {}

for index_key, config in INDEXES.items():
    print(f"\n{'='*40}")
    print(f"INDEX: {index_key}")
    print(f"Description: {config['description']}")
    print(f"{'='*40}")
    
    try:
        index = create_index(
            endpoint_name=ENDPOINT_NAME,
            source_table=config["source_table"],
            index_name=config["index_name"],
            primary_key=config["primary_key"],
            embedding_column=config["embedding_column"],
            sync_mode=config["sync_mode"]
        )
        created_indexes[index_key] = index
    except Exception as e:
        print(f"❌ Error creating index: {e}")
        created_indexes[index_key] = None

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Create Combined Executive Insights Index
# MAGIC 
# MAGIC This index combines multiple summary tables for executive-level queries.
# MAGIC We'll create a view that unions the summary tables, then index it.

# COMMAND ----------

# First, create a combined view for executive insights
spark.sql(f"""
    CREATE OR REPLACE VIEW {CATALOG}.{SCHEMA}.executive_insights_combined AS
    
    -- Category summaries
    SELECT 
        text_id,
        text_content,
        'category_summary' as source_type,
        category,
        NULL as product_id,
        text_generated_at
    FROM {CATALOG}.{SCHEMA}.category_summary_text
    
    UNION ALL
    
    -- Trend summaries
    SELECT 
        text_id,
        text_content,
        'trend_summary' as source_type,
        category,
        NULL as product_id,
        text_generated_at
    FROM {CATALOG}.{SCHEMA}.trend_summary_text
    
    UNION ALL
    
    -- Product performance (top performers and dogs only for executive view)
    SELECT 
        text_id,
        text_content,
        'product_performance' as source_type,
        category,
        product_id,
        text_generated_at
    FROM {CATALOG}.{SCHEMA}.product_performance_text
    WHERE performance_tier IN ('Star', 'Dog')
""")

# Materialize as a table for Vector Search
spark.sql(f"""
    CREATE OR REPLACE TABLE {CATALOG}.{SCHEMA}.executive_insights_text
    TBLPROPERTIES (delta.enableChangeDataFeed = true)
    AS SELECT * FROM {CATALOG}.{SCHEMA}.executive_insights_combined
""")

print("Executive insights combined table created")
display(spark.table(f"{CATALOG}.{SCHEMA}.executive_insights_text").limit(5))

# COMMAND ----------

# Create the executive insights index (if needed separately)
# Note: You may want to create a separate index or use the combined table
print("\nUpdating executive insights index configuration...")

# Update the index config to point to the combined table
INDEXES["executive_insights"]["source_table"] = f"{CATALOG}.{SCHEMA}.executive_insights_text"

# Create the index
try:
    exec_index = create_index(
        endpoint_name=ENDPOINT_NAME,
        source_table=INDEXES["executive_insights"]["source_table"],
        index_name=INDEXES["executive_insights"]["index_name"],
        primary_key=INDEXES["executive_insights"]["primary_key"],
        embedding_column=INDEXES["executive_insights"]["embedding_column"],
        sync_mode=INDEXES["executive_insights"]["sync_mode"]
    )
    created_indexes["executive_insights"] = exec_index
except Exception as e:
    print(f"Note: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Test Vector Search

# COMMAND ----------

def test_search(index_name: str, query: str, num_results: int = 3):
    """Test vector similarity search"""
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"Index: {index_name}")
    print(f"{'='*60}")
    
    try:
        index = vs_client.get_index(index_name)
        results = index.similarity_search(
            query_text=query,
            columns=["text_id", "text_content"],
            num_results=num_results
        )
        
        data = results.get("result", {}).get("data_array", [])
        if data:
            for i, row in enumerate(data, 1):
                print(f"\n--- Result {i} (Score: {row[-1]:.4f}) ---")
                print(f"ID: {row[0]}")
                print(f"Content preview: {row[1][:300]}...")
        else:
            print("No results found")
        return results
    except Exception as e:
        print(f"Error: {e}")
        return None

# COMMAND ----------

# Test queries for each index
print("=" * 60)
print("TESTING VECTOR SEARCH")
print("=" * 60)

# Test product details
if created_indexes.get("product_details"):
    test_search(
        INDEXES["product_details"]["index_name"],
        "What chainsaws have 50cc or larger engine?"
    )

# Test inventory status
if created_indexes.get("inventory_status"):
    test_search(
        INDEXES["inventory_status"]["index_name"],
        "Which products are low on stock and need restocking?"
    )

# Test sales
if created_indexes.get("sales_summary"):
    test_search(
        INDEXES["sales_summary"]["index_name"],
        "Best selling battery products with year over year growth"
    )

# Test executive insights
if created_indexes.get("executive_insights"):
    test_search(
        INDEXES["executive_insights"]["index_name"],
        "Give me a summary of company performance and what products should we invest in"
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Index Sync Utilities
# MAGIC 
# MAGIC Functions for manual and scheduled sync operations.

# COMMAND ----------

def sync_index(index_name: str):
    """Trigger sync for a TRIGGERED mode index"""
    print(f"Triggering sync for index: {index_name}")
    try:
        index = vs_client.get_index(index_name)
        index.sync()
        print(f"✅ Sync triggered for {index_name}")
        return True
    except Exception as e:
        print(f"❌ Error triggering sync: {e}")
        return False

def sync_all_daily_indexes():
    """Sync all indexes that should be updated daily"""
    daily_indexes = ["inventory_status", "sales_summary", "executive_insights"]
    results = {}
    for idx_key in daily_indexes:
        if idx_key in INDEXES:
            result = sync_index(INDEXES[idx_key]["index_name"])
            results[idx_key] = result
    return results

def sync_weekly_indexes():
    """Sync indexes that should be updated weekly"""
    weekly_indexes = ["product_details"]
    results = {}
    for idx_key in weekly_indexes:
        if idx_key in INDEXES:
            result = sync_index(INDEXES[idx_key]["index_name"])
            results[idx_key] = result
    return results

# Example: Sync all daily indexes
# sync_all_daily_indexes()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 60)
print("VECTOR SEARCH SETUP SUMMARY")
print("=" * 60)

print(f"\nEndpoint: {ENDPOINT_NAME}")
print(f"Embedding Model: databricks-gte-large-en (1024 dimensions)")

print("\n" + "-" * 60)
print("INDEXES CREATED:")
print("-" * 60)

for idx_key, config in INDEXES.items():
    status = "✅ Created" if created_indexes.get(idx_key) else "❌ Failed"
    print(f"\n{idx_key}:")
    print(f"  Index: {config['index_name']}")
    print(f"  Source: {config['source_table']}")
    print(f"  Sync Mode: {config['sync_mode']}")
    print(f"  Status: {status}")
    print(f"  Description: {config['description']}")

print("\n" + "-" * 60)
print("SYNC SCHEDULE RECOMMENDATION:")
print("-" * 60)
print("""
WEEKLY (Sunday 2 AM):
  - product_details_index: Product specs rarely change
  
DAILY (3-5 AM, staggered):
  - inventory_status_index: Pricing and stock levels
  - sales_summary_index: New sales data
  - executive_insights_index: Updated aggregations
  
Use the sync utility functions:
  - sync_index(index_name): Sync single index
  - sync_all_daily_indexes(): Sync all daily indexes
  - sync_weekly_indexes(): Sync weekly indexes
""")

print("\n✅ Vector Search setup complete!")
