# Databricks Mosaic AI Integration Guide

## 🎯 Overview: Custom Solution vs Mosaic AI

You've built a **custom RAG solution**. Databricks offers **Mosaic AI** - a production-grade platform that does much of this automatically. Here's how they compare and how to upgrade.

---

## 📊 Custom vs Mosaic AI Comparison

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     YOUR CUSTOM SOLUTION                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐         │
│  │ Document   │   │  Manual    │   │  Manual    │   │  Manual    │         │
│  │ Ingestion  │──▶│  Chunking  │──▶│ Embedding  │──▶│  Cosine    │         │
│  │ (Python)   │   │ (Python)   │   │(sentence-  │   │ Similarity │         │
│  │            │   │            │   │transformers│   │ (numpy)    │         │
│  └────────────┘   └────────────┘   └────────────┘   └────────────┘         │
│        │                │                │                │                 │
│        ▼                ▼                ▼                ▼                 │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │              Unity Catalog Delta Tables                      │           │
│  │   documents │ document_chunks │ document_vectors            │           │
│  └─────────────────────────────────────────────────────────────┘           │
│                                                                              │
│  ✅ Full control                    ❌ Manual embedding management           │
│  ✅ Learn fundamentals              ❌ No auto-sync when data changes        │
│  ✅ No extra cost                   ❌ Slow similarity search (scan all)     │
│  ✅ Works on any cluster            ❌ No built-in evaluation                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                      MOSAIC AI SOLUTION                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────┐   ┌─────────────────────────────────────────────────┐      │
│  │   Delta    │   │           MOSAIC AI VECTOR SEARCH                │      │
│  │   Table    │──▶│  ┌─────────────────────────────────────────────┐ │      │
│  │ (source)   │   │  │ • Auto-chunking (optional)                  │ │      │
│  │            │   │  │ • Auto-embedding (Foundation Models)        │ │      │
│  └────────────┘   │  │ • Auto-sync (continuous or triggered)       │ │      │
│                   │  │ • ANN index (millisecond search)            │ │      │
│                   │  │ • Hybrid search (vector + keyword)          │ │      │
│                   │  └─────────────────────────────────────────────┘ │      │
│                   └─────────────────────────────────────────────────────┘   │
│                          │                                                   │
│                          ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                   MOSAIC AI AGENT FRAMEWORK                          │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐│   │
│  │  │ • One-click deployment to Model Serving                        ││   │
│  │  │ • Built-in evaluation (Agent Evaluation)                       ││   │
│  │  │ • MLflow tracing & observability                               ││   │
│  │  │ • Review App for stakeholder feedback                          ││   │
│  │  │ • Integration with LangChain, LangGraph, OpenAI SDK            ││   │
│  │  └─────────────────────────────────────────────────────────────────┘│   │
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ✅ Production-ready                ✅ Auto-sync with Delta tables          │
│  ✅ Millisecond search (ANN)        ✅ Built-in LLM judges for evaluation    │
│  ✅ Hybrid search                   ✅ One-click deployment                  │
│  ✅ Foundation Model APIs           ⚠️ Additional cost                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Mosaic AI Components

| Component | Purpose | Replaces Your... |
|-----------|---------|------------------|
| **Vector Search** | Store & search embeddings | `document_vectors` table + cosine similarity |
| **Foundation Model APIs** | Generate embeddings & responses | `sentence-transformers` model |
| **Agent Framework** | Deploy RAG as production API | Custom `RAGQuerySystem` class |
| **Agent Evaluation** | Measure quality with AI judges | Manual testing |
| **Model Serving** | Host endpoints | N/A (you didn't have this) |
| **MLflow Tracing** | Observability & debugging | `queries_log` table |

---

## 📁 New Notebook Structure (Mosaic AI Version)

```
04-databricks-enterprise/
└── notebooks/
    ├── 01_unity_catalog_setup.sql      # KEEP (still needed)
    ├── 02_rag_data_pipeline.py         # MODIFY (simpler - no chunking needed if using managed)
    ├── 03_embedding_pipeline.py        # REMOVE (Vector Search handles this)
    ├── 04_rag_query_demo.py            # REMOVE (Agent Framework handles this)
    │
    ├── 05_mosaic_vector_search.py      # NEW - Create Vector Search index
    ├── 06_mosaic_agent_framework.py    # NEW - Deploy RAG agent
    └── 07_mosaic_agent_evaluation.py   # NEW - Evaluate quality
```

---

## 🚀 Implementation Guide

### Step 1: Prerequisites

```python
# Install required packages
%pip install databricks-vectorsearch databricks-agents mlflow langchain langchain-community
dbutils.library.restartPython()
```

### Step 2: Enable Change Data Feed on Source Table

Vector Search requires Change Data Feed (CDF) enabled on your source table:

```sql
-- Enable CDF on your existing table
ALTER TABLE ai_systems.rag_production.document_chunks 
SET TBLPROPERTIES (delta.enableChangeDataFeed = true);
```

---

## 📝 Notebook 05: Mosaic AI Vector Search

```python
# Databricks notebook source
# MAGIC %md
# MAGIC # Mosaic AI Vector Search Setup
# MAGIC 
# MAGIC This notebook replaces manual embedding generation with Databricks-managed Vector Search.

# COMMAND ----------

# Install Vector Search SDK
%pip install databricks-vectorsearch
dbutils.library.restartPython()

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient

# Initialize client
client = VectorSearchClient()

# Configuration
CATALOG = "ai_systems"
SCHEMA = "rag_production"
VECTOR_SEARCH_ENDPOINT = "rag_vector_endpoint"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Create Vector Search Endpoint
# MAGIC 
# MAGIC A Vector Search endpoint is compute that serves your vector index.

# COMMAND ----------

# Check if endpoint exists, create if not
try:
    endpoint = client.get_endpoint(VECTOR_SEARCH_ENDPOINT)
    print(f"✅ Endpoint '{VECTOR_SEARCH_ENDPOINT}' already exists")
except:
    print(f"Creating endpoint '{VECTOR_SEARCH_ENDPOINT}'...")
    client.create_endpoint(
        name=VECTOR_SEARCH_ENDPOINT,
        endpoint_type="STANDARD"  # or "STORAGE_OPTIMIZED" for larger datasets
    )
    print(f"✅ Endpoint created. This may take a few minutes to provision.")

# COMMAND ----------

# Wait for endpoint to be ready
import time

def wait_for_endpoint(client, endpoint_name, timeout=600):
    start = time.time()
    while time.time() - start < timeout:
        endpoint = client.get_endpoint(endpoint_name)
        status = endpoint.get("endpoint_status", {}).get("state", "UNKNOWN")
        if status == "ONLINE":
            print(f"✅ Endpoint is ONLINE")
            return True
        print(f"Endpoint status: {status}. Waiting...")
        time.sleep(30)
    raise TimeoutError(f"Endpoint not ready after {timeout} seconds")

wait_for_endpoint(client, VECTOR_SEARCH_ENDPOINT)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Create Vector Search Index
# MAGIC 
# MAGIC The index will:
# MAGIC - Read from your `document_chunks` table
# MAGIC - Automatically generate embeddings using Databricks Foundation Model
# MAGIC - Auto-sync when source data changes

# COMMAND ----------

# Index configuration
SOURCE_TABLE = f"{CATALOG}.{SCHEMA}.document_chunks"
INDEX_NAME = f"{CATALOG}.{SCHEMA}.chunks_vector_index"

# Check if index exists
try:
    index = client.get_index(INDEX_NAME)
    print(f"✅ Index '{INDEX_NAME}' already exists")
except:
    print(f"Creating index '{INDEX_NAME}'...")
    
    # Create Delta Sync Index with Databricks-managed embeddings
    index = client.create_delta_sync_index(
        endpoint_name=VECTOR_SEARCH_ENDPOINT,
        source_table_name=SOURCE_TABLE,
        index_name=INDEX_NAME,
        pipeline_type="TRIGGERED",  # or "CONTINUOUS" for real-time sync
        primary_key="chunk_id",
        embedding_source_column="chunk_text",  # Column to embed
        embedding_model_endpoint_name="databricks-gte-large-en"  # Databricks Foundation Model
    )
    print(f"✅ Index created. Syncing data...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Trigger Initial Sync

# COMMAND ----------

# Get the index and trigger sync
index = client.get_index(INDEX_NAME)

# Check sync status
def get_index_status(index):
    return index.describe().get("status", {})

status = get_index_status(index)
print(f"Index status: {status}")

# Trigger sync if needed
if status.get("ready", False) == False:
    print("Triggering sync...")
    index.sync()

# COMMAND ----------

# Wait for index to be ready
def wait_for_index(index, timeout=600):
    start = time.time()
    while time.time() - start < timeout:
        status = index.describe().get("status", {})
        if status.get("ready", False):
            print(f"✅ Index is ready!")
            print(f"   Indexed rows: {status.get('num_rows', 'unknown')}")
            return True
        print(f"Index syncing... {status}")
        time.sleep(30)
    raise TimeoutError(f"Index not ready after {timeout} seconds")

wait_for_index(index)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Test Vector Search

# COMMAND ----------

# Query the index
test_query = "How does RAG reduce hallucination?"

results = index.similarity_search(
    query_text=test_query,
    columns=["chunk_id", "doc_id", "chunk_text"],
    num_results=5
)

print(f"Query: {test_query}")
print("=" * 80)
print(f"\nFound {len(results.get('result', {}).get('data_array', []))} results:\n")

for i, row in enumerate(results.get("result", {}).get("data_array", []), 1):
    chunk_id, doc_id, chunk_text, score = row[0], row[1], row[2], row[3] if len(row) > 3 else "N/A"
    print(f"{i}. Score: {score}")
    print(f"   Chunk: {chunk_text[:200]}...")
    print()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Test Hybrid Search (Vector + Keyword)

# COMMAND ----------

# Hybrid search combines vector similarity with keyword matching
results = index.similarity_search(
    query_text="machine learning neural networks",
    columns=["chunk_id", "doc_id", "chunk_text"],
    num_results=5,
    query_type="HYBRID"  # Combines vector + keyword search
)

print("Hybrid Search Results:")
for i, row in enumerate(results.get("result", {}).get("data_array", []), 1):
    print(f"{i}. {row[2][:150]}...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Comparison: Custom vs Mosaic AI
# MAGIC 
# MAGIC | Aspect | Your Custom Solution | Mosaic AI Vector Search |
# MAGIC |--------|---------------------|-------------------------|
# MAGIC | Embedding | Manual (sentence-transformers) | Automatic (Foundation Model) |
# MAGIC | Storage | Delta table (document_vectors) | Managed Vector Index |
# MAGIC | Search | Full scan + cosine similarity | ANN index (milliseconds) |
# MAGIC | Sync | Manual re-run pipeline | Automatic (continuous/triggered) |
# MAGIC | Hybrid Search | Not available | Built-in |

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Vector Search Setup Complete!
# MAGIC 
# MAGIC Your index is now:
# MAGIC - Automatically generating embeddings using `databricks-gte-large-en`
# MAGIC - Indexed for fast ANN (Approximate Nearest Neighbor) search
# MAGIC - Ready to sync when source data changes
# MAGIC 
# MAGIC Next: Set up Agent Framework for deployment
```

---

## 📝 Notebook 06: Mosaic AI Agent Framework

```python
# Databricks notebook source
# MAGIC %md
# MAGIC # Mosaic AI Agent Framework
# MAGIC 
# MAGIC Deploy your RAG application as a production-ready endpoint with one line of code.

# COMMAND ----------

%pip install databricks-agents mlflow langchain langchain-community databricks-vectorsearch
dbutils.library.restartPython()

# COMMAND ----------

import mlflow
from databricks.vector_search.client import VectorSearchClient
from langchain_community.chat_models import ChatDatabricks
from langchain_community.vectorstores import DatabricksVectorSearch
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# Enable MLflow tracing for observability
mlflow.langchain.autolog()

# Configuration
CATALOG = "ai_systems"
SCHEMA = "rag_production"
INDEX_NAME = f"{CATALOG}.{SCHEMA}.chunks_vector_index"
VECTOR_SEARCH_ENDPOINT = "rag_vector_endpoint"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Create the RAG Chain

# COMMAND ----------

# Initialize Vector Search client
vs_client = VectorSearchClient()

# Create retriever from Vector Search index
index = vs_client.get_index(
    endpoint_name=VECTOR_SEARCH_ENDPOINT,
    index_name=INDEX_NAME
)

# Wrap as LangChain retriever
vectorstore = DatabricksVectorSearch(
    index=index,
    text_column="chunk_text",
    columns=["chunk_id", "doc_id", "chunk_text"]
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

# COMMAND ----------

# Initialize LLM (Databricks Foundation Model)
llm = ChatDatabricks(
    endpoint="databricks-meta-llama-3-1-70b-instruct",  # or "databricks-dbrx-instruct"
    temperature=0.1
)

# COMMAND ----------

# Create RAG prompt template
RAG_PROMPT = PromptTemplate(
    template="""You are a helpful AI assistant. Answer the question based on the provided context.
If you cannot answer based on the context, say "I don't have enough information to answer that question."

Context:
{context}

Question: {question}

Answer: """,
    input_variables=["context", "question"]
)

# Create RAG chain
rag_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    chain_type_kwargs={"prompt": RAG_PROMPT},
    return_source_documents=True
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Test the RAG Chain Locally

# COMMAND ----------

# Test query
question = "What is machine learning and how does it relate to AI?"

response = rag_chain.invoke({"query": question})

print(f"Question: {question}")
print("=" * 80)
print(f"\nAnswer: {response['result']}")
print(f"\nSources used: {len(response['source_documents'])}")
for i, doc in enumerate(response['source_documents'], 1):
    print(f"  {i}. {doc.page_content[:100]}...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Log the Model to MLflow

# COMMAND ----------

# Define input example for schema
input_example = {"query": "What is RAG?"}

# Log the chain to MLflow
with mlflow.start_run(run_name="rag-agent-v1"):
    logged_model = mlflow.langchain.log_model(
        lc_model=rag_chain,
        artifact_path="rag_chain",
        input_example=input_example,
        registered_model_name=f"{CATALOG}.{SCHEMA}.rag_agent"
    )
    
print(f"✅ Model logged to: {logged_model.model_uri}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Deploy to Model Serving

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import EndpointCoreConfigInput, ServedEntityInput

# Initialize workspace client
w = WorkspaceClient()

# Endpoint configuration
SERVING_ENDPOINT_NAME = "rag-agent-endpoint"

# Get the latest model version
model_name = f"{CATALOG}.{SCHEMA}.rag_agent"
latest_version = w.model_registry.get_latest_versions(model_name)[0].version

# Create or update serving endpoint
try:
    # Try to get existing endpoint
    endpoint = w.serving_endpoints.get(SERVING_ENDPOINT_NAME)
    print(f"Endpoint exists, updating to version {latest_version}...")
    
    w.serving_endpoints.update_config_and_wait(
        name=SERVING_ENDPOINT_NAME,
        served_entities=[
            ServedEntityInput(
                entity_name=model_name,
                entity_version=str(latest_version),
                workload_size="Small",
                scale_to_zero_enabled=True
            )
        ]
    )
except:
    print(f"Creating new endpoint '{SERVING_ENDPOINT_NAME}'...")
    
    w.serving_endpoints.create_and_wait(
        name=SERVING_ENDPOINT_NAME,
        config=EndpointCoreConfigInput(
            served_entities=[
                ServedEntityInput(
                    entity_name=model_name,
                    entity_version=str(latest_version),
                    workload_size="Small",
                    scale_to_zero_enabled=True
                )
            ]
        )
    )

print(f"✅ Endpoint '{SERVING_ENDPOINT_NAME}' is ready!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Test the Deployed Endpoint

# COMMAND ----------

import requests
import json

# Get endpoint URL
endpoint_url = f"https://{spark.conf.get('spark.databricks.workspaceUrl')}/serving-endpoints/{SERVING_ENDPOINT_NAME}/invocations"

# Get token
token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()

# Test query
test_payload = {
    "inputs": [{"query": "Explain how RAG systems work"}]
}

response = requests.post(
    endpoint_url,
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json=test_payload
)

print("Endpoint Response:")
print(json.dumps(response.json(), indent=2))

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Agent Deployment Complete!
# MAGIC 
# MAGIC Your RAG agent is now:
# MAGIC - Deployed as a REST API endpoint
# MAGIC - Auto-scaling based on traffic
# MAGIC - Observable with MLflow tracing
# MAGIC - Integrated with Unity Catalog governance
# MAGIC 
# MAGIC Next: Set up Agent Evaluation for quality monitoring
```

---

## 📝 Notebook 07: Mosaic AI Agent Evaluation

```python
# Databricks notebook source
# MAGIC %md
# MAGIC # Mosaic AI Agent Evaluation
# MAGIC 
# MAGIC Evaluate your RAG agent quality using AI judges.

# COMMAND ----------

%pip install databricks-agents mlflow
dbutils.library.restartPython()

# COMMAND ----------

import mlflow
import pandas as pd
from databricks.agents import evaluate

# Configuration
CATALOG = "ai_systems"
SCHEMA = "rag_production"
MODEL_NAME = f"{CATALOG}.{SCHEMA}.rag_agent"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Create Evaluation Dataset

# COMMAND ----------

# Define evaluation questions with expected answers (ground truth)
eval_data = pd.DataFrame([
    {
        "request": "What is machine learning?",
        "expected_response": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed.",
        "expected_retrieved_context": ["machine learning", "AI", "algorithms"]
    },
    {
        "request": "How does RAG reduce hallucination?",
        "expected_response": "RAG reduces hallucination by grounding LLM responses in retrieved factual information from a knowledge base.",
        "expected_retrieved_context": ["RAG", "hallucination", "retrieval"]
    },
    {
        "request": "What are vector embeddings?",
        "expected_response": "Vector embeddings are numerical representations of text that capture semantic meaning, enabling similarity comparisons.",
        "expected_retrieved_context": ["embeddings", "vectors", "semantic"]
    },
    {
        "request": "What is Unity Catalog?",
        "expected_response": "Unity Catalog is Databricks' unified governance solution for data and AI assets.",
        "expected_retrieved_context": ["Unity Catalog", "governance", "Databricks"]
    },
    {
        "request": "Explain deep learning neural networks",
        "expected_response": "Deep learning uses multi-layer neural networks to learn representations from data.",
        "expected_retrieved_context": ["deep learning", "neural networks", "layers"]
    }
])

print(f"Evaluation dataset: {len(eval_data)} questions")
display(eval_data)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Run Agent Evaluation

# COMMAND ----------

# Load the model
model_uri = f"models:/{MODEL_NAME}/latest"

# Run evaluation with AI judges
with mlflow.start_run(run_name="rag-evaluation"):
    results = mlflow.evaluate(
        model=model_uri,
        data=eval_data,
        model_type="databricks-agent",  # Enables AI judges
        evaluators=["databricks-agent"],
        evaluator_config={
            "databricks-agent": {
                "metrics": [
                    "answer_correctness",      # Is the answer correct?
                    "groundedness",            # Is the answer grounded in retrieved context?
                    "relevance",               # Is the answer relevant to the question?
                    "chunk_relevance",         # Are retrieved chunks relevant?
                    "safety"                   # Is the answer safe?
                ]
            }
        }
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Analyze Results

# COMMAND ----------

# View evaluation metrics
print("=" * 80)
print("EVALUATION METRICS")
print("=" * 80)

metrics = results.metrics
for metric, value in metrics.items():
    print(f"{metric}: {value:.2%}" if isinstance(value, float) else f"{metric}: {value}")

# COMMAND ----------

# View per-question results
print("\n" + "=" * 80)
print("PER-QUESTION RESULTS")
print("=" * 80)

results_df = results.tables["eval_results"]
display(results_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Identify Issues

# COMMAND ----------

# Find questions with low scores
low_score_threshold = 0.7

if "answer_correctness" in results_df.columns:
    issues = results_df[results_df["answer_correctness/score"] < low_score_threshold]
    
    if len(issues) > 0:
        print(f"⚠️ Found {len(issues)} questions with low correctness scores:")
        for idx, row in issues.iterrows():
            print(f"\n  Question: {row['request']}")
            print(f"  Score: {row['answer_correctness/score']:.2%}")
            print(f"  Feedback: {row.get('answer_correctness/rationale', 'N/A')}")
    else:
        print("✅ All questions passed correctness threshold!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Evaluation Metrics Explained
# MAGIC 
# MAGIC | Metric | What It Measures | AI Judge Prompt |
# MAGIC |--------|-----------------|-----------------|
# MAGIC | **answer_correctness** | Is the answer factually correct? | Compares to ground truth |
# MAGIC | **groundedness** | Is the answer based on retrieved context? | Checks for hallucination |
# MAGIC | **relevance** | Does the answer address the question? | Semantic alignment |
# MAGIC | **chunk_relevance** | Are retrieved chunks useful? | Context quality |
# MAGIC | **safety** | Is the answer safe and appropriate? | Harmful content check |

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Evaluation Complete!
# MAGIC 
# MAGIC You now have:
# MAGIC - Automated quality measurement with AI judges
# MAGIC - Per-question analysis for debugging
# MAGIC - Metrics tracked in MLflow for comparison
# MAGIC 
# MAGIC Use this to iterate and improve your RAG system quality!
```

---

## 📊 Architecture Comparison Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     BEFORE: YOUR CUSTOM SOLUTION                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Documents ──▶ Notebook 02 ──▶ Notebook 03 ──▶ Notebook 04                 │
│                (Chunking)      (Embeddings)    (Query)                       │
│                    │               │               │                         │
│                    ▼               ▼               ▼                         │
│              document_chunks  document_vectors  queries_log                  │
│                    │               │               │                         │
│                    └───────────────┴───────────────┘                        │
│                              Manual Process                                  │
│                         (Re-run for every update)                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                      AFTER: MOSAIC AI SOLUTION                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────┐                                                        │
│   │  Delta Table    │                                                        │
│   │ document_chunks │                                                        │
│   └────────┬────────┘                                                        │
│            │  Auto-sync (continuous)                                         │
│            ▼                                                                 │
│   ┌─────────────────────────────────────────────────────────┐               │
│   │            MOSAIC AI VECTOR SEARCH                       │               │
│   │  • Auto-embedding (databricks-gte-large-en)             │               │
│   │  • ANN indexing (millisecond search)                    │               │
│   │  • Hybrid search                                        │               │
│   └────────────────────────┬────────────────────────────────┘               │
│                            │                                                 │
│                            ▼                                                 │
│   ┌─────────────────────────────────────────────────────────┐               │
│   │            MOSAIC AI AGENT FRAMEWORK                     │               │
│   │  • RAG Chain (LangChain)                                │               │
│   │  • LLM (databricks-meta-llama-3-1-70b-instruct)        │               │
│   │  • MLflow tracing                                       │               │
│   └────────────────────────┬────────────────────────────────┘               │
│                            │                                                 │
│                            ▼                                                 │
│   ┌─────────────────────────────────────────────────────────┐               │
│   │            MODEL SERVING ENDPOINT                        │               │
│   │  • REST API                                             │               │
│   │  • Auto-scaling                                         │               │
│   │  • Production-ready                                     │               │
│   └────────────────────────┬────────────────────────────────┘               │
│                            │                                                 │
│                            ▼                                                 │
│   ┌─────────────────────────────────────────────────────────┐               │
│   │            AGENT EVALUATION                              │               │
│   │  • AI Judges (correctness, groundedness, safety)        │               │
│   │  • Review App (stakeholder feedback)                    │               │
│   │  • Quality monitoring                                   │               │
│   └─────────────────────────────────────────────────────────┘               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 💰 Cost Considerations

| Component | Pricing Model | Approximate Cost |
|-----------|---------------|------------------|
| **Vector Search Endpoint** | Per hour | ~$0.38/hour (Standard) |
| **Foundation Model APIs** | Per token | ~$0.0001 per 1K tokens |
| **Model Serving** | Per hour | ~$0.07/hour (Small) |
| **Agent Evaluation** | Per evaluation | Included with above |

**For learning/development**: Keep endpoints scaled to zero when not in use.

---

## ✅ Summary: What You Gain with Mosaic AI

| Feature | Custom Solution | Mosaic AI |
|---------|-----------------|-----------|
| Embedding generation | Manual (sentence-transformers) | Automatic (Foundation Models) |
| Vector storage | Delta table | Managed Vector Index |
| Search speed | Seconds (full scan) | Milliseconds (ANN) |
| Data sync | Manual re-run | Automatic |
| Deployment | None | One-click REST API |
| Evaluation | Manual testing | AI Judges |
| Observability | queries_log table | MLflow Tracing |
| Production-ready | ❌ | ✅ |

---

## 🎯 Recommended Learning Path

1. **Keep your custom solution** - It demonstrates fundamentals
2. **Add Mosaic AI notebooks** - Shows production upgrade path
3. **Portfolio story**: "Built custom RAG to understand fundamentals, then upgraded to Mosaic AI for production"

This shows interviewers you understand:
- RAG fundamentals (chunking, embedding, similarity search)
- Production concerns (scaling, monitoring, evaluation)
- Databricks platform capabilities
