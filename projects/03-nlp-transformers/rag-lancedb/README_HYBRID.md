# Hybrid RAG with LanceDB - Local + ADLS
**Days 1-2: Enterprise-Ready RAG from Scratch**

**Part of:** AI Architect Portfolio Project  
**Module:** Month 2 Week 2 - RAG Systems  
**Created:** December 2025

---

## 🎯 Why Hybrid?

This tutorial teaches you **both** local development AND cloud-native deployment:

| Approach | Best For | When to Use |
|----------|----------|-------------|
| **Local** | Learning, rapid iteration | • Understanding concepts<br>• Fast experimentation<br>• No Azure costs |
| **ADLS** | Portfolio, production | • Demonstrating Azure skills<br>• Team collaboration<br>• Scalable architecture |

**You'll learn both** - start local, deploy to ADLS! 🚀

---

## 📚 What You'll Learn

### Core RAG Concepts
- ✅ What is RAG and why it's better than vanilla LLMs
- ✅ Vector embeddings and semantic search
- ✅ Document chunking strategies
- ✅ LanceDB for vector storage
- ✅ Building a complete RAG pipeline

### Cloud Architecture
- ✅ Azure Data Lake Storage (ADLS) integration
- ✅ Separation of compute and storage
- ✅ Cloud-native design patterns
- ✅ Production deployment considerations

### Interview-Ready Skills
- ✅ "I built a cloud-native RAG system with ADLS"
- ✅ "I understand trade-offs between local and cloud storage"
- ✅ "I can architect scalable AI systems on Azure"

---

## 🚀 Quick Start

### Prerequisites
```bash
# Python 3.9 or higher
python --version

# Virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### Installation
```bash
# Install all dependencies (includes ADLS support)
pip install -r requirements.txt

# Verify installation
python -c "import lancedb; import adlfs; print('✅ Ready!')"
```

---

## 📁 Project Structure

```
hybrid-rag-lancedb/
├── rag_config.py                  ← Hybrid configuration (local/ADLS)
├── hybrid_rag_system.py           ← Main RAG system
├── document_processor.py          ← Document loading
├── ADLS_SETUP_GUIDE.md           ← Step-by-step ADLS setup
├── requirements.txt               ← Dependencies (includes adlfs)
└── README.md                      ← You are here
```

---

## 🎓 Learning Path

### Phase 1: Local Development (30 minutes)

**Goal:** Understand RAG concepts without cloud complexity

```python
from rag_config import create_local_config
from hybrid_rag_system import HybridRAGSystem

# Start with local storage
config = create_local_config()
rag = HybridRAGSystem(config)

# Ingest documents
documents = [
    {
        'text': "Your document text...",
        'metadata': {'source': 'doc1.txt'}
    }
]
rag.ingest_documents(documents)

# Query
result = rag.query("Your question?")
print(result['answer'])
```

**What you'll see:**
```
📁 STORAGE:
  Backend: LOCAL
  Location: ./lancedb

✅ Vectors stored locally
```

---

### Phase 2: ADLS Setup (15 minutes)

**Goal:** Set up Azure cloud storage

Follow the complete guide: [ADLS_SETUP_GUIDE.md](ADLS_SETUP_GUIDE.md)

**Quick steps:**
```bash
# 1. Create storage account
az storage account create \
  --name mystorageragXXXX \
  --resource-group rg-rag-demo \
  --enable-hierarchical-namespace true

# 2. Create container
az storage container create \
  --name lancedb-vectors \
  --account-name mystorageragXXXX

# 3. Set environment variables
export AZURE_STORAGE_ACCOUNT="mystorageragXXXX"
export AZURE_STORAGE_KEY="your-key-here"
```

---

### Phase 3: Cloud Deployment (15 minutes)

**Goal:** Move to production-like architecture

```python
from rag_config import create_adls_config
from hybrid_rag_system import HybridRAGSystem

# Switch to ADLS storage
config = create_adls_config(
    container="lancedb-vectors",
    path="my-rag-system"
)
rag = HybridRAGSystem(config)

# Same API - different backend!
rag.ingest_documents(documents)
result = rag.query("Your question?")
```

**What you'll see:**
```
📁 STORAGE:
  Backend: ADLS
  Account: mystorageragXXXX
  Container: lancedb-vectors
  Path: my-rag-system
  Full URI: az://lancedb-vectors/my-rag-system

