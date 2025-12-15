# Databricks Unity Catalog with Managed Identity - Deployment Guide

**Production Best Practice: Using Managed Identity for ADLS Access**

---

## 📋 Your Configuration

```
Resource Group:    ml-portfolio-rg
Storage Account:   azlancedb
Container:         databricks-data
Authentication:    Managed Identity (System-Assigned)
Region:           (same as storage account)
```

---

## 🚀 Phase 1: Create Azure Databricks Workspace (15 min)

### **Step 1.1: Create Databricks Container in ADLS**

```bash
# Login to Azure
az login

# Set variables
RG_NAME="ml-portfolio-rg"
STORAGE_ACCOUNT="azlancedb"
CONTAINER_NAME="databricks-data"

# Create container for Databricks
az storage container create \
    --name $CONTAINER_NAME \
    --account-name $STORAGE_ACCOUNT \
    --auth-mode login

echo "✅ Container created: $CONTAINER_NAME"
```

### **Step 1.2: Create Databricks Workspace**

```bash
# Set Databricks workspace name
DATABRICKS_WORKSPACE="databricks-unity-ml"
LOCATION="eastus"  # or your preferred region

# Create Databricks workspace (Premium tier for Unity Catalog)
az databricks workspace create \
    --resource-group $RG_NAME \
    --name $DATABRICKS_WORKSPACE \
    --location $LOCATION \
    --sku premium \
    --managed-resource-group "databricks-rg-$DATABRICKS_WORKSPACE"

echo "✅ Databricks workspace created: $DATABRICKS_WORKSPACE"
echo "   URL: https://$(az databricks workspace show --resource-group $RG_NAME --name $DATABRICKS_WORKSPACE --query workspaceUrl -o tsv)"
```

**Expected Output:**
```
✅ Databricks workspace created: databricks-unity-ml
   URL: https://adb-xxxxxxxxxxxxx.xx.azuredatabricks.net
```

**Save this URL!** You'll need it to access Databricks.

### **Step 1.3: Enable System-Assigned Managed Identity**

```bash
# Enable managed identity on Databricks workspace
az databricks workspace update \
    --resource-group $RG_NAME \
    --name $DATABRICKS_WORKSPACE \
    --set identity.type=SystemAssigned

echo "✅ Managed Identity enabled"

# Get the Managed Identity Principal ID
PRINCIPAL_ID=$(az databricks workspace show \
    --resource-group $RG_NAME \
    --name $DATABRICKS_WORKSPACE \
    --query identity.principalId -o tsv)

echo "   Principal ID: $PRINCIPAL_ID"
```

**Save the Principal ID!** We'll use it in the next step.

---

## 🔐 Phase 2: Grant Storage Access to Managed Identity (5 min)

### **Step 2.1: Assign Storage Blob Data Contributor Role**

```bash
# Get storage account resource ID
STORAGE_ID=$(az storage account show \
    --name $STORAGE_ACCOUNT \
    --resource-group $RG_NAME \
    --query id -o tsv)

# Grant "Storage Blob Data Contributor" role to Databricks managed identity
az role assignment create \
    --assignee $PRINCIPAL_ID \
    --role "Storage Blob Data Contributor" \
    --scope $STORAGE_ID

echo "✅ Storage access granted to Databricks managed identity"
```

### **Step 2.2: Verify Access**

```bash
# List role assignments
az role assignment list \
    --assignee $PRINCIPAL_ID \
    --scope $STORAGE_ID \
    --output table

# Expected to see: Storage Blob Data Contributor
```

---

## 🎯 Phase 3: Configure Unity Catalog (20 min)

### **Step 3.1: Access Databricks Workspace**

1. Open the Databricks URL from Step 1.2
2. Login with your Azure credentials
3. You should see the Databricks UI

### **Step 3.2: Create Access Connector for Unity Catalog**

Unity Catalog requires an **Access Connector** to use managed identity.

