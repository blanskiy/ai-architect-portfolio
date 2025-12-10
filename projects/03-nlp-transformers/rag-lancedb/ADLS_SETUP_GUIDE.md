# Azure Data Lake Storage (ADLS) Setup Guide
**For Hybrid LanceDB RAG System**

## 🎯 Overview

This guide walks you through setting up Azure Data Lake Storage Gen2 for your RAG system. ADLS provides cloud-native, scalable storage for your vector embeddings.

**Time to Complete:** 15 minutes  
**Cost:** ~$0.02/GB/month (minimal for learning)

---

## 🏗️ Architecture

```
Your RAG System (Local)
    ↓
    ↓ HTTPS Connection
    ↓
Azure Data Lake Storage Gen2
├─ Container: lancedb-vectors
│  └─ Path: rag-system/
│     ├─ LanceDB metadata
│     ├─ Vector index
│     └─ Document chunks
```

---

## 📋 Prerequisites

- Azure subscription (free tier works!)
- Azure CLI installed (or use Azure Portal)
- Python with `lancedb` and `adlfs` packages

---

## 🚀 Option 1: Azure Portal (GUI)

### Step 1: Create Storage Account

1. **Login to Azure Portal**
   - Go to https://portal.azure.com

2. **Create Storage Account**
   - Click "Create a resource"
   - Search for "Storage account"
   - Click "Create"

3. **Configure Settings:**
   ```
   Basics:
   ├─ Subscription: Your subscription
   ├─ Resource Group: rg-rag-demo (create new)
   ├─ Storage account name: mystorageragXXXX (must be globally unique)
   ├─ Region: East US (or your preferred region)
   ├─ Performance: Standard
   └─ Redundancy: LRS (Locally-redundant storage)
   
   Advanced:
   ├─ Security: Enable infrastructure encryption (optional)
   ├─ Hierarchical namespace: ✅ ENABLED (CRITICAL for ADLS Gen2!)
   └─ Blob soft delete: Optional
   
   Review + Create:
   └─ Click "Create"
   ```

4. **Wait for Deployment** (~2 minutes)

### Step 2: Create Container

1. **Navigate to Storage Account**
   - Go to your storage account: `mystorageragXXXX`

2. **Create Container**
   - Left menu: "Containers"
   - Click "+ Container"
   - Name: `lancedb-vectors`
   - Public access level: Private
   - Click "Create"

### Step 3: Get Access Key

1. **Get Credentials**
   - Left menu: "Access keys"
   - Click "Show keys"
   - Copy:
     - Storage account name: `mystorageragXXXX`
     - Key1: `long-key-string-here...`

2. **Set Environment Variables** (PowerShell)
   ```powershell
   $env:AZURE_STORAGE_ACCOUNT="mystorageragXXXX"
   $env:AZURE_STORAGE_KEY="your-key-here"
   ```

---

## 🚀 Option 2: Azure CLI (Command Line)

### Step 1: Login to Azure

```bash
# Login
az login

# Set subscription (if you have multiple)
az account set --subscription "Your Subscription Name"

# Verify
az account show
```

### Step 2: Create Resource Group

```bash
# Create resource group
az group create \
  --name rg-rag-demo \
  --location eastus

# Verify
az group list --output table
```

### Step 3: Create Storage Account

```bash
# Create storage account (replace XXXX with random numbers)
az storage account create \
  --name mystorageragXXXX \
  --resource-group rg-rag-demo \
  --location eastus \
  --sku Standard_LRS \
  --kind StorageV2 \
  --enable-hierarchical-namespace true

# CRITICAL: --enable-hierarchical-namespace true enables ADLS Gen2!

# Verify
az storage account show \
  --name mystorageragXXXX \
  --resource-group rg-rag-demo \
  --query "name"
```

### Step 4: Create Container

```bash
# Get account key
ACCOUNT_KEY=$(az storage account keys list \
  --resource-group rg-rag-demo \
  --account-name mystorageragXXXX \
  --query '[0].value' \
  --output tsv)

# Create container
az storage container create \
  --name lancedb-vectors \
  --account-name mystorageragXXXX \
  --account-key $ACCOUNT_KEY

# Verify
az storage container list \
  --account-name mystorageragXXXX \
  --account-key $ACCOUNT_KEY \
  --output table
```

### Step 5: Set Environment Variables

