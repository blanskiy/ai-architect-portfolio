# Databricks notebook source
# MAGIC %md
# MAGIC # Embedding Pipeline
# MAGIC
# MAGIC This notebook generates vector embeddings for document chunks using sentence transformers.
# MAGIC
# MAGIC ## Pipeline Steps:
# MAGIC 1. Load chunks from Unity Catalog
# MAGIC 2. Generate embeddings using sentence-transformers
# MAGIC 3. Store vectors in document_vectors table

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

# Install sentence-transformers (if needed)
# Install required packages with compatible versions
%pip install typing_extensions>=4.5.0 sentence-transformers -q

# COMMAND ----------

# Restart Python to load new packages
dbutils.library.restartPython()

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from sentence_transformers import SentenceTransformer
from datetime import datetime
import numpy as np

# Get Spark session
spark = SparkSession.builder.getOrCreate()

# Configuration
CATALOG = "ai_systems"
SCHEMA = "rag_production"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 384 dimensions, fast and efficient

# Set default catalog and schema
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

print(f"Using: {CATALOG}.{SCHEMA}")
print(f"Embedding model: {EMBEDDING_MODEL}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Embedding Model

# COMMAND ----------

# Load the sentence transformer model
model = SentenceTransformer(EMBEDDING_MODEL)
embedding_dim = model.get_sentence_embedding_dimension()

print(f"Model loaded: {EMBEDDING_MODEL}")
print(f"Embedding dimensions: {embedding_dim}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Chunks Without Embeddings

# COMMAND ----------

# Get chunks that don't have embeddings yet
chunks_df = spark.sql("""
    SELECT c.chunk_id, c.doc_id, c.chunk_text
    FROM document_chunks c
    LEFT JOIN document_vectors v ON c.chunk_id = v.chunk_id
    WHERE v.chunk_id IS NULL
    AND c.chunk_text IS NOT NULL
    AND LENGTH(c.chunk_text) > 0
""")

chunks_to_process = chunks_df.collect()
print(f"Chunks to process: {len(chunks_to_process)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Embeddings

# COMMAND ----------

def generate_embedding(text: str) -> list:
    """Generate embedding for a single text"""
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()

def get_text_preview(text: str, max_length: int = 100) -> str:
    """Get preview of text"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

# COMMAND ----------

# Process chunks and generate embeddings
vectors_data = []
batch_size = 32
total = len(chunks_to_process)

print(f"Processing {total} chunks...")

# Process in batches for efficiency
for i in range(0, total, batch_size):
    batch = chunks_to_process[i:i+batch_size]
    texts = [row.chunk_text for row in batch]
    
    # Generate embeddings for batch
    embeddings = model.encode(texts, convert_to_numpy=True)
    
    # Create records
    for j, row in enumerate(batch):
        vectors_data.append({
            'chunk_id': row.chunk_id,
            'doc_id': row.doc_id,
            'embedding': embeddings[j].tolist(),
            'embedding_model': EMBEDDING_MODEL,
            'text_preview': get_text_preview(row.chunk_text),
            'created_timestamp': datetime.now()
        })
    
    # Progress update
    processed = min(i + batch_size, total)
    print(f"Processed {processed}/{total} chunks ({(processed/total)*100:.1f}%)")

print(f"✅ Generated {len(vectors_data)} embeddings")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Store Embeddings in Unity Catalog

# COMMAND ----------

# Define schema for vectors table
vector_schema = StructType([
    StructField("chunk_id", StringType(), False),
    StructField("doc_id", StringType(), False),
    StructField("embedding", ArrayType(FloatType()), True),
    StructField("embedding_model", StringType(), True),
    StructField("text_preview", StringType(), True),
    StructField("created_timestamp", TimestampType(), True)
])

# Convert to DataFrame
vectors_df = spark.createDataFrame(vectors_data, schema=vector_schema)

print(f"Vectors DataFrame: {vectors_df.count()} rows")
print(f"Embedding dimensions: {len(vectors_data[0]['embedding']) if vectors_data else 0}")

# COMMAND ----------

# Insert vectors
vectors_df.write.mode("append").saveAsTable("document_vectors")
print("✅ Vectors stored in document_vectors table")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Embeddings

# COMMAND ----------

# Count total vectors
vector_count = spark.sql("SELECT COUNT(*) as count FROM document_vectors").collect()[0]["count"]
print(f"Total vectors in table: {vector_count}")

# COMMAND ----------

# View vector statistics
display(spark.sql("""
    SELECT 
        embedding_model,
        COUNT(*) as vector_count,
        MIN(created_timestamp) as earliest,
        MAX(created_timestamp) as latest
    FROM document_vectors
    GROUP BY embedding_model
"""))

# COMMAND ----------

# View vectors with document info
display(spark.sql("""
    SELECT 
        v.chunk_id,
        d.title as document_title,
        v.text_preview,
        v.embedding_model,
        SIZE(v.embedding) as embedding_dimensions
    FROM document_vectors v
    JOIN document_chunks c ON v.chunk_id = c.chunk_id
    JOIN documents d ON c.doc_id = d.doc_id
    LIMIT 10
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test Vector Similarity (Basic)

# COMMAND ----------

def cosine_similarity(vec1: list, vec2: list) -> float:
    """Calculate cosine similarity between two vectors"""
    a = np.array(vec1)
    b = np.array(vec2)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# COMMAND ----------

# Test query
test_query = "How does RAG work with language models?"
query_embedding = generate_embedding(test_query)

print(f"Query: {test_query}")
print(f"Query embedding shape: {len(query_embedding)}")

# COMMAND ----------

# Simple similarity search (in-memory for demo)
# In production, use a vector database or Databricks Vector Search

all_vectors = spark.sql("""
    SELECT v.chunk_id, v.embedding, v.text_preview, d.title
    FROM document_vectors v
    JOIN document_chunks c ON v.chunk_id = c.chunk_id
    JOIN documents d ON c.doc_id = d.doc_id
""").collect()

# Calculate similarities
results = []
for row in all_vectors:
    similarity = cosine_similarity(query_embedding, row.embedding)
    results.append({
        'chunk_id': row.chunk_id,
        'title': row.title,
        'text_preview': row.text_preview,
        'similarity': similarity
    })

# Sort by similarity
results.sort(key=lambda x: x['similarity'], reverse=True)

# Display top results
print(f"\nTop 5 results for: '{test_query}'")
print("-" * 80)
for i, r in enumerate(results[:5]):
    print(f"{i+1}. [{r['similarity']:.4f}] {r['title']}")
    print(f"   {r['text_preview']}")
    print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Log Embedding Metrics

# COMMAND ----------

import uuid

# Log metrics
metrics_data = [
    (f"metric_{uuid.uuid4().hex[:8]}", "vectors_generated", float(len(vectors_data)), datetime.now(), {"pipeline": "embedding"}, {"model": EMBEDDING_MODEL}),
    (f"metric_{uuid.uuid4().hex[:8]}", "embedding_dimensions", float(embedding_dim), datetime.now(), {"pipeline": "embedding"}, {"model": EMBEDDING_MODEL})
]

metrics_schema = StructType([
    StructField("metric_id", StringType(), False),
    StructField("metric_name", StringType(), True),
    StructField("metric_value", DoubleType(), True),
    StructField("timestamp", TimestampType(), True),
    StructField("metadata", MapType(StringType(), StringType()), True),
    StructField("tags", MapType(StringType(), StringType()), True)
])

metrics_df = spark.createDataFrame(metrics_data, schema=metrics_schema)
metrics_df.write.mode("append").saveAsTable("system_metrics")

print("✅ Embedding metrics logged")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pipeline Complete! ✅
# MAGIC
# MAGIC Successfully generated and stored:
# MAGIC - Vector embeddings for all document chunks
# MAGIC - Using model: `all-MiniLM-L6-v2` (384 dimensions)
# MAGIC - Verified similarity search works
# MAGIC
# MAGIC Next step: Run the RAG query demo to test end-to-end retrieval