# Databricks Enterprise RAG System with Unity Catalog

[![Azure](https://img.shields.io/badge/Azure-Databricks-orange)](https://azure.microsoft.com/en-us/products/databricks)
[![Unity Catalog](https://img.shields.io/badge/Unity-Catalog-blue)](https://www.databricks.com/product/unity-catalog)
[![Delta Lake](https://img.shields.io/badge/Delta-Lake-green)](https://delta.io/)

## 🎯 Project Overview

Enterprise-grade RAG (Retrieval-Augmented Generation) system built on Azure Databricks with Unity Catalog for data governance, Delta Lake for reliable storage, and production-ready ML pipelines.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Azure Databricks                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                     Unity Catalog                              │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │  │
│  │  │  Metastore  │──│   Catalog   │──│   Schema    │          │  │
│  │  │   (Azure)   │  │ ai_systems  │  │rag_production│         │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘          │  │
│  │                           │                                    │  │
│  │         ┌─────────────────┼─────────────────┐                 │  │
│  │         ▼                 ▼                 ▼                 │  │
│  │  ┌───────────┐    ┌───────────┐    ┌───────────┐             │  │
│  │  │ documents │    │  chunks   │    │  vectors  │             │  │
│  │  │  (Delta)  │    │  (Delta)  │    │  (Delta)  │             │  │
│  │  └───────────┘    └───────────┘    └───────────┘             │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Processing Pipeline                         │  │
│  │  Document Ingestion → Chunking → Embedding → Vector Storage   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      RAG Query Flow                            │  │
│  │  User Query → Embed → Vector Search → Context → LLM → Answer  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## ✨ Key Features

- **Unity Catalog Integration**: Enterprise data governance with fine-grained access control
- **Delta Lake Storage**: ACID transactions, time travel, and optimized performance
- **Scalable Architecture**: Distributed processing with Apache Spark
- **Production ML Pipeline**: End-to-end document processing and embedding
- **Vector Search Ready**: Optimized storage for embedding vectors
- **Audit & Lineage**: Full data lineage tracking through Unity Catalog

## 📁 Project Structure

```
04-databricks-enterprise/
├── README.md                          # This file
├── SETUP_GUIDE.md                     # Detailed setup instructions
│
├── notebooks/                         # Databricks notebooks (exported)
│   ├── 01_unity_catalog_setup.sql     # Unity Catalog DDL
│   ├── 02_rag_data_pipeline.py        # Document processing pipeline
│   ├── 03_embedding_pipeline.py       # Embedding generation
│   └── 04_rag_query_demo.py           # RAG query demonstration
│
├── src/                               # Python modules
│   ├── __init__.py
│   ├── document_processor.py          # Document chunking logic
│   ├── embedding_service.py           # Embedding generation
│   └── unity_catalog_client.py        # Unity Catalog operations
│
├── config/
│   ├── catalog_config.py              # Catalog/schema configuration
│   └── spark_config.py                # Spark session configuration
│
├── tests/
│   └── test_rag_pipeline.py           # Unit tests
│
└── docs/
    ├── architecture.md                # Detailed architecture docs
    ├── unity_catalog_setup.md         # Setup documentation
    └── screenshots/                   # UI screenshots
```

## 🚀 Quick Start

### Prerequisites

- Azure subscription with Databricks workspace
- Unity Catalog enabled workspace
- Python 3.9+

### Setup

1. **Clone this repository**
   ```bash
   git clone https://github.com/yourusername/ai-architect-portfolio.git
   cd ai-architect-portfolio/projects/04-databricks-enterprise
   ```

2. **Import notebooks to Databricks**
   - Upload notebooks from `notebooks/` folder to your Databricks workspace

3. **Run Unity Catalog setup**
   ```sql
   -- Run 01_unity_catalog_setup.sql
   CREATE CATALOG ai_systems ...
   ```

4. **Execute the RAG pipeline**
   - Run notebooks 02-04 in sequence

## 📊 Data Schema

### documents
| Column | Type | Description |
|--------|------|-------------|
| doc_id | STRING | Unique document identifier |
| title | STRING | Document title |
| content | STRING | Full document content |
| source | STRING | Document source/origin |
| metadata | MAP<STRING,STRING> | Additional metadata |
| ingestion_timestamp | TIMESTAMP | When document was ingested |
| last_updated | TIMESTAMP | Last modification time |

### document_chunks
| Column | Type | Description |
|--------|------|-------------|
| chunk_id | STRING | Unique chunk identifier |
| doc_id | STRING | Parent document ID |
| chunk_text | STRING | Chunk content |
| chunk_index | INT | Position in document |
| token_count | INT | Number of tokens |
| metadata | MAP<STRING,STRING> | Chunk metadata |
| created_timestamp | TIMESTAMP | Creation time |

### document_vectors
| Column | Type | Description |
|--------|------|-------------|
| chunk_id | STRING | Reference to chunk |
| doc_id | STRING | Reference to document |
| embedding | ARRAY<FLOAT> | Vector embedding |
| embedding_model | STRING | Model used for embedding |
| text_preview | STRING | First N chars of text |
| created_timestamp | TIMESTAMP | Creation time |

## 🔧 Configuration

### Unity Catalog Settings

```python
CATALOG_CONFIG = {
    "catalog_name": "ai_systems",
    "schema_name": "rag_production",
    "storage_location": "abfss://unity-catalog-storage@dbstorageo4nkgp5awhmgo.dfs.core.windows.net/2503836992218403"
}
```

### Spark Configuration

```python
SPARK_CONFIG = {
    "spark.databricks.unity_catalog.enabled": "true",
    "spark.sql.adaptive.enabled": "true",
    "spark.sql.adaptive.coalescePartitions.enabled": "true"
}
```

## 📈 Performance Metrics

| Metric | Value |
|--------|-------|
| Document Ingestion | ~1000 docs/min |
| Chunk Processing | ~5000 chunks/min |
| Embedding Generation | ~100 embeddings/sec |
| Query Latency (p95) | <500ms |

## 🔐 Security Features

- **Unity Catalog RBAC**: Fine-grained access control at catalog/schema/table level
- **Data Lineage**: Full tracking of data transformations
- **Audit Logging**: All access and modifications logged
- **Encryption**: Data encrypted at rest and in transit

## 📚 Related Projects

- [03-nlp-transformers/rag-lancedb](../03-nlp-transformers/rag-lancedb) - LanceDB-based RAG implementation
- [08-capstone-rag-enterprise-assistant](../08-capstone-rag-enterprise-assistant) - Full enterprise RAG solution

## 🎓 Key Learnings

1. **Unity Catalog Architecture**: Metastores, catalogs, schemas, and their relationships
2. **Storage Credentials**: Service principal authentication for external storage
3. **External Locations**: Mapping storage paths to credentials
4. **Delta Lake Features**: ACID transactions, time travel, deletion vectors
5. **Spark Optimization**: Adaptive query execution, partition coalescing

## 📄 License

MIT License - see [LICENSE](../../LICENSE) for details

## 👤 Author

**Bruce Lanskiy**
- LinkedIn: [Your LinkedIn]
- GitHub: [Your GitHub]
- Portfolio: [Your Portfolio Site]

---

*Part of the AI Architect Portfolio - Demonstrating enterprise-grade ML systems on cloud platforms*