✅ Connected to ADLS
📦 Vectors stored in ADLS
```

---

## 🏗️ Architecture Comparison

### Local Architecture
```
┌─────────────────────────┐
│  Your Computer          │
│  ├─ Python code         │
│  ├─ LanceDB vectors     │ ← Everything local
│  └─ Query processing    │
└─────────────────────────┘
```

**Pros:**
- ✅ Zero cost
- ✅ Fast iteration
- ✅ No network latency
- ✅ Perfect for learning

**Cons:**
- ❌ Not scalable
- ❌ Can't collaborate
- ❌ Data lost if machine fails
- ❌ Not impressive in portfolio

---

### ADLS Architecture (Cloud-Native)
```
┌─────────────────────────┐
│  Your Computer          │
│  ├─ Python code         │ ← Compute
│  └─ Query processing    │
└─────────────────────────┘
         ↓ HTTPS
┌─────────────────────────┐
│  Azure ADLS Gen2        │
│  ├─ LanceDB vectors     │ ← Storage
│  └─ Persistent data     │
└─────────────────────────┘
```

**Pros:**
- ✅ Scalable (TBs of vectors)
- ✅ Team collaboration
- ✅ Data persistence
- ✅ **Portfolio-worthy architecture**

**Cons:**
- ⚠️ Minimal cost (~$0.02/GB/month)
- ⚠️ Network latency (~50-100ms)
- ⚠️ Requires Azure setup

---

## 💡 When to Use Each

| Scenario | Recommended | Why |
|----------|------------|-----|
| **Learning RAG concepts** | Local | Fast, free, focus on learning |
| **Portfolio project** | ADLS | Shows Azure skills, production-like |
| **Quick prototyping** | Local | Iterate quickly |
| **Team project** | ADLS | Share data across team |
| **Production deployment** | ADLS | Scalable, reliable |
| **Interview demo** | ADLS | More impressive |

---

## 🎯 Our Recommendation

### For Learning + Portfolio (Best!)

```python
# Week workflow:
# Day 1 (morning): Learn with local
config_local = create_local_config()
rag_local = HybridRAGSystem(config_local)

# Day 1 (afternoon): Setup ADLS
# Follow ADLS_SETUP_GUIDE.md

# Day 2: Migrate to ADLS for portfolio
config_adls = create_adls_config()
rag_adls = HybridRAGSystem(config_adls)

# Commit ADLS version to GitHub! ✅
```

**Result:** You learn concepts locally, but your portfolio shows cloud-native architecture! 🚀

---

## 💰 Cost Comparison

### Local Storage
```
Cost: $0/month
Perfect for learning!
```

### ADLS Storage
```
For Learning Project:
├─ Storage: 100 MB vectors = $0.002/month
├─ Operations: 1,000 reads = $0.0004/month
└─ Total: < $0.01/month ☕

For Small Production:
├─ Storage: 10 GB vectors = $0.21/month
├─ Operations: 100,000 ops = $0.69/month
└─ Total: ~$0.90/month

Worth it for portfolio value!
```

---

## 🔄 Easy Switching

The hybrid system makes it trivial to switch:

```python
# Development: Local
from rag_config import RAGConfig
config = RAGConfig(storage_backend='local')

# Production: ADLS
config = RAGConfig(storage_backend='adls')

# Everything else is identical!
```

---

## 🎤 Interview Talking Points

### With Local Only:
> "I built a RAG system with LanceDB for local vector storage."

**Impact:** ⭐⭐ (Basic)

---

### With Hybrid (Local + ADLS):
> "I built a cloud-native RAG system using LanceDB with Azure Data Lake Storage. During development, I used local storage for rapid iteration. For production deployment, I migrated to ADLS which demonstrates separation of compute and storage - a key cloud architecture principle. The vector index persists in ADLS, enabling team collaboration and scalability while keeping compute flexible. This architecture scales from prototype to production without code changes."

**Impact:** ⭐⭐⭐⭐⭐ (Professional!)

---

## 📊 What You'll Build

```
Hybrid RAG System:
──────────────────

