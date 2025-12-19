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
# MAGIC **Catalog:** ai_systems
# MAGIC **Schema:** stihl_silver

# COMMAND ----------

# MAGIC %pip install databricks-vectorsearch --upgrade --quiet
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient
import time

# Initialize client
vs_client = VectorSearchClient(disable_notice=True)

# Configuration - Using existing ai_systems catalog
CATALOG = "ai_systems"
SCHEMA_SILVER = "stihl_silver"

# Endpoint configuration
ENDPOINT_NAME = "stihl_inventory_endpoint"

# Index configurations
INDEXES = {
    "product_details": {
        "source_table": f"{CATALOG}.{SCHEMA_SILVER}.product_details_text",
        "index_name": f"{CATALOG}.{SCHEMA_SILVER}.product_details_index",
        "primary_key": "text_id",
        "embedding_column": "text_content",
        "sync_mode": "TRIGGERED",
        "description": "Product specifications, features, descriptions (rarely changes)"
    },
    "inventory_status": {
        "source_table": f"{CATALOG}.{SCHEMA_SILVER}.inventory_status_text",
        "index_name": f"{CATALOG}.{SCHEMA_SILVER}.inventory_status_index",
        "primary_key": "text_id",
        "embedding_column": "text_content",
        "sync_mode": "TRIGGERED",
        "description": "Current pricing and inventory levels (changes daily)"
    },
    "sales_summary": {
        "source_table": f"{CATALOG}.{SCHEMA_SILVER}.sales_summary_text",
        "index_name": f"{CATALOG}.{SCHEMA_SILVER}.sales_summary_index",
        "primary_key": "text_id",
        "embedding_column": "text_content",
        "sync_mode": "TRIGGERED",
        "description": "Monthly sales performance (new data daily)"
    },
    "executive_insights": {
        "source_table": f"{CATALOG}.{SCHEMA_SILVER}.executive_insights_text",
        "index_name": f"{CATALOG}.{SCHEMA_SILVER}.executive_insights_index",
        "primary_key": "text_id",
        "embedding_column": "text_content",
        "sync_mode": "TRIGGERED",
        "description": "Category summaries, trends, product recommendations"
    }
}

print(f"Catalog: {CATALOG}")
print(f"Schema: {SCHEMA_SILVER}")
print(f"Endpoint: {ENDPOINT_NAME}")
print(f"Indexes to create: {list(INDEXES.keys())}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Create Vector Search Endpoint

# COMMAND ----------

def create_endpoint_if_not_exists(endpoint_name: str):
    """Create Vector Search endpoint if it doesn't exist"""
    
    # List existing endpoints
    endpoints = vs_client.list_endpoints()
    endpoint_names = [ep.get("name") for ep in endpoints.get("endpoints", [])]
    
    if endpoint_name in endpoint_names:
        print(f"✓ Endpoint '{endpoint_name}' already exists")
        # Get endpoint details
        endpoint = vs_client.get_endpoint(endpoint_name)
        state = endpoint.get("endpoint_status", {}).get("state", "UNKNOWN")
        print(f"  Status: {state}")
        return endpoint
    else:
        print(f"Creating endpoint '{endpoint_name}'...")
        vs_client.create_endpoint(
            name=endpoint_name,
            endpoint_type="STANDARD"
        )
        print(f"  Endpoint creation initiated. This may take 10-20 minutes.")
        return wait_for_endpoint(endpoint_name)

def wait_for_endpoint(endpoint_name: str, timeout: int = 1800):
    """Wait for endpoint to become ONLINE"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        endpoint = vs_client.get_endpoint(endpoint_name)
        state = endpoint.get("endpoint_status", {}).get("state", "")
        print(f"  Endpoint state: {state}")
        
        if state == "ONLINE":
            print(f"✓ Endpoint '{endpoint_name}' is ONLINE")
            return endpoint
        elif state == "FAILED":
            raise Exception(f"Endpoint creation failed: {endpoint}")
        
        time.sleep(60)
    
    raise TimeoutError(f"Endpoint not ready after {timeout} seconds")

# Create the endpoint
print("=" * 60)
print("CREATING/VERIFYING ENDPOINT")
print("=" * 60)
endpoint = create_endpoint_if_not_exists(ENDPOINT_NAME)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Create Vector Search Indexes

# COMMAND ----------

def index_exists(endpoint_name: str, index_name: str) -> bool:
    """Check if an index exists"""
    try:
        vs_client.get_index(endpoint_name=endpoint_name, index_name=index_name)
        return True
    except Exception as e:
        if "NOT_FOUND" in str(e) or "does not exist" in str(e).lower() or "RESOURCE_DOES_NOT_EXIST" in str(e):
            return False
        # If different error, re-raise
        raise e

def create_index(
    endpoint_name: str,
    source_table: str,
    index_name: str,
    primary_key: str,
    embedding_column: str,
    sync_mode: str = "TRIGGERED"
):
    """Create a Delta Sync Vector Search index with managed embeddings"""
    
    # Check if index already exists
    if index_exists(endpoint_name, index_name):
        print(f"✓ Index '{index_name}' already exists")
        index = vs_client.get_index(endpoint_name=endpoint_name, index_name=index_name)
        status = index.describe()
        print(f"  Ready: {status.get('status', {}).get('ready', False)}")
        print(f"  Rows: {status.get('status', {}).get('num_rows', 0)}")
        return index
    
    # Create new index
    print(f"Creating index '{index_name}'...")
    print(f"  Source table: {source_table}")
    print(f"  Primary key: {primary_key}")
    print(f"  Embedding column: {embedding_column}")
    print(f"  Sync mode: {sync_mode}")
    
    index = vs_client.create_delta_sync_index(
        endpoint_name=endpoint_name,
        source_table_name=source_table,
        index_name=index_name,
        pipeline_type=sync_mode,
        primary_key=primary_key,
        embedding_source_column=embedding_column,
        embedding_model_endpoint_name="databricks-gte-large-en"
    )
    
    print(f"  Index creation initiated. This may take 5-15 minutes.")
    return wait_for_index(endpoint_name, index_name)

def wait_for_index(endpoint_name: str, index_name: str, timeout: int = 1200):
    """Wait for index to be ready"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            index = vs_client.get_index(endpoint_name=endpoint_name, index_name=index_name)
            status = index.describe().get("status", {})
            ready = status.get("ready", False)
            row_count = status.get("num_rows", 0)
            index_status = status.get("indexed_row_count", 0)
            
            print(f"  Ready: {ready}, Indexed rows: {index_status}, Total rows: {row_count}")
            
            if ready:
                print(f"✓ Index '{index_name}' is READY with {row_count} rows")
                return index
        except Exception as e:
            print(f"  Waiting... ({str(e)[:60]})")
        
        time.sleep(30)
    
    print(f"⚠ Index not ready after {timeout} seconds - may still be indexing")
    return None

# COMMAND ----------

# Create all indexes
print("=" * 60)
print("CREATING VECTOR SEARCH INDEXES")
print("=" * 60)

created_indexes = {}

for index_key, config in INDEXES.items():
    print(f"\n{'='*50}")
    print(f"INDEX: {index_key}")
    print(f"Description: {config['description']}")
    print(f"{'='*50}")
    
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
        print(f"✓ {index_key} completed")
    except Exception as e:
        print(f"✗ Error creating index: {e}")
        created_indexes[index_key] = None

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Test Vector Search

# COMMAND ----------

def test_search(endpoint_name: str, index_name: str, query: str, num_results: int = 3):
    """Test vector similarity search"""
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"Index: {index_name}")
    print(f"{'='*60}")
    
    try:
        index = vs_client.get_index(endpoint_name=endpoint_name, index_name=index_name)
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
                content_preview = row[1][:300] if len(row[1]) > 300 else row[1]
                print(f"Content: {content_preview}...")
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

