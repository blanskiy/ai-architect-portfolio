# Databricks notebook source
# MAGIC %md
# MAGIC # RAG Query Demo
# MAGIC
# MAGIC This notebook demonstrates the complete RAG query flow:
# MAGIC 1. Receive user query
# MAGIC 2. Generate query embedding
# MAGIC 3. Retrieve similar chunks from Unity Catalog
# MAGIC 4. Generate response with context

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

# MAGIC %pip install sentence-transformers openai -q

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
import uuid
import builtins

# Get Spark session
spark = SparkSession.builder.getOrCreate()

# Configuration
CATALOG = "ai_systems"
SCHEMA = "rag_production"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_K = 5  # Number of results to retrieve

# Set default catalog and schema
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

print(f"Using: {CATALOG}.{SCHEMA}")

# COMMAND ----------

# Load embedding model
model = SentenceTransformer(EMBEDDING_MODEL)
print(f"Embedding model loaded: {EMBEDDING_MODEL}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## RAG Query System

# COMMAND ----------

class RAGQuerySystem:
    """RAG Query System using Unity Catalog"""
    
    def __init__(self, spark_session, embedding_model, top_k: int = 5):
        self.spark = spark_session
        self.model = embedding_model
        self.top_k = top_k
        self.query_history = []
    
    def generate_embedding(self, text: str) -> list:
        """Generate embedding for text"""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def cosine_similarity(self, vec1: list, vec2: list) -> float:
        """Calculate cosine similarity"""
        a = np.array(vec1)
        b = np.array(vec2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    
    def retrieve(self, query: str) -> list:
        """Retrieve relevant chunks for query"""
        start_time = datetime.now()
        
        # Generate query embedding
        query_embedding = self.generate_embedding(query)
        
        # Get all vectors (in production, use vector search)
        vectors_df = self.spark.sql("""
            SELECT 
                v.chunk_id,
                v.doc_id,
                v.embedding,
                v.text_preview,
                c.chunk_text,
                c.chunk_index,
                d.title as document_title,
                d.source
            FROM document_vectors v
            JOIN document_chunks c ON v.chunk_id = c.chunk_id
            JOIN documents d ON c.doc_id = d.doc_id
        """).collect()
        
        # Calculate similarities
        results = []
        for row in vectors_df:
            similarity = self.cosine_similarity(query_embedding, row.embedding)
            results.append({
                'chunk_id': row.chunk_id,
                'doc_id': row.doc_id,
                'document_title': row.document_title,
                'source': row.source,
                'chunk_text': row.chunk_text,
                'chunk_index': row.chunk_index,
                'similarity': similarity
            })
        
        # Sort by similarity and take top K
        results.sort(key=lambda x: x['similarity'], reverse=True)
        top_results = results[:self.top_k]
        
        # Calculate response time
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Log query
        self._log_query(query, len(top_results), response_time)
        
        return top_results
    
    def _log_query(self, query: str, num_results: int, response_time_ms: float):
        """Log query to queries_log table"""
        query_id = f"query_{uuid.uuid4().hex[:12]}"
        
        log_data = [(
            query_id,
            query,
            "demo_user",
            datetime.now(),
            num_results,
            response_time_ms,
            "semantic",
            {"model": EMBEDDING_MODEL, "top_k": str(self.top_k)}
        )]
        
        schema = StructType([
            StructField("query_id", StringType(), False),
            StructField("query_text", StringType(), True),
            StructField("user_id", StringType(), True),
            StructField("timestamp", TimestampType(), True),
            StructField("num_results", IntegerType(), True),
            StructField("response_time_ms", DoubleType(), True),
            StructField("search_type", StringType(), True),
            StructField("metadata", MapType(StringType(), StringType()), True)
        ])
        
        log_df = self.spark.createDataFrame(log_data, schema=schema)
        log_df.write.mode("append").saveAsTable("queries_log")
        
        self.query_history.append({
            'query_id': query_id,
            'query': query,
            'num_results': num_results,
            'response_time_ms': response_time_ms
        })
    
    def format_context(self, results: list) -> str:
        """Format retrieved results as context"""
        context_parts = []
        for i, r in enumerate(results, 1):
            context_parts.append(f"""
[Source {i}: {r['document_title']}]
{r['chunk_text']}
""")
        return "\n".join(context_parts)
    
    def generate_prompt(self, query: str, context: str) -> str:
        """Generate prompt for LLM"""
        return f"""Based on the following context, answer the question.

Context:
{context}

Question: {query}

Answer: """
    
    def query(self, query_text: str, show_sources: bool = True) -> dict:
        """Execute full RAG query"""
        # Retrieve relevant chunks
        results = self.retrieve(query_text)
        
        # Format context
        context = self.format_context(results)
        
        # Generate prompt
        prompt = self.generate_prompt(query_text, context)
        
        return {
            'query': query_text,
            'results': results,
            'context': context,
            'prompt': prompt,
            'num_results': len(results)
        }

# Initialize RAG system
rag = RAGQuerySystem(spark, model, top_k=TOP_K)
print("✅ RAG Query System initialized")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Demo Queries

# COMMAND ----------

# Test Query 1: RAG-related
query1 = "How does RAG reduce hallucination in AI systems?"
result1 = rag.query(query1)

print(f"Query: {query1}")
print("=" * 80)
print("\nRetrieved Sources:")
for i, r in enumerate(result1['results'], 1):
    print(f"\n{i}. [{r['similarity']:.4f}] {r['document_title']}")
    print(f"   {r['chunk_text'][:200]}...")

# COMMAND ----------

# Test Query 2: Machine Learning
query2 = "What are the different types of machine learning?"
result2 = rag.query(query2)

print(f"Query: {query2}")
print("=" * 80)
print("\nRetrieved Sources:")
for i, r in enumerate(result2['results'], 1):
    print(f"\n{i}. [{r['similarity']:.4f}] {r['document_title']}")
    print(f"   {r['chunk_text'][:200]}...")

# COMMAND ----------

# Test Query 3: Vector Databases
query3 = "What algorithms do vector databases use for similarity search?"
result3 = rag.query(query3)

print(f"Query: {query3}")
print("=" * 80)
print("\nRetrieved Sources:")
for i, r in enumerate(result3['results'], 1):
    print(f"\n{i}. [{r['similarity']:.4f}] {r['document_title']}")
    print(f"   {r['chunk_text'][:200]}...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## View Generated Context and Prompt

# COMMAND ----------

# Show full context for the RAG query
print("=" * 80)
print("GENERATED CONTEXT")
print("=" * 80)
print(result1['context'])

# COMMAND ----------

# Show the prompt that would be sent to LLM
print("=" * 80)
print("LLM PROMPT")
print("=" * 80)
print(result1['prompt'])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Query Analytics

# COMMAND ----------

# View recent queries
display(spark.sql("""
    SELECT 
        query_id,
        query_text,
        num_results,
        ROUND(response_time_ms, 2) as response_time_ms,
        search_type,
        timestamp
    FROM queries_log
    ORDER BY timestamp DESC
    LIMIT 10
"""))

# COMMAND ----------

# Query statistics
display(spark.sql("""
    SELECT 
        COUNT(*) as total_queries,
        ROUND(AVG(response_time_ms), 2) as avg_response_time_ms,
        ROUND(MIN(response_time_ms), 2) as min_response_time_ms,
        ROUND(MAX(response_time_ms), 2) as max_response_time_ms,
        ROUND(AVG(num_results), 1) as avg_results_returned
    FROM queries_log
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Interactive Query Function

# COMMAND ----------

def ask(question: str):
    """Interactive RAG query function"""
    print(f"\n{'='*80}")
    print(f"Question: {question}")
    print('='*80)
    
    result = rag.query(question)
    
    print(f"\nFound {result['num_results']} relevant sources:")
    print("-" * 40)
    
    for i, r in enumerate(result['results'], 1):
        print(f"\n📄 Source {i}: {r['document_title']}")
        print(f"   Relevance: {r['similarity']:.2%}")
        print(f"   Content: {r['chunk_text'][:150]}...")
    
    print(f"\n{'='*80}")
    print("Context prepared for LLM (first 500 chars):")
    print("-" * 40)
    print(result['context'][:500] + "...")
    
    return result

# COMMAND ----------

# Try it!
result = ask("What is transfer learning in NLP?")

# COMMAND ----------

# Another query
result = ask("How do neural networks learn?")

# COMMAND ----------

# MAGIC %md
# MAGIC ## System Metrics Summary

# COMMAND ----------

# View all system metrics
display(spark.sql("""
    SELECT 
        metric_name,
        metric_value,
        metadata['pipeline'] as pipeline,
        tags,
        timestamp
    FROM system_metrics
    ORDER BY timestamp DESC
"""))

# COMMAND ----------

ask("What is machine learning?")

# COMMAND ----------

ask("What algorithms do vector databases use?")

# COMMAND ----------

# MAGIC %md
# MAGIC ## RAG Demo Complete! ✅
# MAGIC
# MAGIC This demonstration showed:
# MAGIC
# MAGIC 1. **Semantic Search**: Query embedding + cosine similarity
# MAGIC 2. **Context Retrieval**: Top-K relevant chunks from Unity Catalog
# MAGIC 3. **Prompt Generation**: Formatted context for LLM input
# MAGIC 4. **Query Logging**: All queries tracked in queries_log table
# MAGIC 5. **Analytics**: Query performance metrics
# MAGIC
# MAGIC ### Next Steps for Production:
# MAGIC - Use Databricks Vector Search for scalable similarity search
# MAGIC - Integrate with Azure OpenAI for response generation
# MAGIC - Add re-ranking for improved relevance
# MAGIC - Implement caching for frequent queries
# MAGIC - Set up monitoring and alerting