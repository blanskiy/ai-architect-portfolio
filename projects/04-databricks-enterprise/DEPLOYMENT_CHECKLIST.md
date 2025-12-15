# 🚀 Databricks Unity Catalog - Deployment Checklist

**Quick Reference: Step-by-Step Deployment with Managed Identity**

---

## ✅ Phase 1: Azure CLI Setup (30 minutes)

### **Run the Deployment Script**

```bash
# Navigate to project directory
cd databricks-unity-catalog

# Make script executable (if not already)
chmod +x deploy_managed_identity.sh

# Run deployment script
./deploy_managed_identity.sh
```

**What it does:**
- ✅ Creates `databricks-data` container in `azlancedb`
- ✅ Creates Databricks workspace `databricks-unity-ml`
- ✅ Enables System-Assigned Managed Identity
- ✅ Grants Storage Blob Data Contributor role
- ✅ Creates Unity Catalog Access Connector
- ✅ Saves configuration to `deployment_config.txt`

**Expected time:** 15-20 minutes

**Save the output!** You'll need:
- Workspace URL
- Principal IDs
- Tenant ID
- Spark configuration

---

## ✅ Phase 2: Unity Catalog Setup (20 minutes)

### **Step 1: Access Databricks Account Console**

1. Open workspace URL from script output
2. Login with Azure credentials
3. Click your profile (top-right) → **Manage Account**
4. You're now in Account Console

### **Step 2: Create Metastore**

1. In Account Console → **Data** → **Metastores**
2. Click **Create Metastore**
3. Fill in:
   ```
   Name: primary-metastore
   Region: eastus (or your region)
   ADLS Gen2 path: abfss://databricks-data@azlancedb.dfs.core.windows.net/metastore
   ```
4. **Access Connector**: Select `unity-catalog-connector`
5. Click **Create**

✅ **Verify**: Metastore shows as "Active"

### **Step 3: Assign Metastore to Workspace**

1. Still in Account Console → **Workspaces**
2. Find: `databricks-unity-ml`
3. Click **...** → **Assign Metastore**
4. Select: `primary-metastore`
5. Click **Assign**

✅ **Verify**: Workspace shows metastore assigned

---

## ✅ Phase 3: Create Cluster (15 minutes)

### **Step 1: Return to Workspace**

1. Click your workspace name (top-left) → **Go to Workspace**
2. You're back in the main Databricks UI

### **Step 2: Create Cluster**

1. Navigate to **Compute** → **Create Compute**
2. Fill in:
   ```
   Cluster Name: unity-catalog-rag
   Access Mode: Single User
   Runtime: 14.3 LTS (or latest LTS)
   Node Type: Standard_DS3_v2
   Min Workers: 1
   Max Workers: 4
   Autoscaling: Enabled
   ```

### **Step 3: Add Spark Configuration**

1. Click **Advanced Options** → **Spark** tab
2. Paste configuration from `deployment_config.txt`:
   ```
   spark.databricks.unity_catalog.enabled true
   spark.hadoop.fs.azure.account.auth.type.azlancedb.dfs.core.windows.net OAuth
   spark.hadoop.fs.azure.account.oauth.provider.type.azlancedb.dfs.core.windows.net org.apache.hadoop.fs.azurebfs.oauth2.MsiTokenProvider
   spark.hadoop.fs.azure.account.oauth2.msi.tenant <YOUR-TENANT-ID>
   ```
   *(Replace `<YOUR-TENANT-ID>` with actual value from deployment_config.txt)*

3. Click **Create Cluster**
4. Wait ~5 minutes for cluster to start

✅ **Verify**: Cluster status shows "Running"

### **Step 4: Test Storage Access**

1. Create notebook: **Test_Storage**
2. Attach to cluster: `unity-catalog-rag`
3. Run:
   ```python
   # Test ADLS access
   dbutils.fs.ls("abfss://databricks-data@azlancedb.dfs.core.windows.net/")
   ```

✅ **Verify**: Should see directory listing (no auth errors)

---

## ✅ Phase 4: Deploy Unity Catalog Structure (15 minutes)

### **Step 1: Create Folder Structure**

1. In Workspace, click your user folder
2. Create folder: `rag-system`
3. Inside `rag-system`, create folder: `src`

### **Step 2: Upload Files**

Upload to `/Users/<your-email>/rag-system/`:
- `unity_catalog_setup.sql`

Upload to `/Users/<your-email>/rag-system/src/`:
- `delta_rag_system.py`
- `unity_catalog_config.py`
- `azure_config.py`

### **Step 3: Create Setup Notebook**

1. In `rag-system` folder → **Create** → **Notebook**
2. Name: `01_Setup_Unity_Catalog`
3. Language: **SQL**
4. Cluster: `unity-catalog-rag`

### **Step 4: Run Setup SQL**

Copy contents of `unity_catalog_setup.sql` and paste into notebook cells:

**Cell 1: Create Catalog**
```sql
CREATE CATALOG IF NOT EXISTS ai_systems
COMMENT 'AI and ML systems catalog'
MANAGED LOCATION 'abfss://databricks-data@azlancedb.dfs.core.windows.net/catalogs/ai_systems';

SHOW CATALOGS;
```

**Cell 2: Create Schema**
```sql
CREATE SCHEMA IF NOT EXISTS ai_systems.rag_production
COMMENT 'Production RAG system schema'
MANAGED LOCATION 'abfss://databricks-data@azlancedb.dfs.core.windows.net/catalogs/ai_systems/rag_production';

SHOW SCHEMAS IN ai_systems;
```

**Cell 3-7: Create Each Table**
*(Copy table creation statements from unity_catalog_setup.sql)*