```bash
# Create Access Connector
CONNECTOR_NAME="unity-catalog-connector"

az databricks access-connector create \
    --resource-group $RG_NAME \
    --name $CONNECTOR_NAME \
    --location $LOCATION \
    --identity-type SystemAssigned

echo "✅ Access Connector created: $CONNECTOR_NAME"

# Get connector's managed identity
CONNECTOR_PRINCIPAL_ID=$(az databricks access-connector show \
    --resource-group $RG_NAME \
    --name $CONNECTOR_NAME \
    --query identity.principalId -o tsv)

echo "   Connector Principal ID: $CONNECTOR_PRINCIPAL_ID"

# Grant storage access to connector
az role assignment create \
    --assignee $CONNECTOR_PRINCIPAL_ID \
    --role "Storage Blob Data Contributor" \
    --scope $STORAGE_ID

echo "✅ Storage access granted to Access Connector"
```

### **Step 3.3: Create Unity Catalog Metastore**

In Databricks UI:

1. Go to **Account Console** (top-right menu → Manage Account)
2. Click **Data** → **Metastores**
3. Click **Create Metastore**
4. Fill in:
   - **Name**: `primary-metastore`
   - **Region**: Select your region (e.g., East US)
   - **ADLS Gen2 path**: `abfss://databricks-data@azlancedb.dfs.core.windows.net/metastore`
   - **Access Connector ID**: Select the connector we just created
5. Click **Create**

**Expected Result:**
```
✅ Metastore created: primary-metastore
   Location: abfss://databricks-data@azlancedb.dfs.core.windows.net/metastore
   Access: Via managed identity
```

### **Step 3.4: Assign Metastore to Workspace**

Still in Account Console:

1. Go to **Workspaces**
2. Find your workspace: `databricks-unity-ml`
3. Click **Actions** → **Assign Metastore**
4. Select: `primary-metastore`
5. Click **Assign**

**Verification:**
```
✅ Workspace assigned to metastore
   Workspace: databricks-unity-ml
   Metastore: primary-metastore
```

---

## 💻 Phase 4: Create and Configure Cluster (15 min)

### **Step 4.1: Create All-Purpose Cluster**

In Databricks workspace:

1. Go to **Compute** → **Create Compute**
2. Fill in:

```
Cluster Name: unity-catalog-rag
Access Mode: Single User (or Shared - Unity Catalog enabled)
Databricks Runtime: 14.3 LTS (or latest LTS)
Node Type: Standard_DS3_v2
Workers: 
  - Min: 1
  - Max: 4
  - Autoscaling: Enabled
```

3. **Advanced Options** → **Spark** tab:

```ini
# Spark Configuration for Managed Identity
spark.databricks.passthrough.enabled true
spark.databricks.unity_catalog.enabled true

# Configure ADLS Gen2 access with Managed Identity
spark.hadoop.fs.azure.account.auth.type.azlancedb.dfs.core.windows.net OAuth
spark.hadoop.fs.azure.account.oauth.provider.type.azlancedb.dfs.core.windows.net org.apache.hadoop.fs.azurebfs.oauth2.MsiTokenProvider
spark.hadoop.fs.azure.account.oauth2.msi.tenant <YOUR-TENANT-ID>
```

**To get your Tenant ID:**
```bash
az account show --query tenantId -o tsv
```

4. Click **Create Cluster**
5. Wait ~5 minutes for cluster to start

**Expected Result:**
```
✅ Cluster created and running
   Name: unity-catalog-rag
   State: Running
   Unity Catalog: Enabled
   Managed Identity: Configured
```

### **Step 4.2: Test Storage Access**

Create a new notebook and test:

```python
# Test ADLS access with managed identity
dbutils.fs.ls("abfss://databricks-data@azlancedb.dfs.core.windows.net/")

# Expected output: List of files/folders in container
# Should NOT get any authentication errors
```

If successful, you'll see directory listing. If error, check managed identity configuration.

---

## 📦 Phase 5: Deploy Unity Catalog Structure (10 min)

### **Step 5.1: Upload SQL Setup File**