**Linux/Mac:**
```bash
export AZURE_STORAGE_ACCOUNT="mystorageragXXXX"
export AZURE_STORAGE_KEY="$ACCOUNT_KEY"

# Make permanent (add to ~/.bashrc or ~/.zshrc)
echo "export AZURE_STORAGE_ACCOUNT='mystorageragXXXX'" >> ~/.bashrc
echo "export AZURE_STORAGE_KEY='$ACCOUNT_KEY'" >> ~/.bashrc
```

**Windows PowerShell:**
```powershell
$env:AZURE_STORAGE_ACCOUNT="mystorageragXXXX"
$env:AZURE_STORAGE_KEY="your-key-here"

# Make permanent (system-wide)
[System.Environment]::SetEnvironmentVariable('AZURE_STORAGE_ACCOUNT', 'mystorageragXXXX', 'User')
[System.Environment]::SetEnvironmentVariable('AZURE_STORAGE_KEY', 'your-key-here', 'User')
```

---

## 📦 Install Required Packages

```bash
# Install ADLS filesystem support
pip install adlfs

# Install LanceDB (if not already installed)
pip install lancedb

# Verify installation
python -c "import adlfs; print('✅ adlfs installed')"
python -c "import lancedb; print('✅ lancedb installed')"
```

---

## ✅ Test Your Setup

Create a test script: `test_adls_connection.py`

```python
"""Test ADLS connection for LanceDB RAG system."""

import os
import lancedb
import numpy as np

# Get credentials
account_name = os.getenv("AZURE_STORAGE_ACCOUNT")
account_key = os.getenv("AZURE_STORAGE_KEY")

print("=" * 80)
print("TESTING ADLS CONNECTION")
print("=" * 80)

# Check environment variables
print(f"\n1️⃣  Checking environment variables...")
if not account_name:
    print("❌ AZURE_STORAGE_ACCOUNT not set")
    exit(1)
if not account_key:
    print("❌ AZURE_STORAGE_KEY not set")
    exit(1)
print(f"✅ Account: {account_name}")
print(f"✅ Key: {'*' * 20}... (hidden)")

# Test connection
print(f"\n2️⃣  Testing LanceDB connection to ADLS...")
try:
    uri = "az://lancedb-vectors/test-connection"
    storage_options = {
        "account_name": account_name,
        "account_key": account_key
    }
    
    db = lancedb.connect(uri, storage_options=storage_options)
    print(f"✅ Connected to ADLS: {uri}")
    
    # Create test table
    print(f"\n3️⃣  Creating test table...")
    test_data = [
        {
            "id": "test1",
            "text": "This is a test document",
            "vector": np.random.randn(128).tolist()
        }
    ]
    
    table = db.create_table("test_table", data=test_data, mode="overwrite")
    print(f"✅ Created test table with {len(test_data)} rows")
    
    # Query test table
    print(f"\n4️⃣  Querying test table...")
    query_vector = np.random.randn(128)
    results = table.search(query_vector).limit(1).to_list()
    print(f"✅ Query successful, found {len(results)} results")
    
    print(f"\n" + "=" * 80)
    print("🎉 SUCCESS! ADLS is configured correctly!")
    print("=" * 80)
    print(f"\nYour vectors will be stored at:")
    print(f"  {uri}")
    print(f"\nYou can now use ADLS with your RAG system!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\n💡 Troubleshooting:")
    print("  1. Verify storage account exists")
    print("  2. Check container 'lancedb-vectors' exists")
    print("  3. Verify access key is correct")
    print("  4. Check network connectivity to Azure")
```

Run the test:
```bash
python test_adls_connection.py
```

Expected output:
```
================================================================================
TESTING ADLS CONNECTION
================================================================================

1️⃣  Checking environment variables...
✅ Account: mystorageragXXXX
✅ Key: ********************... (hidden)

2️⃣  Testing LanceDB connection to ADLS...
✅ Connected to ADLS: az://lancedb-vectors/test-connection

3️⃣  Creating test table...
✅ Created test table with 1 rows

4️⃣  Querying test table...
✅ Query successful, found 1 results

================================================================================
🎉 SUCCESS! ADLS is configured correctly!
================================================================================
```

---

## 🎯 Using ADLS with Your RAG System

Now you can use ADLS in your RAG system:

```python
from rag_config import create_adls_config
from hybrid_rag_system import HybridRAGSystem

# Create ADLS configuration
config = create_adls_config(
    container="lancedb-vectors",
    path="my-rag-system"
)

# Initialize RAG system with ADLS
rag = HybridRAGSystem(config)

# Ingest documents (vectors stored in ADLS)
documents = [
    {
        'text': "Your document text here...",
        'metadata': {'source': 'doc1.txt'}
    }
]
rag.ingest_documents(documents)

# Query (retrieves from ADLS)
result = rag.query("Your question here?")
print(result['answer'])
```