**Cell 8: Verify**
```sql
USE CATALOG ai_systems;
USE SCHEMA rag_production;
SHOW TABLES;
```

✅ **Verify**: All 5 tables listed:
- documents
- document_chunks
- document_vectors
- queries_log
- system_metrics

---

## ✅ Phase 5: Run RAG Demo (15 minutes)

### **Step 1: Create Demo Notebook**

1. In `rag-system` folder → **Create** → **Notebook**
2. Name: `02_RAG_Demo`
3. Language: **Python**
4. Cluster: `unity-catalog-rag`

### **Step 2: Copy Demo Code**

Open `MANAGED_IDENTITY_SETUP.md` → Find "Step 6.2: Create Demo Notebook"
Copy all cells into your notebook

**Update path in first cell:**
```python
sys.path.append('/Workspace/Users/<YOUR-EMAIL>/rag-system/src')
```

### **Step 3: Run Demo**

1. Click **Run All**
2. Wait ~3 minutes for completion

✅ **Verify**: All cells complete successfully

---

## ✅ Phase 6: Verification (10 minutes)

### **1. Check Data in Tables**

```sql
SELECT 
    (SELECT COUNT(*) FROM ai_systems.rag_production.documents) as docs,
    (SELECT COUNT(*) FROM ai_systems.rag_production.document_chunks) as chunks,
    (SELECT COUNT(*) FROM ai_systems.rag_production.document_vectors) as vectors,
    (SELECT COUNT(*) FROM ai_systems.rag_production.queries_log) as queries;
```

✅ **Verify**: All counts > 0

### **2. View in Data Explorer**

1. Click **Data** icon (left sidebar)
2. Navigate: `ai_systems` → `rag_production`
3. Click each table
4. Check:
   - ✅ Schema tab (columns)
   - ✅ Sample Data tab (rows)
   - ✅ Details tab (location, properties)
   - ✅ **Lineage tab** (data flow visualization!)

### **3. Check Storage in Azure**

```bash
# In Azure CLI
az storage blob list \
    --container-name databricks-data \
    --account-name azlancedb \
    --prefix "catalogs/ai_systems" \
    --auth-mode login \
    --output table
```

✅ **Verify**: See Delta Lake files (_delta_log directories)

### **4. Check Audit Logs**

```sql
SELECT * FROM system.access.audit
WHERE request_params.full_name_arg LIKE 'ai_systems.rag_production%'
ORDER BY event_time DESC
LIMIT 20;
```

✅ **Verify**: See your activity logged

---

## 🎉 Success! You Have:

- [x] Databricks workspace with Unity Catalog
- [x] Managed Identity configured (no secrets!)
- [x] 5 Delta Lake tables created
- [x] RAG system working end-to-end
- [x] Documents ingested and searchable
- [x] Automatic lineage tracking
- [x] Audit logs capturing all access
- [x] Production-ready enterprise governance

---

## 📸 Screenshots for Portfolio

Take screenshots of:

1. **Unity Catalog Structure**
   - Data Explorer showing catalog → schema → tables

2. **Lineage Visualization**
   - Click any table → Lineage tab → Screenshot

3. **Demo Results**
   - RAG demo notebook with search results

4. **Audit Logs**
   - system.access.audit query results

5. **Delta Lake Details**
   - Table details showing ADLS location

---

## 🔥 Next Steps

Now that it's deployed:

1. **Add Your Own Documents**
   ```python
   doc_id = rag.ingest_document(
       title="Your Document",
       content="Your content...",
       source="your_source"
   )
   ```

2. **Setup Databricks Vector Search**
   - Create vector index on document_vectors table
   - Enable faster similarity search

3. **Add Real Embeddings**
   - Integrate Azure OpenAI
   - Replace random vectors with actual embeddings

4. **Create Dashboard**
   - Build Databricks SQL dashboard
   - Monitor query performance

5. **Setup CI/CD**
   - Use Databricks Asset Bundles
   - Automate deployments

---

## 📞 Need Help?

**Common Issues:**

**Error: "This request is not authorized"**
→ Re-run: `./deploy_managed_identity.sh` (step 6 only)

**Error: "Unity Catalog not enabled"**
→ Verify: Workspace assigned to metastore in Account Console

**Error: "Cluster startup failed"**
→ Check: Spark configuration has correct Tenant ID

**Error: "Cannot create catalog"**
→ Run: `GRANT CREATE CATALOG ON METASTORE TO '<your-email>';`

---

## ⏱️ Total Deployment Time

- Phase 1 (Azure CLI): 30 minutes
- Phase 2 (Unity Catalog): 20 minutes
- Phase 3 (Cluster): 15 minutes
- Phase 4 (Tables): 15 minutes
- Phase 5 (Demo): 15 minutes
- Phase 6 (Verification): 10 minutes

**Total: ~105 minutes (1.75 hours)**

---

## ✅ Final Checklist

Before marking complete:

- [ ] Deployment script ran successfully
- [ ] Workspace URL accessible
- [ ] Metastore created and assigned
- [ ] Cluster running with Unity Catalog
- [ ] Storage access tested (no auth errors)
- [ ] All 5 tables created
- [ ] Demo notebook runs completely
- [ ] Data visible in tables
- [ ] Lineage visible in Data Explorer
- [ ] Audit logs show activity
- [ ] Files visible in ADLS container
- [ ] Screenshots taken for portfolio

---

**Status**: Ready to Deploy! 🚀  
**Authentication**: Managed Identity (Most Secure) 🔒  
**Time Investment**: ~2 hours  
**Result**: Enterprise-Grade RAG System ⭐
