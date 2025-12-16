# Databricks notebook source
# MAGIC %md
# MAGIC # Mosaic AI Agent Framework
# MAGIC 
# MAGIC Deploy your RAG application as a production-ready endpoint.
# MAGIC 
# MAGIC This notebook:
# MAGIC 1. Creates a RAG chain using LangChain
# MAGIC 2. Connects to Vector Search for retrieval
# MAGIC 3. Uses Foundation Model LLM for generation
# MAGIC 4. Deploys to Model Serving endpoint
# MAGIC 
# MAGIC ## Prerequisites
# MAGIC - Vector Search index created (notebook 05)
# MAGIC - Unity Catalog access

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install Dependencies

# COMMAND ----------

%pip install databricks-vectorsearch langchain langchain-community mlflow databricks-sdk
dbutils.library.restartPython()

# COMMAND ----------

import mlflow
import os
from databricks.vector_search.client import VectorSearchClient

# Enable MLflow autologging for tracing
mlflow.langchain.autolog()

# Configuration
CATALOG = "ai_systems"
SCHEMA = "rag_production"
INDEX_NAME = f"{CATALOG}.{SCHEMA}.chunks_vector_index"
VECTOR_SEARCH_ENDPOINT = "rag_vector_endpoint"
MODEL_NAME = f"{CATALOG}.{SCHEMA}.rag_agent"
SERVING_ENDPOINT = "rag-agent-endpoint"

