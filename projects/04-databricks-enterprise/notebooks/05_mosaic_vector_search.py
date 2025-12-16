# Databricks notebook source
# MAGIC %md
# MAGIC # Mosaic AI Vector Search Setup
# MAGIC 
# MAGIC This notebook replaces manual embedding generation (03_embedding_pipeline.py) with 
# MAGIC Databricks-managed Vector Search that:
# MAGIC - Automatically generates embeddings using Foundation Models
# MAGIC - Creates an ANN index for millisecond search
# MAGIC - Auto-syncs when source Delta table changes
# MAGIC 
# MAGIC ## Prerequisites
# MAGIC - Unity Catalog enabled workspace
# MAGIC - Serverless compute enabled
# MAGIC - document_chunks table created (from notebook 01 & 02)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install Dependencies

# COMMAND ----------

%pip install databricks-vectorsearch
dbutils.library.restartPython()

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient
import time

# Initialize client
client = VectorSearchClient()

# Configuration
CATALOG = "ai_systems"
SCHEMA = "rag_production"
VECTOR_SEARCH_ENDPOINT = "rag_vector_endpoint"
SOURCE_TABLE = f"{CATALOG}.{SCHEMA}.document_chunks"
INDEX_NAME = f"{CATALOG}.{SCHEMA}.chunks_vector_index"