1. In Databricks workspace, go to **Workspace**
2. Create folder: `/Users/<your-email>/rag-system`
3. Right-click folder → **Import**
4. Upload `unity_catalog_setup.sql` from your local machine

### **Step 5.2: Create SQL Notebook**

1. In the same folder, **Create** → **Notebook**
2. Name: `01_Setup_Unity_Catalog`
3. Language: **SQL**
4. Cluster: `unity-catalog-rag`

### **Step 5.3: Run Setup SQL**

In the notebook, paste and run:

```sql
-- ============================================================
-- Unity Catalog Setup for RAG System
-- Using Managed Identity for ADLS Access
-- ============================================================

-- Create Catalog
CREATE CATALOG IF NOT EXISTS ai_systems
COMMENT 'AI and ML systems catalog'
MANAGED LOCATION 'abfss://databricks-data@azlancedb.dfs.core.windows.net/catalogs/ai_systems';

-- Create Schema
CREATE SCHEMA IF NOT EXISTS ai_systems.rag_production
COMMENT 'Production RAG system schema'
MANAGED LOCATION 'abfss://databricks-data@azlancedb.dfs.core.windows.net/catalogs/ai_systems/rag_production';

-- Verify creation
SHOW CATALOGS;
SHOW SCHEMAS IN ai_systems;
```

Run the cell. **Expected Output:**
```
✅ Catalog 'ai_systems' created
✅ Schema 'ai_systems.rag_production' created
```

### **Step 5.4: Create Tables**

Continue in the same notebook:

```sql
-- Create documents table
CREATE TABLE IF NOT EXISTS ai_systems.rag_production.documents (
  doc_id STRING COMMENT 'Unique document identifier',
  title STRING COMMENT 'Document title',
  content STRING COMMENT 'Full document content',
  source STRING COMMENT 'Document source (PDF, URL, etc)',
  metadata MAP<STRING, STRING> COMMENT 'Additional metadata',
  ingestion_timestamp TIMESTAMP COMMENT 'When document was ingested',
  last_updated TIMESTAMP COMMENT 'Last update timestamp'
)
USING DELTA
COMMENT 'Source documents for RAG system'
LOCATION 'abfss://databricks-data@azlancedb.dfs.core.windows.net/catalogs/ai_systems/rag_production/documents'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.minReaderVersion' = '1',
  'delta.minWriterVersion' = '2'
);

-- Create document_chunks table
CREATE TABLE IF NOT EXISTS ai_systems.rag_production.document_chunks (
  chunk_id STRING COMMENT 'Unique chunk identifier',
  doc_id STRING COMMENT 'Parent document ID',
  chunk_text STRING COMMENT 'Chunk content',
  chunk_index INT COMMENT 'Position in document',
  token_count INT COMMENT 'Number of tokens in chunk',
  metadata MAP<STRING, STRING> COMMENT 'Chunk metadata',
  created_timestamp TIMESTAMP COMMENT 'Creation timestamp'
)
USING DELTA
COMMENT 'Chunked documents for RAG retrieval'
LOCATION 'abfss://databricks-data@azlancedb.dfs.core.windows.net/catalogs/ai_systems/rag_production/document_chunks'
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

-- Create document_vectors table
CREATE TABLE IF NOT EXISTS ai_systems.rag_production.document_vectors (
  chunk_id STRING COMMENT 'Reference to chunk',
  doc_id STRING COMMENT 'Reference to document',
  embedding ARRAY<FLOAT> COMMENT 'Vector embedding (768-dim)',
  embedding_model STRING COMMENT 'Model used for embedding',
  text_preview STRING COMMENT 'First 100 chars of chunk',
  created_timestamp TIMESTAMP COMMENT 'Creation timestamp'
)
USING DELTA
COMMENT 'Vector embeddings for document chunks'
LOCATION 'abfss://databricks-data@azlancedb.dfs.core.windows.net/catalogs/ai_systems/rag_production/document_vectors'
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

-- Create queries_log table
CREATE TABLE IF NOT EXISTS ai_systems.rag_production.queries_log (
  query_id STRING COMMENT 'Unique query identifier',
  query_text STRING COMMENT 'User query',
  query_embedding ARRAY<FLOAT> COMMENT 'Query vector',
  top_k INT COMMENT 'Number of results requested',
  results_count INT COMMENT 'Number of results returned',
  latency_ms DOUBLE COMMENT 'Query latency in milliseconds',
  user_id STRING COMMENT 'User who made query',
  timestamp TIMESTAMP COMMENT 'Query timestamp'
)
USING DELTA
COMMENT 'Audit log of all RAG queries'
LOCATION 'abfss://databricks-data@azlancedb.dfs.core.windows.net/catalogs/ai_systems/rag_production/queries_log'
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.deletedFileRetentionDuration' = 'interval 30 days'
);

-- Create system_metrics table
CREATE TABLE IF NOT EXISTS ai_systems.rag_production.system_metrics (
  metric_id STRING COMMENT 'Metric identifier',
  metric_name STRING COMMENT 'Metric name',
  metric_value DOUBLE COMMENT 'Metric value',
  metric_unit STRING COMMENT 'Unit of measurement',
  tags MAP<STRING, STRING> COMMENT 'Metric tags',
  timestamp TIMESTAMP COMMENT 'Metric timestamp'
)
USING DELTA
COMMENT 'System performance metrics'
LOCATION 'abfss://databricks-data@azlancedb.dfs.core.windows.net/catalogs/ai_systems/rag_production/system_metrics';

-- Verify all tables created
SHOW TABLES IN ai_systems.rag_production;
```

