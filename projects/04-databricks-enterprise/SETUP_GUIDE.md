# Unity Catalog RAG System - Setup Guide

## 📋 Overview

This guide walks through setting up the enterprise RAG system with Unity Catalog on Azure Databricks.

## 🔧 Prerequisites

- Azure subscription with Databricks workspace
- Unity Catalog enabled on workspace
- Databricks Runtime 14.0+ (LTS recommended)

## 📁 Files Included

```
notebooks/
├── 01_unity_catalog_setup.sql     # Creates catalog, schema, tables
├── 02_rag_data_pipeline.py        # Document processing pipeline
├── 03_embedding_pipeline.py       # Generates vector embeddings
└── 04_rag_query_demo.py           # RAG query demonstration
```

## 🚀 Setup Steps

### Step 1: Import Notebooks to Databricks

1. Go to your Databricks workspace
2. Navigate to **Workspace** in the left menu
3. Right-click on your user folder
4. Select **Import**
5. Upload each notebook file

### Step 2: Create Compute Cluster

1. Go to **Compute** → **Create Compute**
2. Configure:
   - **Name**: `rag-pipeline-cluster`
   - **Single Node**: Yes (for development)
   - **Databricks Runtime**: `14.3 LTS`
   - **Node Type**: `Standard_DS3_v2`
3. Click **Create Compute**
4. Wait for cluster to start (~3-5 minutes)

### Step 3: Run Unity Catalog Setup

1. Open `01_unity_catalog_setup.sql`
2. Attach to your cluster
3. Run all cells
4. Verify tables are created:
   ```sql
   SHOW TABLES IN ai_systems.rag_production;
   ```

### Step 4: Run Data Pipeline

1. Open `02_rag_data_pipeline.py`
2. Attach to your cluster
3. Run all cells
4. Verify documents and chunks are created:
   ```sql
   SELECT COUNT(*) FROM ai_systems.rag_production.documents;
   SELECT COUNT(*) FROM ai_systems.rag_production.document_chunks;
   ```

### Step 5: Generate Embeddings

1. Open `03_embedding_pipeline.py`
2. Attach to your cluster
3. Run all cells (first run will install sentence-transformers)
4. Verify vectors are created:
   ```sql
   SELECT COUNT(*) FROM ai_systems.rag_production.document_vectors;
   ```

### Step 6: Test RAG Queries

1. Open `04_rag_query_demo.py`
2. Attach to your cluster
3. Run cells to test queries
4. Use the `ask()` function for interactive queries:
   ```python
   ask("What is machine learning?")
   ```

## 📊 Data Schema

### documents
| Column | Type | Description |
|--------|------|-------------|
| doc_id | STRING | Unique document identifier |
| title | STRING | Document title |
| content | STRING | Full document content |
| source | STRING | Document source |
| metadata | MAP | Additional metadata |
| ingestion_timestamp | TIMESTAMP | Ingestion time |
| last_updated | TIMESTAMP | Last update time |

### document_chunks
| Column | Type | Description |
|--------|------|-------------|
| chunk_id | STRING | Unique chunk identifier |
| doc_id | STRING | Parent document ID |
| chunk_text | STRING | Chunk content |
| chunk_index | INT | Position in document |
| token_count | INT | Token count |
| metadata | MAP | Chunk metadata |
| created_timestamp | TIMESTAMP | Creation time |

### document_vectors
| Column | Type | Description |
|--------|------|-------------|
| chunk_id | STRING | Reference to chunk |
| doc_id | STRING | Reference to document |
| embedding | ARRAY<FLOAT> | Vector embedding |
| embedding_model | STRING | Model used |
| text_preview | STRING | Text preview |
| created_timestamp | TIMESTAMP | Creation time |

### queries_log
| Column | Type | Description |
|--------|------|-------------|
| query_id | STRING | Unique query ID |
| query_text | STRING | User query |
| user_id | STRING | User identifier |
| timestamp | TIMESTAMP | Query time |
| num_results | INT | Results returned |
| response_time_ms | DOUBLE | Response time |
| search_type | STRING | Search type |
| metadata | MAP | Query metadata |

### system_metrics
| Column | Type | Description |
|--------|------|-------------|
| metric_id | STRING | Metric identifier |
| metric_name | STRING | Metric name |
| metric_value | DOUBLE | Metric value |
| timestamp | TIMESTAMP | Recording time |
| metadata | MAP | Metric context |
| tags | MAP | Metric tags |

## ⚙️ Configuration

### Managed Storage Location

The system uses Databricks-managed storage:
```
abfss://unity-catalog-storage@dbstorageo4nkgp5awhmgo.dfs.core.windows.net/2503836992218403/
```

### Embedding Model

Default: `all-MiniLM-L6-v2` (384 dimensions)
- Fast inference
- Good for semantic search
- Suitable for English text

To change model, update in notebook:
```python
EMBEDDING_MODEL = "your-model-name"
```

## 🔍 Troubleshooting

### Error: "Metastore storage root URL does not exist"
**Solution**: Specify `MANAGED LOCATION` when creating catalog:
```sql
CREATE CATALOG ai_systems
MANAGED LOCATION 'abfss://unity-catalog-storage@...'
```

### Error: "PARSE_SYNTAX_ERROR" on CREATE STORAGE CREDENTIAL
**Solution**: Use managed storage instead of external credentials. The notebooks are configured to work with managed storage.

### Error: pip install fails
**Solution**: Add `%pip install package -q` at the top of the notebook and restart Python.

### Slow embedding generation
**Solution**: 
- Use batch processing (already implemented)
- Consider using GPU cluster for large datasets
- Use smaller embedding model

## 📈 Performance Tips

1. **Batch Processing**: Process documents in batches of 32-64
2. **Partitioning**: Partition large tables by date or source
3. **Caching**: Cache frequently accessed DataFrames
4. **Index Optimization**: Let Delta Lake auto-optimize

## 🔐 Security Considerations

1. **Access Control**: Use Unity Catalog grants for table access
2. **Data Encryption**: Delta Lake encrypts data at rest
3. **Audit Logging**: All queries logged to queries_log table
4. **Lineage Tracking**: Unity Catalog tracks data lineage

## 📚 Next Steps

1. **Scale Up**: Add more documents to the system
2. **Vector Search**: Implement Databricks Vector Search for production
3. **LLM Integration**: Connect to Azure OpenAI for response generation
4. **Monitoring**: Set up dashboards for system metrics
5. **CI/CD**: Implement notebook versioning with Databricks Repos

## 🆘 Support

For issues with:
- **Databricks**: Check Databricks documentation
- **Unity Catalog**: Review Unity Catalog guides
- **This project**: Open an issue on GitHub

---

*Setup guide for the Databricks Enterprise RAG System with Unity Catalog*