print(f"Configuration:")
print(f"  Source Table: {SOURCE_TABLE}")
print(f"  Index Name: {INDEX_NAME}")
print(f"  Endpoint: {VECTOR_SEARCH_ENDPOINT}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Enable Change Data Feed on Source Table
# MAGIC 
# MAGIC Vector Search requires Change Data Feed (CDF) to track changes.

# COMMAND ----------

# MAGIC %sql
# MAGIC -- Enable Change Data Feed on source table
# MAGIC ALTER TABLE ai_systems.rag_production.document_chunks 
# MAGIC SET TBLPROPERTIES (delta.enableChangeDataFeed = true);

# COMMAND ----------

# Verify CDF is enabled
spark.sql(f"DESCRIBE EXTENDED {SOURCE_TABLE}").filter("col_name = 'delta.enableChangeDataFeed'").show()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Create Vector Search Endpoint
# MAGIC 
# MAGIC An endpoint is the compute resource that serves your vector indexes.

# COMMAND ----------

def create_endpoint_if_not_exists(client, endpoint_name):
    """Create Vector Search endpoint if it doesn't exist"""
    try:
        endpoint = client.get_endpoint(endpoint_name)
        print(f"✅ Endpoint '{endpoint_name}' already exists")
        return endpoint
    except Exception as e:
        if "NOT_FOUND" in str(e) or "does not exist" in str(e).lower():
            print(f"Creating endpoint '{endpoint_name}'...")
            client.create_endpoint(
                name=endpoint_name,
                endpoint_type="STANDARD"
            )
            print(f"✅ Endpoint creation initiated")
            return None
        else:
            raise e

create_endpoint_if_not_exists(client, VECTOR_SEARCH_ENDPOINT)

# COMMAND ----------

def wait_for_endpoint_ready(client, endpoint_name, timeout=900):
    """Wait for endpoint to be online"""
    print(f"Waiting for endpoint '{endpoint_name}' to be ready...")
    start = time.time()
    
    while time.time() - start < timeout:
        try:
            endpoint = client.get_endpoint(endpoint_name)
            state = endpoint.get("endpoint_status", {}).get("state", "UNKNOWN")
            
            if state == "ONLINE":
                print(f"✅ Endpoint is ONLINE")
                return True
            
            print(f"  Status: {state} - waiting...")
            time.sleep(30)
            
        except Exception as e:
            print(f"  Error checking status: {e}")
            time.sleep(30)
    
    raise TimeoutError(f"Endpoint not ready after {timeout} seconds")

wait_for_endpoint_ready(client, VECTOR_SEARCH_ENDPOINT)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Create Vector Search Index
# MAGIC 
# MAGIC The index configuration:
# MAGIC - **Delta Sync**: Automatically syncs with source table
# MAGIC - **Managed Embeddings**: Databricks generates embeddings using `databricks-gte-large-en`
# MAGIC - **Triggered Sync**: Manual trigger (use CONTINUOUS for real-time)

# COMMAND ----------

def create_index_if_not_exists(client, endpoint_name, source_table, index_name):
    """Create Vector Search index if it doesn't exist"""
    try:
        index = client.get_index(index_name)
        print(f"✅ Index '{index_name}' already exists")
        return index
    except Exception as e:
        if "NOT_FOUND" in str(e) or "does not exist" in str(e).lower():
            print(f"Creating index '{index_name}'...")
            
            index = client.create_delta_sync_index(
                endpoint_name=endpoint_name,
                source_table_name=source_table,
                index_name=index_name,
                pipeline_type="TRIGGERED",  # or "CONTINUOUS" for real-time
                primary_key="chunk_id",
                embedding_source_column="chunk_text",
                embedding_model_endpoint_name="databricks-gte-large-en"  # Foundation Model
            )
            
            print(f"✅ Index creation initiated")
            return index
        else:
            raise e

index = create_index_if_not_exists(client, VECTOR_SEARCH_ENDPOINT, SOURCE_TABLE, INDEX_NAME)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Trigger Initial Sync

# COMMAND ----------

def sync_and_wait(index, timeout=900):
    """Trigger sync and wait for completion"""
    
    # Get current status
    status = index.describe().get("status", {})
    
    if not status.get("ready", False):
        print("Triggering sync...")
        try:
            index.sync()
        except Exception as e:
            if "already in progress" in str(e).lower():
                print("Sync already in progress")
            else:
                raise e
    
    # Wait for ready
    print("Waiting for index to be ready...")
    start = time.time()
    
    while time.time() - start < timeout:
        try:
            status = index.describe().get("status", {})
            
            if status.get("ready", False):
                num_rows = status.get("num_rows", "unknown")
                print(f"✅ Index is ready!")
                print(f"   Indexed rows: {num_rows}")
                return True
            
            state = status.get("detailed_state", status.get("state", "UNKNOWN"))
            print(f"  Status: {state} - waiting...")
            time.sleep(30)
            
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(30)
    
    raise TimeoutError(f"Index not ready after {timeout} seconds")

# Get index and sync
index = client.get_index(INDEX_NAME)
sync_and_wait(index)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Test Vector Search

# COMMAND ----------

def search_index(index, query, num_results=5):
    """Search the vector index"""
    results = index.similarity_search(
        query_text=query,
        columns=["chunk_id", "doc_id", "chunk_text"],
        num_results=num_results
    )
    return results

# Test queries
test_queries = [
    "How does RAG reduce hallucination?",
    "What is machine learning?",
    "Explain vector embeddings"
]

for query in test_queries:
    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print('='*80)
    
    results = search_index(index, query)
    data = results.get("result", {}).get("data_array", [])
    
    for i, row in enumerate(data[:3], 1):
        chunk_text = row[2] if len(row) > 2 else "N/A"
        score = row[-1] if len(row) > 3 else "N/A"
        print(f"\n{i}. Score: {score}")
        print(f"   {chunk_text[:200]}...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Test Hybrid Search (Vector + Keyword)

# COMMAND ----------

# Hybrid search combines semantic similarity with keyword matching
hybrid_results = index.similarity_search(
    query_text="machine learning neural networks deep learning",
    columns=["chunk_id", "doc_id", "chunk_text"],
    num_results=5,
    query_type="HYBRID"  # Enable hybrid search
)

print("Hybrid Search Results (Vector + Keyword):")
print("=" * 80)

for i, row in enumerate(hybrid_results.get("result", {}).get("data_array", []), 1):
    chunk_text = row[2] if len(row) > 2 else "N/A"
    print(f"\n{i}. {chunk_text[:200]}...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Compare with Custom Solution
# MAGIC 
# MAGIC Let's compare search performance.

# COMMAND ----------

import time

# Mosaic AI Vector Search
query = "How does retrieval augmented generation work?"

start = time.time()
vs_results = index.similarity_search(
    query_text=query,
    columns=["chunk_id", "doc_id", "chunk_text"],
    num_results=5
)
vs_time = (time.time() - start) * 1000

print(f"Mosaic AI Vector Search:")
print(f"  Query time: {vs_time:.2f} ms")
print(f"  Results: {len(vs_results.get('result', {}).get('data_array', []))}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary: Custom vs Mosaic AI
# MAGIC 
# MAGIC | Aspect | Your Custom Solution | Mosaic AI Vector Search |
# MAGIC |--------|---------------------|-------------------------|
# MAGIC | **Embedding Model** | sentence-transformers (local) | databricks-gte-large-en (managed) |
# MAGIC | **Embedding Dimensions** | 384 | 1024 (higher quality) |
# MAGIC | **Storage** | Delta table (document_vectors) | Managed ANN index |
# MAGIC | **Search Algorithm** | Full scan + cosine similarity | Approximate Nearest Neighbor |
# MAGIC | **Search Speed** | O(n) - slower with more data | O(log n) - consistent |
# MAGIC | **Sync** | Manual re-run notebook | Automatic (triggered/continuous) |
# MAGIC | **Hybrid Search** | Not available | Built-in |
# MAGIC | **Production Ready** | ❌ | ✅ |

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Vector Search Setup Complete!
# MAGIC 
# MAGIC Your index is now:
# MAGIC - ✅ Automatically generating embeddings
# MAGIC - ✅ Indexed for fast ANN search
# MAGIC - ✅ Ready to auto-sync when data changes
# MAGIC 
# MAGIC **Next Step**: Run `06_mosaic_agent_framework.py` to deploy as production endpoint