**Expected Output:**
```
✅ 5 tables created:
   - documents
   - document_chunks
   - document_vectors
   - queries_log
   - system_metrics
```

### **Step 5.5: Grant Permissions**

```sql
-- Grant permissions to yourself and team
GRANT USE CATALOG ON CATALOG ai_systems TO `<your-email@company.com>`;
GRANT USE SCHEMA ON SCHEMA ai_systems.rag_production TO `<your-email@company.com>`;
GRANT ALL PRIVILEGES ON SCHEMA ai_systems.rag_production TO `<your-email@company.com>`;

-- Verify
SHOW GRANTS ON CATALOG ai_systems;
SHOW GRANTS ON SCHEMA ai_systems.rag_production;
```

---

## 🧪 Phase 6: Deploy and Test RAG System (20 min)

### **Step 6.1: Upload Python Code**

1. In Databricks workspace, navigate to `/Users/<your-email>/rag-system`
2. Create folder: `src`
3. Upload these files:
   - `delta_rag_system.py`
   - `unity_catalog_config.py`
   - `azure_config.py`

### **Step 6.2: Create Demo Notebook**

Create new notebook: `02_RAG_Demo`

```python
# Databricks notebook source
# MAGIC %md
# MAGIC # Delta Lake RAG System Demo
# MAGIC ## With Managed Identity Authentication

# COMMAND ----------
# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------
# Import Delta RAG system
import sys
sys.path.append('/Workspace/Users/<your-email>/rag-system/src')

from delta_rag_system import DeltaLakeRAGSystem
import uuid
from datetime import datetime

# Initialize RAG system
rag = DeltaLakeRAGSystem(
    spark,
    catalog="ai_systems",
    schema="rag_production"
)

print("✅ RAG system initialized")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Ingest Test Document

# COMMAND ----------
# Ingest a sample document
doc_id = rag.ingest_document(
    title="Unity Catalog Overview",
    content="""Unity Catalog is Databricks' unified governance solution for data and AI assets.
    It provides centralized access control, auditing, lineage, and data discovery across all workspaces.
    Unity Catalog supports fine-grained permissions at the catalog, schema, table, and column levels.
    It automatically tracks data lineage and provides audit logs for compliance requirements.""",
    source="databricks_documentation",
    metadata={"category": "governance", "version": "1.0", "author": "databricks"}
)

print(f"✅ Document ingested with ID: {doc_id}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Verify Document in Table

# COMMAND ----------
# Query the documents table
documents_df = spark.sql("""
    SELECT doc_id, title, LEFT(content, 100) as content_preview, source
    FROM ai_systems.rag_production.documents
    ORDER BY ingestion_timestamp DESC
    LIMIT 5
""")

display(documents_df)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Chunk Document

# COMMAND ----------
# Chunk the document
chunks = rag.chunk_document(doc_id, chunk_size=200, overlap=50)

print(f"✅ Created {len(chunks)} chunks")
print(f"   Chunk IDs: {chunks[:3]}...")  # Show first 3

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. View Chunks

# COMMAND ----------
# Query chunks table
chunks_df = spark.sql(f"""
    SELECT chunk_id, LEFT(chunk_text, 100) as chunk_preview, chunk_index, token_count
    FROM ai_systems.rag_production.document_chunks
    WHERE doc_id = '{doc_id}'
    ORDER BY chunk_index
""")

display(chunks_df)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. Generate Embeddings

# COMMAND ----------
# Generate embeddings for chunks
num_embeddings = rag.generate_embeddings(chunks, model_name="sentence-transformers/all-MiniLM-L6-v2")

print(f"✅ Generated {num_embeddings} embeddings")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 6. View Vectors

# COMMAND ----------
# Query vectors table
vectors_df = spark.sql(f"""
    SELECT 
        chunk_id, 
        doc_id, 
        text_preview,
        SIZE(embedding) as vector_dim,
        embedding_model
    FROM ai_systems.rag_production.document_vectors
    WHERE doc_id = '{doc_id}'
    LIMIT 5
""")

display(vectors_df)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 7. Search (RAG Query)

# COMMAND ----------
# Perform search
query = "What is Unity Catalog?"
results = rag.search(query, top_k=3, user_id="demo_user")

print(f"✅ Search completed")
print(f"   Query: {query}")
print(f"   Results: {len(results)}")

# Display results
import pandas as pd
results_df = pd.DataFrame(results)
display(results_df[['title', 'text_preview', 'score']])

# COMMAND ----------
# MAGIC %md
# MAGIC ## 8. Verify Query Logging

# COMMAND ----------
# Check query logs
query_logs_df = spark.sql("""
    SELECT 
        query_id,
        query_text,
        top_k,
        results_count,
        latency_ms,
        user_id,
        timestamp
    FROM ai_systems.rag_production.queries_log
    ORDER BY timestamp DESC
    LIMIT 10
""")

display(query_logs_df)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 9. Check Table Statistics

# COMMAND ----------
# Get counts for all tables
stats = spark.sql("""
    SELECT 'documents' as table_name, COUNT(*) as row_count 
    FROM ai_systems.rag_production.documents
    UNION ALL
    SELECT 'document_chunks', COUNT(*) 
    FROM ai_systems.rag_production.document_chunks
    UNION ALL
    SELECT 'document_vectors', COUNT(*) 
    FROM ai_systems.rag_production.document_vectors
    UNION ALL
    SELECT 'queries_log', COUNT(*) 
    FROM ai_systems.rag_production.queries_log
""")

display(stats)

# COMMAND ----------
# MAGIC %md
# MAGIC ## ✅ Demo Complete!
# MAGIC 
# MAGIC Successfully demonstrated:
# MAGIC - Document ingestion to Delta Lake
# MAGIC - Chunking with overlap
# MAGIC - Embedding generation
# MAGIC - Vector search
# MAGIC - Query logging
# MAGIC - All with Unity Catalog governance and Managed Identity authentication!
```