# Only test indexes that were successfully created
if created_indexes.get("product_details"):
    test_search(
        ENDPOINT_NAME,
        INDEXES["product_details"]["index_name"],
        "What chainsaws have 50cc or larger engine?"
    )

if created_indexes.get("inventory_status"):
    test_search(
        ENDPOINT_NAME,
        INDEXES["inventory_status"]["index_name"],
        "Which products are low on stock and need restocking?"
    )

if created_indexes.get("sales_summary"):
    test_search(
        ENDPOINT_NAME,
        INDEXES["sales_summary"]["index_name"],
        "Best selling battery products with year over year growth"
    )

if created_indexes.get("executive_insights"):
    test_search(
        ENDPOINT_NAME,
        INDEXES["executive_insights"]["index_name"],
        "Give me a summary of company performance and what products should we invest in"
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Index Sync Utilities

# COMMAND ----------

def sync_index(endpoint_name: str, index_name: str):
    """Trigger sync for a TRIGGERED mode index"""
    print(f"Triggering sync for index: {index_name}")
    try:
        index = vs_client.get_index(endpoint_name=endpoint_name, index_name=index_name)
        index.sync()
        print(f"✓ Sync triggered for {index_name}")
        return True
    except Exception as e:
        print(f"✗ Error triggering sync: {e}")
        return False

def sync_all_daily_indexes():
    """Sync all indexes that should be updated daily"""
    daily_indexes = ["inventory_status", "sales_summary", "executive_insights"]
    results = {}
    for idx_key in daily_indexes:
        if idx_key in INDEXES:
            result = sync_index(ENDPOINT_NAME, INDEXES[idx_key]["index_name"])
            results[idx_key] = result
    return results

def sync_weekly_indexes():
    """Sync indexes that should be updated weekly"""
    weekly_indexes = ["product_details"]
    results = {}
    for idx_key in weekly_indexes:
        if idx_key in INDEXES:
            result = sync_index(ENDPOINT_NAME, INDEXES[idx_key]["index_name"])
            results[idx_key] = result
    return results

# Example usage (uncomment to run):
# sync_all_daily_indexes()
# sync_weekly_indexes()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 60)
print("VECTOR SEARCH SETUP SUMMARY")
print("=" * 60)

print(f"\nCatalog: {CATALOG}")
print(f"Schema: {SCHEMA_SILVER}")
print(f"Endpoint: {ENDPOINT_NAME}")
print(f"Embedding Model: databricks-gte-large-en (1024 dimensions)")

print("\n" + "-" * 60)
print("INDEX STATUS:")
print("-" * 60)

for idx_key, config in INDEXES.items():
    status = "✓ Created" if created_indexes.get(idx_key) else "✗ Failed"
    print(f"\n{idx_key}:")
    print(f"  Index: {config['index_name']}")
    print(f"  Source: {config['source_table']}")
    print(f"  Sync Mode: {config['sync_mode']}")
    print(f"  Status: {status}")

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
  - sync_index(ENDPOINT_NAME, index_name)
  - sync_all_daily_indexes()
  - sync_weekly_indexes()
""")

print("\n" + "=" * 60)
print("Vector Search setup complete!")
print("=" * 60)
