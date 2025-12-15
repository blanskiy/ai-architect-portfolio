# Databricks notebook source
# MAGIC %md
# MAGIC # RAG Data Pipeline
# MAGIC
# MAGIC This notebook implements the document processing pipeline for the RAG system:
# MAGIC 1. Document ingestion
# MAGIC 2. Text chunking
# MAGIC 3. Metadata extraction
# MAGIC 4. Storage to Unity Catalog

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from datetime import datetime
import uuid
import re

# Get Spark session
spark = SparkSession.builder.getOrCreate()

# Configuration
CATALOG = "ai_systems"
SCHEMA = "rag_production"

# Set default catalog and schema
spark.sql(f"USE CATALOG {CATALOG}")
spark.sql(f"USE SCHEMA {SCHEMA}")

print(f"Using: {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Document Processing Functions

# COMMAND ----------

class DocumentProcessor:
    """Process documents for RAG system"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def generate_id(self, prefix: str = "doc") -> str:
        """Generate unique ID"""
        return f"{prefix}_{uuid.uuid4().hex[:12]}"
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s.,!?;:\-\'"()]', '', text)
        return text.strip()
    
    def chunk_text(self, text: str, doc_id: str) -> list:
        """Split text into overlapping chunks"""
        if not text:
            return []
        
        words = text.split()
        chunks = []
        
        i = 0
        chunk_index = 0
        
        while i < len(words):
            # Get chunk of words
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = ' '.join(chunk_words)
            
            # Create chunk record
            chunk = {
                'chunk_id': self.generate_id('chunk'),
                'doc_id': doc_id,
                'chunk_text': chunk_text,
                'chunk_index': chunk_index,
                'token_count': len(chunk_words),
                'created_timestamp': datetime.now()
            }
            chunks.append(chunk)
            
            # Move forward with overlap
            i += self.chunk_size - self.chunk_overlap
            chunk_index += 1
        
        return chunks
    
    def process_document(self, title: str, content: str, source: str, 
                         metadata: dict = None) -> tuple:
        """Process a single document and return document + chunks"""
        doc_id = self.generate_id('doc')
        clean_content = self.clean_text(content)
        
        # Create document record
        document = {
            'doc_id': doc_id,
            'title': title,
            'content': clean_content,
            'source': source,
            'metadata': metadata or {},
            'ingestion_timestamp': datetime.now(),
            'last_updated': datetime.now()
        }
        
        # Create chunks
        chunks = self.chunk_text(clean_content, doc_id)
        
        return document, chunks

# Initialize processor
processor = DocumentProcessor(chunk_size=100, chunk_overlap=20)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Sample Documents for Ingestion

# COMMAND ----------

# Sample documents to ingest
sample_documents = [
    {
        "title": "Introduction to Machine Learning",
        "content": """Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. 
        It focuses on developing algorithms that can access data and use it to learn for themselves. 
        The process begins with observations or data, such as examples, direct experience, or instruction, to look for patterns in data and make better decisions in the future.
        The primary aim is to allow computers to learn automatically without human intervention and adjust actions accordingly.
        Machine learning algorithms are often categorized as supervised, unsupervised, or reinforcement learning.
        Supervised learning algorithms learn from labeled training data, while unsupervised learning finds hidden patterns in data without labels.
        Reinforcement learning trains agents to make sequences of decisions by rewarding desired behaviors.""",
        "source": "ml_fundamentals",
        "metadata": {"category": "ai", "level": "beginner", "topic": "machine_learning"}
    },
    {
        "title": "Deep Learning Neural Networks",
        "content": """Deep learning is part of a broader family of machine learning methods based on artificial neural networks with representation learning.
        Learning can be supervised, semi-supervised or unsupervised.
        Deep learning architectures such as deep neural networks, recurrent neural networks, convolutional neural networks and transformers have been applied to many fields.
        These architectures have produced results comparable to and in some cases surpassing human expert performance.
        The word deep refers to the number of layers through which the data is transformed.
        More precisely, deep learning systems have a substantial credit assignment path depth.
        Neural networks are computing systems inspired by biological neural networks that constitute animal brains.
        An artificial neural network consists of a collection of connected nodes called artificial neurons.""",
        "source": "deep_learning_guide",
        "metadata": {"category": "ai", "level": "intermediate", "topic": "deep_learning"}
    },
    {
        "title": "Natural Language Processing Fundamentals",
        "content": """Natural Language Processing (NLP) is a field of artificial intelligence that gives machines the ability to read, understand, and derive meaning from human languages.
        NLP combines computational linguistics with machine learning and deep learning models.
        Key NLP tasks include text classification, named entity recognition, sentiment analysis, machine translation, and question answering.
        Modern NLP heavily relies on transformer architectures, which use attention mechanisms to process sequential data.
        BERT, GPT, and T5 are examples of transformer-based models that have revolutionized NLP.
        Word embeddings like Word2Vec and GloVe represent words as dense vectors capturing semantic relationships.
        Transfer learning has enabled NLP models to be pre-trained on large corpora and fine-tuned for specific tasks.
        Recent advances include large language models capable of few-shot and zero-shot learning.""",
        "source": "nlp_handbook",
        "metadata": {"category": "ai", "level": "intermediate", "topic": "nlp"}
    },
    {
        "title": "RAG Architecture and Implementation",
        "content": """Retrieval-Augmented Generation (RAG) is a technique that combines the strengths of retrieval-based and generation-based approaches.
        RAG systems retrieve relevant documents from a knowledge base and use them to augment the generation process.
        The architecture consists of a retriever component that finds relevant passages and a generator that produces responses based on the retrieved context.
        Key components include document chunking, embedding generation, vector storage, and similarity search.
        Dense passage retrieval uses neural networks to encode queries and documents into dense vectors.
        The generator, typically a large language model, receives the query along with retrieved passages to generate informed responses.
        RAG helps reduce hallucination by grounding responses in retrieved facts.
        Production RAG systems require careful consideration of latency, accuracy, and cost trade-offs.""",
        "source": "rag_architecture_guide",
        "metadata": {"category": "ai", "level": "advanced", "topic": "rag"}
    },
    {
        "title": "Vector Databases for AI Applications",
        "content": """Vector databases are specialized database systems designed to store, index, and query high-dimensional vector embeddings.
        They are essential components in modern AI applications including semantic search, recommendation systems, and RAG.
        Popular vector databases include Pinecone, Weaviate, Milvus, Qdrant, and Chroma.
        These databases use approximate nearest neighbor (ANN) algorithms for efficient similarity search.
        Common ANN algorithms include HNSW (Hierarchical Navigable Small World), IVF (Inverted File Index), and PQ (Product Quantization).
        Vector databases support various distance metrics including cosine similarity, Euclidean distance, and dot product.
        Hybrid search combines vector similarity with traditional keyword filtering for improved results.
        Scalability considerations include sharding, replication, and index optimization strategies.""",
        "source": "vector_db_overview",
        "metadata": {"category": "databases", "level": "intermediate", "topic": "vector_databases"}
    }
]

print(f"Prepared {len(sample_documents)} documents for ingestion")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Process and Ingest Documents

# COMMAND ----------

# Process all documents
all_documents = []
all_chunks = []

for doc_data in sample_documents:
    document, chunks = processor.process_document(
        title=doc_data["title"],
        content=doc_data["content"],
        source=doc_data["source"],
        metadata=doc_data["metadata"]
    )
    all_documents.append(document)
    all_chunks.extend(chunks)

print(f"Processed {len(all_documents)} documents into {len(all_chunks)} chunks")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Insert Documents into Unity Catalog

# COMMAND ----------

# Define schemas
doc_schema = StructType([
    StructField("doc_id", StringType(), False),
    StructField("title", StringType(), True),
    StructField("content", StringType(), True),
    StructField("source", StringType(), True),
    StructField("metadata", MapType(StringType(), StringType()), True),
    StructField("ingestion_timestamp", TimestampType(), True),
    StructField("last_updated", TimestampType(), True)
])

chunk_schema = StructType([
    StructField("chunk_id", StringType(), False),
    StructField("doc_id", StringType(), False),
    StructField("chunk_text", StringType(), True),
    StructField("chunk_index", IntegerType(), True),
    StructField("token_count", IntegerType(), True),
    StructField("metadata", MapType(StringType(), StringType()), True),
    StructField("created_timestamp", TimestampType(), True)
])

# COMMAND ----------

# Convert to DataFrames
docs_df = spark.createDataFrame(all_documents, schema=doc_schema)
chunks_df = spark.createDataFrame(
    [(c['chunk_id'], c['doc_id'], c['chunk_text'], c['chunk_index'], 
      c['token_count'], {}, c['created_timestamp']) for c in all_chunks],
    schema=chunk_schema
)

print(f"Documents DataFrame: {docs_df.count()} rows")
print(f"Chunks DataFrame: {chunks_df.count()} rows")

# COMMAND ----------

# Insert documents
docs_df.write.mode("append").saveAsTable("documents")
print("✅ Documents inserted")

# Insert chunks
chunks_df.write.mode("append").saveAsTable("document_chunks")
print("✅ Chunks inserted")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Data

# COMMAND ----------

# Count records
doc_count = spark.sql("SELECT COUNT(*) as count FROM documents").collect()[0]["count"]
chunk_count = spark.sql("SELECT COUNT(*) as count FROM document_chunks").collect()[0]["count"]

print(f"Total documents: {doc_count}")
print(f"Total chunks: {chunk_count}")

# COMMAND ----------

# View document summary
display(spark.sql("""
    SELECT 
        doc_id,
        title,
        source,
        metadata['category'] as category,
        metadata['topic'] as topic,
        LENGTH(content) as content_length,
        ingestion_timestamp
    FROM documents
    ORDER BY ingestion_timestamp DESC
"""))

# COMMAND ----------

# View chunks per document
display(spark.sql("""
    SELECT 
        d.title,
        COUNT(c.chunk_id) as chunk_count,
        AVG(c.token_count) as avg_tokens_per_chunk,
        SUM(c.token_count) as total_tokens
    FROM documents d
    JOIN document_chunks c ON d.doc_id = c.doc_id
    GROUP BY d.title
    ORDER BY chunk_count DESC
"""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Log Ingestion Metrics

# COMMAND ----------

# Log metrics to system_metrics table
metrics_data = [
    (f"metric_{uuid.uuid4().hex[:8]}", "documents_ingested", float(len(all_documents)), datetime.now(), {"pipeline": "rag_data"}, {"type": "count"}),
    (f"metric_{uuid.uuid4().hex[:8]}", "chunks_created", float(len(all_chunks)), datetime.now(), {"pipeline": "rag_data"}, {"type": "count"}),
    (f"metric_{uuid.uuid4().hex[:8]}", "avg_chunks_per_doc", float(len(all_chunks) / len(all_documents)), datetime.now(), {"pipeline": "rag_data"}, {"type": "average"})
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

print("✅ Metrics logged to system_metrics table")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pipeline Complete! ✅
# MAGIC
# MAGIC Successfully processed and ingested:
# MAGIC - Documents with metadata
# MAGIC - Text chunks for retrieval
# MAGIC - Pipeline metrics
# MAGIC
# MAGIC Next step: Run the embedding pipeline to generate vector embeddings