print(f"Configuration:")
print(f"  Vector Index: {INDEX_NAME}")
print(f"  Model Name: {MODEL_NAME}")
print(f"  Serving Endpoint: {SERVING_ENDPOINT}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Create Vector Store Retriever

# COMMAND ----------

from langchain_community.vectorstores import DatabricksVectorSearch

# Initialize Vector Search client
vs_client = VectorSearchClient()

# Get the index
index = vs_client.get_index(
    endpoint_name=VECTOR_SEARCH_ENDPOINT,
    index_name=INDEX_NAME
)

# Create LangChain vector store wrapper
vectorstore = DatabricksVectorSearch(
    index=index,
    text_column="chunk_text",
    columns=["chunk_id", "doc_id", "chunk_text"]
)

# Create retriever
retriever = vectorstore.as_retriever(
    search_kwargs={"k": 5}  # Return top 5 results
)

# Test retriever
test_docs = retriever.invoke("What is machine learning?")
print(f"Retriever test - found {len(test_docs)} documents")
for i, doc in enumerate(test_docs[:2], 1):
    print(f"  {i}. {doc.page_content[:100]}...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Initialize Foundation Model LLM

# COMMAND ----------

from langchain_community.chat_models import ChatDatabricks

# Use Databricks Foundation Model
# Options: databricks-meta-llama-3-1-70b-instruct, databricks-dbrx-instruct, databricks-mixtral-8x7b-instruct
llm = ChatDatabricks(
    endpoint="databricks-meta-llama-3-1-70b-instruct",
    temperature=0.1,
    max_tokens=500
)

# Test LLM
test_response = llm.invoke("Say 'Hello, RAG system is working!' in exactly those words.")
print(f"LLM test: {test_response.content}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Create RAG Chain

# COMMAND ----------

from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# Define RAG prompt
RAG_PROMPT_TEMPLATE = """You are a helpful AI assistant that answers questions based on the provided context.

Instructions:
- Answer the question using ONLY the information in the context below
- If the context doesn't contain enough information, say "I don't have enough information to answer that question"
- Be concise and direct in your answers
- Do not make up information

Context:
{context}

Question: {question}

Answer:"""

RAG_PROMPT = PromptTemplate(
    template=RAG_PROMPT_TEMPLATE,
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

print("✅ RAG chain created")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Test RAG Chain Locally

# COMMAND ----------

def ask(question):
    """Query the RAG chain and display results"""
    print(f"\n{'='*80}")
    print(f"Question: {question}")
    print('='*80)
    
    response = rag_chain.invoke({"query": question})
    
    print(f"\nAnswer: {response['result']}")
    print(f"\nSources ({len(response['source_documents'])} documents):")
    
    for i, doc in enumerate(response['source_documents'][:3], 1):
        print(f"  {i}. {doc.page_content[:150]}...")
    
    return response

# Test queries
ask("What is machine learning and how does it work?")

# COMMAND ----------

ask("How does RAG help reduce hallucination in AI systems?")

# COMMAND ----------

ask("What are vector embeddings used for?")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Log Model to MLflow

# COMMAND ----------

# Input example for schema inference
input_example = {"query": "What is RAG?"}

# Log the model
with mlflow.start_run(run_name="rag-agent-v1") as run:
    
    # Log model
    logged_model = mlflow.langchain.log_model(
        lc_model=rag_chain,
        artifact_path="rag_chain",
        input_example=input_example,
        registered_model_name=MODEL_NAME
    )
    
    # Log parameters
    mlflow.log_params({
        "vector_index": INDEX_NAME,
        "llm_endpoint": "databricks-meta-llama-3-1-70b-instruct",
        "retriever_k": 5,
        "temperature": 0.1
    })
    
    run_id = run.info.run_id
    model_uri = logged_model.model_uri

print(f"✅ Model logged")
print(f"   Run ID: {run_id}")
print(f"   Model URI: {model_uri}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Test Logged Model

# COMMAND ----------

# Load and test the logged model
loaded_model = mlflow.langchain.load_model(model_uri)

test_response = loaded_model.invoke({"query": "Explain deep learning"})
print(f"Loaded model test:")
print(f"  Answer: {test_response['result'][:200]}...")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Deploy to Model Serving
# MAGIC 
# MAGIC This creates a REST API endpoint for your RAG application.

# COMMAND ----------

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import EndpointCoreConfigInput, ServedEntityInput

# Initialize workspace client
w = WorkspaceClient()

# Get latest model version
from mlflow.tracking import MlflowClient
mlflow_client = MlflowClient()

model_version_info = mlflow_client.get_latest_versions(MODEL_NAME, stages=["None"])
if model_version_info:
    latest_version = model_version_info[0].version
    print(f"Latest model version: {latest_version}")
else:
    print("No model versions found")
    latest_version = "1"

# COMMAND ----------

# Create or update serving endpoint
def deploy_endpoint(workspace_client, endpoint_name, model_name, model_version):
    """Deploy model to serving endpoint"""
    
    served_entity = ServedEntityInput(
        entity_name=model_name,
        entity_version=str(model_version),
        workload_size="Small",
        scale_to_zero_enabled=True  # Save cost when not in use
    )
    
    try:
        # Check if endpoint exists
        endpoint = workspace_client.serving_endpoints.get(endpoint_name)
        print(f"Endpoint '{endpoint_name}' exists, updating...")
        
        workspace_client.serving_endpoints.update_config_and_wait(
            name=endpoint_name,
            served_entities=[served_entity]
        )
        
    except Exception as e:
        if "NOT_FOUND" in str(e) or "does not exist" in str(e):
            print(f"Creating new endpoint '{endpoint_name}'...")
            
            workspace_client.serving_endpoints.create_and_wait(
                name=endpoint_name,
                config=EndpointCoreConfigInput(
                    served_entities=[served_entity]
                )
            )
        else:
            raise e
    
    print(f"✅ Endpoint '{endpoint_name}' is ready!")
    return endpoint_name

# Deploy
deploy_endpoint(w, SERVING_ENDPOINT, MODEL_NAME, latest_version)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 8: Test Deployed Endpoint

# COMMAND ----------

import requests
import json

# Get workspace URL and token
workspace_url = spark.conf.get("spark.databricks.workspaceUrl")
token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()

# Endpoint URL
endpoint_url = f"https://{workspace_url}/serving-endpoints/{SERVING_ENDPOINT}/invocations"

def query_endpoint(question):
    """Query the deployed endpoint"""
    
    payload = {
        "inputs": [{"query": question}]
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(endpoint_url, headers=headers, json=payload)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

# COMMAND ----------

# Test the endpoint
print("Testing deployed endpoint...")
print("=" * 80)

result = query_endpoint("What is machine learning?")
if result:
    print(json.dumps(result, indent=2)[:1000])

# COMMAND ----------

# MAGIC %md
# MAGIC ## Endpoint Information

# COMMAND ----------

# Display endpoint details
endpoint_info = w.serving_endpoints.get(SERVING_ENDPOINT)

print(f"Endpoint Name: {endpoint_info.name}")
print(f"State: {endpoint_info.state.ready}")
print(f"URL: https://{workspace_url}/serving-endpoints/{SERVING_ENDPOINT}/invocations")

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Agent Deployment Complete!
# MAGIC 
# MAGIC Your RAG agent is now:
# MAGIC - ✅ Deployed as a REST API
# MAGIC - ✅ Auto-scaling based on traffic
# MAGIC - ✅ Scale-to-zero when idle (cost saving)
# MAGIC - ✅ Observable with MLflow tracing
# MAGIC - ✅ Governed by Unity Catalog
# MAGIC 
# MAGIC ### API Usage
# MAGIC 
# MAGIC ```python
# MAGIC import requests
# MAGIC 
# MAGIC response = requests.post(
# MAGIC     "https://<workspace>/serving-endpoints/rag-agent-endpoint/invocations",
# MAGIC     headers={"Authorization": "Bearer <token>"},
# MAGIC     json={"inputs": [{"query": "Your question here"}]}
# MAGIC )
# MAGIC ```
# MAGIC 
# MAGIC **Next Step**: Run `07_mosaic_agent_evaluation.py` to evaluate quality