### **Step 6.3: Run Complete Demo**

1. Attach notebook to cluster: `unity-catalog-rag`
2. Click **Run All**
3. Wait for all cells to complete (~2-3 minutes)

**Expected Results:**
- ✅ Document ingested
- ✅ Chunks created
- ✅ Embeddings generated
- ✅ Search executed
- ✅ Results displayed
- ✅ Query logged

---

## ✅ Phase 7: Verification Checklist

### **1. Storage Verification**

```bash
# Check that files were created in ADLS
az storage blob list \
    --container-name databricks-data \
    --account-name azlancedb \
    --prefix "catalogs/ai_systems" \
    --auth-mode login \
    --output table

# Expected: See _delta_log directories for each table
```

### **2. Unity Catalog Verification**

In Databricks UI → **Data Explorer**:
- Navigate to `ai_systems` catalog
- Expand `rag_production` schema
- Click each table to see:
  - Schema
  - Sample data
  - Details tab (location, properties)
  - History tab (Delta Lake versions)
  - **Lineage tab** (see data flow!) ✨

### **3. Query Verification**

```sql
-- Check all tables have data
SELECT 
    (SELECT COUNT(*) FROM ai_systems.rag_production.documents) as documents,
    (SELECT COUNT(*) FROM ai_systems.rag_production.document_chunks) as chunks,
    (SELECT COUNT(*) FROM ai_systems.rag_production.document_vectors) as vectors,
    (SELECT COUNT(*) FROM ai_systems.rag_production.queries_log) as queries;

-- Expected: All counts > 0
```

