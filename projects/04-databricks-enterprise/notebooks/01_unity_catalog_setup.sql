-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Unity Catalog Setup for RAG System
-- MAGIC 
-- MAGIC This notebook sets up the Unity Catalog structure for the enterprise RAG system.
-- MAGIC 
-- MAGIC ## Prerequisites
-- MAGIC - Unity Catalog enabled workspace
-- MAGIC - Appropriate permissions to create catalogs and schemas
-- MAGIC 
-- MAGIC ## Structure Created
-- MAGIC ```
-- MAGIC ai_systems (Catalog)
-- MAGIC └── rag_production (Schema)
-- MAGIC     ├── documents
-- MAGIC     ├── document_chunks
-- MAGIC     ├── document_vectors
-- MAGIC     ├── queries_log
-- MAGIC     └── system_metrics
-- MAGIC ```

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 1: Create Catalog

-- COMMAND ----------

-- Create catalog with managed location (using Databricks-managed storage)
CREATE CATALOG IF NOT EXISTS ai_systems
MANAGED LOCATION 'abfss://unity-catalog-storage@dbstorageo4nkgp5awhmgo.dfs.core.windows.net/2503836992218403/catalogs/ai_systems'
COMMENT 'AI and ML systems catalog for enterprise RAG';

-- COMMAND ----------

-- Verify catalog created
SHOW CATALOGS;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 2: Create Schema

-- COMMAND ----------

USE CATALOG ai_systems;

CREATE SCHEMA IF NOT EXISTS rag_production
MANAGED LOCATION 'abfss://unity-catalog-storage@dbstorageo4nkgp5awhmgo.dfs.core.windows.net/2503836992218403/catalogs/ai_systems/rag_production'
COMMENT 'Production RAG system schema with document storage and vector embeddings';

-- COMMAND ----------

-- Verify schema created
SHOW SCHEMAS IN ai_systems;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 3: Create Tables

-- COMMAND ----------

USE CATALOG ai_systems;
USE SCHEMA rag_production;

-- Table 1: Main documents table
CREATE TABLE IF NOT EXISTS documents (
    doc_id STRING NOT NULL COMMENT 'Unique document identifier',
    title STRING COMMENT 'Document title',
    content STRING COMMENT 'Full document content',
    source STRING COMMENT 'Document source (file path, URL, etc.)',
    metadata MAP<STRING, STRING> COMMENT 'Additional metadata key-value pairs',
    ingestion_timestamp TIMESTAMP COMMENT 'When document was ingested',
    last_updated TIMESTAMP COMMENT 'Last modification timestamp'
)
USING DELTA
COMMENT 'Main documents table storing original documents for RAG system'
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
);

-- COMMAND ----------

-- Table 2: Document chunks for retrieval
CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id STRING NOT NULL COMMENT 'Unique chunk identifier',
    doc_id STRING NOT NULL COMMENT 'Parent document ID (foreign key)',
    chunk_text STRING COMMENT 'Chunk text content',
    chunk_index INT COMMENT 'Position of chunk in original document',
    token_count INT COMMENT 'Number of tokens in chunk',
    metadata MAP<STRING, STRING> COMMENT 'Chunk-specific metadata',
    created_timestamp TIMESTAMP COMMENT 'When chunk was created'
)
USING DELTA
COMMENT 'Document chunks optimized for RAG retrieval'
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true'
);

-- COMMAND ----------

-- Table 3: Vector embeddings
CREATE TABLE IF NOT EXISTS document_vectors (
    chunk_id STRING NOT NULL COMMENT 'Reference to chunk',
    doc_id STRING NOT NULL COMMENT 'Reference to document',
    embedding ARRAY<FLOAT> COMMENT 'Vector embedding (typically 384-1536 dimensions)',
    embedding_model STRING COMMENT 'Model used to generate embedding',
    text_preview STRING COMMENT 'First N characters of source text',
    created_timestamp TIMESTAMP COMMENT 'When embedding was created'
)
USING DELTA
COMMENT 'Vector embeddings for semantic search'
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true'
);

-- COMMAND ----------

-- Table 4: Query audit log
CREATE TABLE IF NOT EXISTS queries_log (
    query_id STRING NOT NULL COMMENT 'Unique query identifier',
    query_text STRING COMMENT 'User query text',
    user_id STRING COMMENT 'User who made the query',
    timestamp TIMESTAMP COMMENT 'Query timestamp',
    num_results INT COMMENT 'Number of results returned',
    response_time_ms DOUBLE COMMENT 'Query response time in milliseconds',
    search_type STRING COMMENT 'Type of search (semantic, keyword, hybrid)',
    metadata MAP<STRING, STRING> COMMENT 'Additional query metadata'
)
USING DELTA
COMMENT 'Audit log for RAG queries - for monitoring and analysis'
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true'
);

-- COMMAND ----------

-- Table 5: System metrics
CREATE TABLE IF NOT EXISTS system_metrics (
    metric_id STRING NOT NULL COMMENT 'Unique metric identifier',
    metric_name STRING COMMENT 'Name of the metric',
    metric_value DOUBLE COMMENT 'Metric value',
    timestamp TIMESTAMP COMMENT 'When metric was recorded',
    metadata MAP<STRING, STRING> COMMENT 'Additional context',
    tags MAP<STRING, STRING> COMMENT 'Tags for filtering'
)
USING DELTA
COMMENT 'System performance and health metrics'
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true'
);

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 4: Verify Tables Created

