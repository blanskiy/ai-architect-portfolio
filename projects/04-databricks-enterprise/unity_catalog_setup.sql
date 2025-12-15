
-- ============================================================
-- Unity Catalog Setup: ai_systems
-- Environment: development
-- Generated for: Enterprise RAG System
-- ============================================================


-- Create Catalog
CREATE CATALOG IF NOT EXISTS ai_systems
COMMENT 'AI and ML systems catalog'
MANAGED LOCATION 'abfss://databricks-data@azlancedb.dfs.core.windows.net/catalogs/ai_systems';


-- Schema: rag_production

-- Create Schema
CREATE SCHEMA IF NOT EXISTS ai_systems.rag_production
COMMENT 'Production RAG system schema'
MANAGED LOCATION 'abfss://databricks-data@azlancedb.dfs.core.windows.net/catalogs/ai_systems/rag_production';


-- Create Table: documents
CREATE TABLE IF NOT EXISTS ai_systems.rag_production.documents (
  doc_id STRING COMMENT 'Unique document identifier',  title STRING COMMENT 'Document title',  content STRING COMMENT 'Full document content',  source STRING COMMENT 'Document source (PDF, URL, etc)',  metadata MAP<STRING, STRING> COMMENT 'Additional metadata',  ingestion_timestamp TIMESTAMP COMMENT 'When document was ingested',  last_updated TIMESTAMP COMMENT 'Last update timestamp'
)
USING DELTA
COMMENT 'Source documents for RAG system'
LOCATION 'abfss://databricks-data@azlancedb.dfs.core.windows.net/catalogs/ai_systems/rag_production/documents'
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true', 'delta.minReaderVersion' = '1', 'delta.minWriterVersion' = '2');


-- Create Table: document_chunks
CREATE TABLE IF NOT EXISTS ai_systems.rag_production.document_chunks (
  chunk_id STRING COMMENT 'Unique chunk identifier',  doc_id STRING COMMENT 'Parent document ID',  chunk_text STRING COMMENT 'Chunk content',  chunk_index INT COMMENT 'Position in document',  token_count INT COMMENT 'Number of tokens in chunk',  metadata MAP<STRING, STRING> COMMENT 'Chunk metadata',  created_timestamp TIMESTAMP COMMENT 'Creation timestamp'
)
USING DELTA
COMMENT 'Chunked documents for RAG retrieval'
LOCATION 'abfss://databricks-data@azlancedb.dfs.core.windows.net/catalogs/ai_systems/rag_production/document_chunks'
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');


-- Create Table: document_vectors
CREATE TABLE IF NOT EXISTS ai_systems.rag_production.document_vectors (
  chunk_id STRING COMMENT 'Reference to chunk',  doc_id STRING COMMENT 'Reference to document',  embedding ARRAY<FLOAT> COMMENT 'Vector embedding (768-dim)',  embedding_model STRING COMMENT 'Model used for embedding',  text_preview STRING COMMENT 'First 100 chars of chunk',  created_timestamp TIMESTAMP COMMENT 'Creation timestamp'
)
USING DELTA
COMMENT 'Vector embeddings for document chunks'
LOCATION 'abfss://databricks-data@azlancedb.dfs.core.windows.net/catalogs/ai_systems/rag_production/document_vectors'
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');


-- Create Table: queries_log
CREATE TABLE IF NOT EXISTS ai_systems.rag_production.queries_log (
  query_id STRING COMMENT 'Unique query identifier',  query_text STRING COMMENT 'User query',  query_embedding ARRAY<FLOAT> COMMENT 'Query vector',  top_k INT COMMENT 'Number of results requested',  results_count INT COMMENT 'Number of results returned',  latency_ms DOUBLE COMMENT 'Query latency in milliseconds',  user_id STRING COMMENT 'User who made query',  timestamp TIMESTAMP COMMENT 'Query timestamp'
)
USING DELTA
COMMENT 'Audit log of all RAG queries'
LOCATION 'abfss://databricks-data@azlancedb.dfs.core.windows.net/catalogs/ai_systems/rag_production/queries_log'
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true', 'delta.deletedFileRetentionDuration' = 'interval 30 days');


-- Create Table: system_metrics
CREATE TABLE IF NOT EXISTS ai_systems.rag_production.system_metrics (
  metric_id STRING COMMENT 'Metric identifier',  metric_name STRING COMMENT 'Metric name',  metric_value DOUBLE COMMENT 'Metric value',  metric_unit STRING COMMENT 'Unit of measurement',  tags MAP<STRING, STRING> COMMENT 'Metric tags',  timestamp TIMESTAMP COMMENT 'Metric timestamp'
)
USING DELTA
COMMENT 'System performance metrics'
LOCATION 'abfss://databricks-data@azlancedb.dfs.core.windows.net/catalogs/ai_systems/rag_production/system_metrics'
;


-- Grant Permissions
GRANT USE CATALOG ON CATALOG ai_systems TO `account users`;
GRANT USE SCHEMA ON SCHEMA ai_systems.rag_production TO `account users`;
GRANT SELECT ON SCHEMA ai_systems.rag_production TO `account users`;


-- ============================================================
-- Setup Complete
-- ============================================================
-- To verify, run:
-- SHOW CATALOGS;
-- SHOW SCHEMAS IN ai_systems;
-- SHOW TABLES IN ai_systems.rag_production;
-- ============================================================