### **4. Permissions Verification**

```sql
-- Check your access
SHOW GRANTS ON CATALOG ai_systems;
SHOW GRANTS ON SCHEMA ai_systems.rag_production;
SHOW GRANTS ON TABLE ai_systems.rag_production.documents;
```

### **5. Audit Log Verification**

```sql
-- View access audit (Unity Catalog tracks everything!)
SELECT 
    event_time,
    user_identity.email as user,
    action_name,
    request_params.full_name_arg as object
FROM system.access.audit
WHERE request_params.full_name_arg LIKE 'ai_systems.rag_production%'
ORDER BY event_time DESC
LIMIT 20;
```

---

## 🎉 Success Criteria

You've successfully deployed when you can:

- [x] Access Databricks workspace
- [x] Cluster running with Unity Catalog enabled
- [x] Managed Identity configured for ADLS access
- [x] Catalog `ai_systems` created and visible
- [x] Schema `rag_production` created with 5 tables
- [x] Demo notebook runs without errors
- [x] Data visible in tables
- [x] Query logs captured
- [x] Files visible in ADLS under `catalogs/ai_systems/`
- [x] Lineage visible in Data Explorer
- [x] Audit logs showing your activity

---

## 🔧 Troubleshooting

### Issue: "This request is not authorized"

**Cause**: Managed Identity not configured properly

**Fix**:
```bash
# Re-grant storage access
az role assignment create \
    --assignee $PRINCIPAL_ID \
    --role "Storage Blob Data Contributor" \
    --scope /subscriptions/<sub-id>/resourceGroups/ml-portfolio-rg/providers/Microsoft.Storage/storageAccounts/azlancedb
```

### Issue: "Unity Catalog not enabled"

**Cause**: Workspace not assigned to metastore

**Fix**: Go to Account Console → Workspaces → Assign metastore to your workspace

### Issue: "Cannot create catalog"

**Cause**: No CREATE CATALOG privilege

**Fix**:
```sql
-- Have account admin run
GRANT CREATE CATALOG ON METASTORE TO `your-email@company.com`;
```

---

## 📚 Next Steps After Deployment

1. **Add More Documents**: Ingest your own documents
2. **Setup Vector Search**: Create Databricks Vector Search index
3. **Add Real Embeddings**: Integrate Azure OpenAI
4. **Create Dashboards**: Build monitoring in Databricks SQL
5. **Setup CI/CD**: Use Databricks Asset Bundles

---

## 🎯 What You've Achieved

✅ **Production Databricks environment** with Unity Catalog  
✅ **Managed Identity authentication** (no secrets in config!)  
✅ **Complete RAG system** running in the cloud  
✅ **Enterprise governance** with audit logs & lineage  
✅ **Delta Lake ACID storage** with time travel  
✅ **Portfolio-ready deployment** you can demo  

**This is enterprise-grade!** 🚀

---

**Total Setup Time**: ~90 minutes  
**Status**: Production-Ready ✅  
**Authentication**: Managed Identity (Most Secure) 🔒