CAPABILITIES:
✅ Local development mode
✅ ADLS production mode
✅ Document ingestion (PDF, DOCX, TXT)
✅ Smart chunking with overlap
✅ Azure OpenAI embeddings
✅ Semantic search
✅ Answer generation with citations
✅ Easy backend switching

ARCHITECTURE:
✅ Separation of compute and storage
✅ Cloud-native design
✅ Production-ready patterns
✅ Portfolio-worthy!
```

---

## 🚀 Getting Started

### Step 1: Clone or Download

Download these files to your project:
- `rag_config.py`
- `hybrid_rag_system.py`
- `document_processor.py`
- `ADLS_SETUP_GUIDE.md`
- `requirements.txt`
- `README.md`

### Step 2: Install Dependencies

```bash
cd your-project-folder
pip install -r requirements.txt
```

### Step 3: Start with Local

```python
python hybrid_rag_system.py
```

This runs the demo with local storage. Understand the concepts!

### Step 4: Setup ADLS

Follow [ADLS_SETUP_GUIDE.md](ADLS_SETUP_GUIDE.md) for complete setup.

### Step 5: Switch to ADLS

Update your code to use ADLS backend - same API, different storage!

### Step 6: Commit to GitHub

```bash
git add .
git commit -m "Add hybrid RAG system with ADLS support"
git push origin main
```

---

## 🎓 Learning Outcomes

After completing this tutorial:

| Skill | Level | Interview-Ready |
|-------|-------|----------------|
| Explain RAG architecture | ✅ Expert | Yes |
| Build RAG pipeline | ✅ Intermediate | Yes |
| Optimize chunking | ✅ Intermediate | Yes |
| Deploy to Azure | ✅ Intermediate | Yes |
| Cloud architecture | ✅ Intermediate | Yes |
| Production considerations | ✅ Beginner | Yes |

---

## 🐛 Troubleshooting

### Local Mode Issues

**Issue:** "LanceDB not installed"
```bash
pip install lancedb
```

**Issue:** "Directory not found"
```bash
mkdir -p ./lancedb
```

---

### ADLS Mode Issues

**Issue:** "Authentication failed"
```bash
# Check environment variables
echo $AZURE_STORAGE_ACCOUNT
echo $AZURE_STORAGE_KEY

# Get fresh credentials
az storage account keys list --account-name mystorageragXXXX
```

**Issue:** "Container not found"
```bash
# Create container
az storage container create \
  --name lancedb-vectors \
  --account-name mystorageragXXXX
```

**Issue:** "Hierarchical namespace not enabled"
```
Must recreate storage account with --enable-hierarchical-namespace true
See ADLS_SETUP_GUIDE.md for details
```

---

## 📚 Additional Resources

- [LanceDB Documentation](https://lancedb.github.io/lancedb/)
- [Azure ADLS Gen2 Docs](https://learn.microsoft.com/en-us/azure/storage/blobs/data-lake-storage-introduction)
- [ADLS Setup Guide](ADLS_SETUP_GUIDE.md)
- [RAG Best Practices](https://www.pinecone.io/learn/retrieval-augmented-generation/)

---

## 🎯 Next Steps

### After Mastering Hybrid RAG:

1. **Days 3-5:** Databricks Unity Catalog
   - Enterprise RAG with built-in governance
   - Automatic lineage tracking
   - Production deployment

2. **Portfolio Enhancement:**
   - Add monitoring and logging
   - Implement hybrid search (keyword + semantic)
   - Build evaluation framework

3. **Interview Preparation:**
   - Practice explaining architecture
   - Prepare demo
   - Document trade-offs

---

## ✅ Success Criteria

You've mastered hybrid RAG when you can:

- [ ] Explain benefits of local vs ADLS storage
- [ ] Build RAG pipeline with both backends
- [ ] Switch between local and ADLS easily
- [ ] Set up ADLS from scratch
- [ ] Deploy to cloud with proper configuration
- [ ] Explain cloud architecture principles
- [ ] Demonstrate in portfolio

---

**Ready to build a production-worthy RAG system?** 

Start with local, deploy to ADLS, impress in interviews! 🚀

---

**Date Created:** December 2025  
**Status:** Complete Tutorial - Ready to Learn!  
**Time to Complete:** 2-3 hours (local) + 15 min (ADLS setup)  
**Difficulty:** Beginner to Intermediate  
**Portfolio Value:** ⭐⭐⭐⭐⭐