---

## 💰 Cost Estimation

### Storage Costs (ADLS Gen2)
```
Pricing (East US):
├─ Storage: $0.0208/GB/month (Hot tier)
├─ Write operations: $0.065 per 10,000 operations
└─ Read operations: $0.004 per 10,000 operations

Example Costs for Learning:
├─ 100 MB vectors: $0.002/month
├─ 1,000 read/write ops: $0.007
└─ Total: < $0.01/month

Example Costs for Small Production:
├─ 10 GB vectors: $0.21/month
├─ 100,000 operations: $0.69/month
└─ Total: ~$0.90/month
```

**Very affordable for learning and small projects!**

---

## 🔒 Security Best Practices

### 1. Use SAS Tokens (Recommended)

Instead of account keys, use SAS tokens with limited permissions:

```bash
# Generate SAS token (expires in 7 days)
az storage container generate-sas \
  --account-name mystorageragXXXX \
  --name lancedb-vectors \
  --permissions rwdl \
  --expiry $(date -u -d "7 days" '+%Y-%m-%dT%H:%MZ') \
  --auth-mode key \
  --account-key $ACCOUNT_KEY \
  --output tsv

# Set environment variable
export AZURE_STORAGE_SAS_TOKEN="your-sas-token"
```

Then use in code:
```python
config = RAGConfig(
    storage_backend='adls',
    adls_sas_token=os.getenv("AZURE_STORAGE_SAS_TOKEN")
)
```

### 2. Use Managed Identity (Production)

For production, use Azure Managed Identity instead of keys:

```python
from azure.identity import DefaultAzureCredential

# Managed identity authentication
credential = DefaultAzureCredential()
storage_options = {
    "account_name": account_name,
    "credential": credential
}
```

### 3. Restrict Network Access

```bash
# Allow access only from your IP
az storage account network-rule add \
  --resource-group rg-rag-demo \
  --account-name mystorageragXXXX \
  --ip-address YOUR_IP_ADDRESS
```

---

## 🐛 Troubleshooting

### Issue: "Container not found"
**Solution:**
```bash
# Verify container exists
az storage container list \
  --account-name mystorageragXXXX \
  --account-key $ACCOUNT_KEY

# Create if missing
az storage container create \
  --name lancedb-vectors \
  --account-name mystorageragXXXX \
  --account-key $ACCOUNT_KEY
```

### Issue: "Authentication failed"
**Solution:**
```bash
# Verify credentials
echo $AZURE_STORAGE_ACCOUNT
echo $AZURE_STORAGE_KEY

# Get fresh key
az storage account keys list \
  --resource-group rg-rag-demo \
  --account-name mystorageragXXXX
```

### Issue: "Hierarchical namespace not enabled"
**Solution:**
ADLS Gen2 requires hierarchical namespace. Can't enable on existing account - must recreate:
```bash
# Delete and recreate with hierarchical namespace
az storage account delete --name mystorageragXXXX --resource-group rg-rag-demo
az storage account create --name mystorageragXXXX --resource-group rg-rag-demo \
  --enable-hierarchical-namespace true
```

### Issue: "Connection timeout"
**Solution:**
Check firewall rules and network connectivity:
```bash
# Test connectivity
curl https://mystorageragXXXX.blob.core.windows.net

# Check firewall rules
az storage account show \
  --name mystorageragXXXX \
  --resource-group rg-rag-demo \
  --query networkRuleSet
```

---

## 🎯 Next Steps

After setup:

1. ✅ Test connection with `test_adls_connection.py`
2. ✅ Run hybrid RAG system with ADLS backend
3. ✅ Verify vectors stored in Azure Portal
4. ✅ Commit your project to GitHub
5. ✅ Add ADLS setup to your portfolio documentation

---

## 📚 Additional Resources

- [Azure Data Lake Storage Gen2 Documentation](https://learn.microsoft.com/en-us/azure/storage/blobs/data-lake-storage-introduction)
- [LanceDB Documentation](https://lancedb.github.io/lancedb/)
- [Azure Storage Pricing](https://azure.microsoft.com/en-us/pricing/details/storage/data-lake/)
- [Azure CLI Reference](https://learn.microsoft.com/en-us/cli/azure/storage)

---

**Setup Complete!** 🎉

You now have cloud-native vector storage for your RAG system!