-- COMMAND ----------

-- List all tables
SHOW TABLES IN ai_systems.rag_production;

-- COMMAND ----------

-- Describe each table
DESCRIBE EXTENDED ai_systems.rag_production.documents;

-- COMMAND ----------

DESCRIBE EXTENDED ai_systems.rag_production.document_chunks;

-- COMMAND ----------

DESCRIBE EXTENDED ai_systems.rag_production.document_vectors;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 5: Insert Test Data

-- COMMAND ----------

-- Insert sample documents
INSERT INTO ai_systems.rag_production.documents VALUES
    ('doc_001', 'Introduction to RAG Systems', 'RAG (Retrieval-Augmented Generation) combines the power of large language models with external knowledge retrieval. This approach allows AI systems to access up-to-date information and provide more accurate responses.', 'manual_entry', map('category', 'ai', 'level', 'introduction'), current_timestamp(), current_timestamp()),
    ('doc_002', 'Vector Embeddings Explained', 'Vector embeddings are numerical representations of text that capture semantic meaning. They enable machines to understand similarity between concepts and perform semantic search.', 'manual_entry', map('category', 'ml', 'level', 'intermediate'), current_timestamp(), current_timestamp()),
    ('doc_003', 'Unity Catalog Best Practices', 'Unity Catalog provides centralized governance for data and AI assets. Best practices include organizing data into logical catalogs, implementing proper access controls, and enabling data lineage tracking.', 'manual_entry', map('category', 'databricks', 'level', 'advanced'), current_timestamp(), current_timestamp());

-- COMMAND ----------

-- Insert sample chunks
INSERT INTO ai_systems.rag_production.document_chunks VALUES
    ('chunk_001', 'doc_001', 'RAG (Retrieval-Augmented Generation) combines the power of large language models with external knowledge retrieval.', 0, 18, map('section', 'intro'), current_timestamp()),
    ('chunk_002', 'doc_001', 'This approach allows AI systems to access up-to-date information and provide more accurate responses.', 1, 16, map('section', 'benefits'), current_timestamp()),
    ('chunk_003', 'doc_002', 'Vector embeddings are numerical representations of text that capture semantic meaning.', 0, 12, map('section', 'definition'), current_timestamp()),
    ('chunk_004', 'doc_002', 'They enable machines to understand similarity between concepts and perform semantic search.', 1, 13, map('section', 'application'), current_timestamp()),
    ('chunk_005', 'doc_003', 'Unity Catalog provides centralized governance for data and AI assets.', 0, 11, map('section', 'overview'), current_timestamp());

-- COMMAND ----------

-- Insert sample vectors (simplified 8-dimensional for demo)
INSERT INTO ai_systems.rag_production.document_vectors VALUES
    ('chunk_001', 'doc_001', array(0.12, 0.45, 0.78, 0.23, 0.56, 0.89, 0.34, 0.67), 'demo-model-v1', 'RAG (Retrieval-Augmented Generation)...', current_timestamp()),
    ('chunk_002', 'doc_001', array(0.23, 0.56, 0.89, 0.12, 0.45, 0.78, 0.91, 0.34), 'demo-model-v1', 'This approach allows AI systems...', current_timestamp()),
    ('chunk_003', 'doc_002', array(0.34, 0.67, 0.12, 0.45, 0.78, 0.23, 0.56, 0.89), 'demo-model-v1', 'Vector embeddings are numerical...', current_timestamp()),
    ('chunk_004', 'doc_002', array(0.45, 0.78, 0.23, 0.56, 0.89, 0.12, 0.67, 0.34), 'demo-model-v1', 'They enable machines to understand...', current_timestamp()),
    ('chunk_005', 'doc_003', array(0.56, 0.89, 0.34, 0.67, 0.12, 0.45, 0.78, 0.23), 'demo-model-v1', 'Unity Catalog provides centralized...', current_timestamp());

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Step 6: Query Test Data

-- COMMAND ----------

-- Count documents
SELECT COUNT(*) as document_count FROM ai_systems.rag_production.documents;

-- COMMAND ----------

-- View all documents
SELECT doc_id, title, source, ingestion_timestamp 
FROM ai_systems.rag_production.documents;

-- COMMAND ----------

-- View chunks with document info
SELECT 
    c.chunk_id,
    c.chunk_index,
    d.title as document_title,
    c.chunk_text,
    c.token_count
FROM ai_systems.rag_production.document_chunks c
JOIN ai_systems.rag_production.documents d ON c.doc_id = d.doc_id
ORDER BY d.doc_id, c.chunk_index;

-- COMMAND ----------

-- View vectors
SELECT 
    v.chunk_id,
    v.text_preview,
    v.embedding_model,
    size(v.embedding) as embedding_dimensions
FROM ai_systems.rag_production.document_vectors v;

-- COMMAND ----------

-- MAGIC %md
-- MAGIC ## Setup Complete! ✅
-- MAGIC 
-- MAGIC Unity Catalog RAG system is now ready:
-- MAGIC - Catalog: `ai_systems`
-- MAGIC - Schema: `rag_production`
-- MAGIC - Tables: `documents`, `document_chunks`, `document_vectors`, `queries_log`, `system_metrics`
-- MAGIC - Test data: 3 documents, 5 chunks, 5 vectors
