# Databricks notebook source
# MAGIC %md
# MAGIC # STIHL Inventory AI Agent
# MAGIC 
# MAGIC This notebook creates an intelligent RAG agent that:
# MAGIC 1. **Automatically classifies** incoming queries
# MAGIC 2. **Routes** to the appropriate Vector Search index
# MAGIC 3. **Retrieves** relevant context
# MAGIC 4. **Generates** informed responses using LLM
# MAGIC 
# MAGIC **Catalog:** ai_systems
# MAGIC **Schema:** stihl_silver

# COMMAND ----------

# MAGIC %pip install databricks-vectorsearch mlflow langchain langchain-community langchain-core --quiet

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration & Imports

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient
from langchain_community.chat_models import ChatDatabricks
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
import mlflow
from mlflow.models import infer_signature
import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Configuration - Using existing ai_systems catalog
CATALOG = "ai_systems"
SCHEMA_SILVER = "stihl_silver"
ENDPOINT_NAME = "stihl_inventory_endpoint"

# Index names
INDEXES = {
    "product_details": f"{CATALOG}.{SCHEMA_SILVER}.product_details_index",
    "inventory_status": f"{CATALOG}.{SCHEMA_SILVER}.inventory_status_index",
    "sales_summary": f"{CATALOG}.{SCHEMA_SILVER}.sales_summary_index",
    "executive_insights": f"{CATALOG}.{SCHEMA_SILVER}.executive_insights_index"
}

# LLM configuration - Update this based on your workspace's available endpoints
# Common options: databricks-meta-llama-3-3-70b-instruct, databricks-dbrx-instruct, databricks-mixtral-8x7b-instruct
LLM_ENDPOINT = "databricks-meta-llama-3-3-70b-instruct"

print(f"Catalog: {CATALOG}")
print(f"Schema: {SCHEMA_SILVER}")
print(f"Vector Search Endpoint: {ENDPOINT_NAME}")
print(f"LLM Endpoint: {LLM_ENDPOINT}")
print(f"Indexes: {list(INDEXES.keys())}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Query Classification System

# COMMAND ----------

class QueryType(Enum):
    PRODUCT_DETAIL = "product_details"
    INVENTORY_STATUS = "inventory_status"
    SALES_PERFORMANCE = "sales_summary"
    EXECUTIVE_INSIGHT = "executive_insights"
    MULTI_INDEX = "multi_index"

@dataclass
class ClassifiedQuery:
    """Result of query classification"""
    original_query: str
    query_type: QueryType
    indexes_to_search: List[str]
    confidence: float
    reasoning: str

class QueryClassifier:
    """
    Classifies incoming queries to determine which Vector Search index to use.
    Uses keyword matching with optional LLM fallback.
    """
    
    PATTERNS = {
        QueryType.PRODUCT_DETAIL: {
            "keywords": [
                "spec", "specification", "feature", "detail", "describe",
                "what is", "tell me about", "model", "engine", "power",
                "weight", "bar length", "displacement", "cc", "voltage",
                "battery", "fuel", "capacity", "warranty", "product"
            ],
            "negative": ["price", "cost", "stock", "inventory", "sales", "sold"]
        },
        QueryType.INVENTORY_STATUS: {
            "keywords": [
                "stock", "inventory", "available", "quantity", "restock",
                "low stock", "out of stock", "warehouse", "supply",
                "price", "cost", "msrp", "margin", "pricing",
                "days of supply", "reorder", "shortage"
            ],
            "negative": ["sales", "revenue", "sold", "best selling", "trend"]
        },
        QueryType.SALES_PERFORMANCE: {
            "keywords": [
                "sales", "sold", "selling", "revenue", "best seller",
                "top selling", "performance", "growth", "yoy", "mom",
                "q1", "q2", "q3", "q4", "quarter", "month", "year",
                "compare", "region", "channel", "trend"
            ],
            "negative": ["summary", "recommend", "discontinue", "invest"]
        },
        QueryType.EXECUTIVE_INSIGHT: {
            "keywords": [
                "summary", "summarize", "overview", "executive",
                "recommend", "recommendation", "should we", "invest",
                "discontinue", "phase out", "strategy", "strategic",
                "company", "overall", "high level", "insight",
                "what products", "which products to", "bet on"
            ],
            "negative": []
        }
    }
    
    def __init__(self, use_llm_fallback: bool = False):
        self.use_llm_fallback = use_llm_fallback
        if use_llm_fallback:
            self.llm = ChatDatabricks(endpoint=LLM_ENDPOINT, temperature=0)
    
    def classify(self, query: str) -> ClassifiedQuery:
        """Classify a query and determine which index(es) to search"""
        query_lower = query.lower()
        
        # Score each query type
        scores = {}
        for query_type, patterns in self.PATTERNS.items():
            score = 0
            # Positive keywords
            for keyword in patterns["keywords"]:
                if keyword in query_lower:
                    score += 1
            # Negative keywords (reduce score)
            for neg_keyword in patterns.get("negative", []):
                if neg_keyword in query_lower:
                    score -= 0.5
            scores[query_type] = max(0, score)
        
        # Determine winner
        max_score = max(scores.values())
        
        if max_score == 0:
            # No clear match - use LLM or default to executive
            if self.use_llm_fallback:
                return self._llm_classify(query)
            else:
                return ClassifiedQuery(
                    original_query=query,
                    query_type=QueryType.EXECUTIVE_INSIGHT,
                    indexes_to_search=[INDEXES["executive_insights"]],
                    confidence=0.5,
                    reasoning="No keyword match, defaulting to executive insights"
                )
        
        # Get winning type(s)
        winners = [qt for qt, score in scores.items() if score == max_score]
        
        if len(winners) == 1:
            winner = winners[0]
            return ClassifiedQuery(
                original_query=query,
                query_type=winner,
                indexes_to_search=[INDEXES[winner.value]],
                confidence=min(1.0, max_score / 3),
                reasoning=f"Matched keywords for {winner.value}"
            )
        else:
            # Multiple matches - search multiple indexes
            return ClassifiedQuery(
                original_query=query,
                query_type=QueryType.MULTI_INDEX,
                indexes_to_search=[INDEXES[w.value] for w in winners],
                confidence=min(1.0, max_score / 3),
                reasoning=f"Multiple matches: {[w.value for w in winners]}"
            )
    
    def _llm_classify(self, query: str) -> ClassifiedQuery:
        """Use LLM as fallback for classification"""
        prompt = f"""Classify this inventory/sales query into ONE category:
- PRODUCT_DETAIL: Questions about product specifications, features, models
- INVENTORY_STATUS: Questions about stock levels, pricing, availability
- SALES_PERFORMANCE: Questions about sales data, revenue, trends
- EXECUTIVE_INSIGHT: Strategic questions, recommendations, summaries

Query: {query}

Respond with ONLY the category name (e.g., PRODUCT_DETAIL)."""
        
        try:
            response = self.llm.invoke(prompt)
            category = response.content.strip().upper()
            
            type_map = {
                "PRODUCT_DETAIL": QueryType.PRODUCT_DETAIL,
                "INVENTORY_STATUS": QueryType.INVENTORY_STATUS,
                "SALES_PERFORMANCE": QueryType.SALES_PERFORMANCE,
                "EXECUTIVE_INSIGHT": QueryType.EXECUTIVE_INSIGHT
            }
            
            query_type = type_map.get(category, QueryType.EXECUTIVE_INSIGHT)
            
            return ClassifiedQuery(
                original_query=query,
                query_type=query_type,
                indexes_to_search=[INDEXES[query_type.value]],
                confidence=0.8,
                reasoning=f"LLM classified as {category}"
            )
        except Exception as e:
            return ClassifiedQuery(
                original_query=query,
                query_type=QueryType.EXECUTIVE_INSIGHT,
                indexes_to_search=[INDEXES["executive_insights"]],
                confidence=0.5,
                reasoning=f"LLM error, defaulting: {str(e)[:50]}"
            )

# COMMAND ----------

# Test the classifier
classifier = QueryClassifier(use_llm_fallback=False)

test_queries = [
    "What are the specs of the MS 271 chainsaw?",
    "Which products are low on stock?",
    "What's the price of the BGA 86 blower?",
    "What were the best selling battery products in Q4?",
    "Give me a summary of company performance",
    "What products should we discontinue?",
    "Compare trimmer sales across regions"
]

print("Query Classification Tests:")
print("=" * 60)
for q in test_queries:
    result = classifier.classify(q)
    print(f"\nQuery: {q}")
    print(f"  Type: {result.query_type.value}")
    print(f"  Indexes: {[i.split('.')[-1] for i in result.indexes_to_search]}")
    print(f"  Confidence: {result.confidence:.2f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Multi-Index Retriever

# COMMAND ----------

class MultiIndexRetriever:
    """
    Retrieves relevant context from multiple Vector Search indexes.
    """
    
    def __init__(self, endpoint_name: str = ENDPOINT_NAME):
        self.vs_client = VectorSearchClient(disable_notice=True)
        self.endpoint_name = endpoint_name
    
    def retrieve(
        self, 
        query: str, 
        index_names: List[str],
        num_results_per_index: int = 5
    ) -> List[Dict]:
        """
        Search multiple indexes and combine results.
        """
        all_results = []
        
        for index_name in index_names:
            try:
                index = self.vs_client.get_index(
                    endpoint_name=self.endpoint_name,
                    index_name=index_name
                )
                results = index.similarity_search(
                    query_text=query,
                    columns=["text_id", "text_content"],
                    num_results=num_results_per_index
                )
                
                data = results.get("result", {}).get("data_array", [])
                for row in data:
                    all_results.append({
                        "text_id": row[0],
                        "text_content": row[1],
                        "score": row[-1],
                        "source_index": index_name.split(".")[-1]
                    })
            except Exception as e:
                print(f"Error searching {index_name}: {e}")
        
        # Sort by score (descending) and deduplicate
        all_results.sort(key=lambda x: x["score"], reverse=True)
        
        # Deduplicate by text_id
        seen = set()
        unique_results = []
        for r in all_results:
            if r["text_id"] not in seen:
                seen.add(r["text_id"])
                unique_results.append(r)
        
        return unique_results
    
    def format_context(self, results: List[Dict], max_chars: int = 8000) -> str:
        """Format retrieved results into context string"""
        if not results:
            return "No relevant information found."
        
        context_parts = []
        total_chars = 0
        
        for i, r in enumerate(results, 1):
            content = r["text_content"]
            source = r["source_index"]
            
            # Truncate if needed
            if total_chars + len(content) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 200:
                    content = content[:remaining] + "..."
                else:
                    break
            
            context_parts.append(f"[Source: {source}]\n{content}")
            total_chars += len(content)
        
        return "\n\n---\n\n".join(context_parts)

# Test retriever
retriever = MultiIndexRetriever()
print("MultiIndexRetriever initialized successfully")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. STIHL Inventory Agent

# COMMAND ----------

class STIHLInventoryAgent:
    """
    Complete RAG agent for STIHL inventory analytics.
    """
    
    SYSTEM_PROMPT = """You are an expert STIHL inventory and sales analyst. You help managers, 
executives, and supply chain teams understand their product portfolio, inventory status, 
and sales performance.

You have access to real-time data about:
- Product specifications and features
- Current inventory levels and pricing
- Historical sales performance
- Category and company-wide trends

Guidelines:
1. Base your answers ONLY on the provided context
2. If the context doesn't contain enough information, say so
3. Be specific with numbers and product names when available
4. For strategic questions, provide actionable insights
5. Format responses clearly with bullet points for lists

Context from STIHL database:
{context}
"""
    
    def __init__(self, use_llm_classifier: bool = False):
        self.classifier = QueryClassifier(use_llm_fallback=use_llm_classifier)
        self.retriever = MultiIndexRetriever()
        self.llm = ChatDatabricks(endpoint=LLM_ENDPOINT, temperature=0.1)
        
        # Build the chain
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", "{question}")
        ])
        
        self.chain = (
            {"context": RunnableLambda(self._get_context), "question": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )
    
    def _get_context(self, question: str) -> str:
        """Classify query and retrieve relevant context"""
        classification = self.classifier.classify(question)
        self.last_classification = classification  # Store for debugging
        
        results = self.retriever.retrieve(
            query=question,
            index_names=classification.indexes_to_search,
            num_results_per_index=5
        )
        
        return self.retriever.format_context(results)
    
    def query(self, question: str) -> str:
        """Process a question and return the response"""
        try:
            response = self.chain.invoke(question)
            return response
        except Exception as e:
            return f"Error processing query: {str(e)}"
    
    def query_with_debug(self, question: str) -> Dict:
        """Process a question and return response with debug info"""
        try:
            response = self.chain.invoke(question)
            return {
                "question": question,
                "response": response,
                "classification": {
                    "type": self.last_classification.query_type.value,
                    "indexes": self.last_classification.indexes_to_search,
                    "confidence": self.last_classification.confidence,
                    "reasoning": self.last_classification.reasoning
                }
            }
        except Exception as e:
            return {
                "question": question,
                "response": f"Error: {str(e)}",
                "classification": None
            }

# COMMAND ----------

# Initialize the agent
agent = STIHLInventoryAgent(use_llm_classifier=False)
print("STIHL Inventory Agent initialized successfully!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Test the Agent

# COMMAND ----------

# Test queries across different personas
test_scenarios = [
    {
        "persona": "Supply Chain",
        "questions": [
            "Which products are low on stock and need restocking?",
            "What's our inventory turnover for chainsaws?"
        ]
    },
    {
        "persona": "Sales",
        "questions": [
            "What are the best-selling battery products in Q4?",
            "Compare trimmer sales across regions"
        ]
    },
    {
        "persona": "Product",
        "questions": [
            "Which chainsaw models have the highest margins?",
            "Tell me about the MS 271 Farm Boss specifications"
        ]
    },
    {
        "persona": "Executive",
        "questions": [
            "Give me a summary of company performance",
            "What products should we discontinue based on the last 24 months?",
            "What products bring us the most revenue and what should we bet on?"
        ]
    }
]

print("=" * 80)
print("STIHL INVENTORY AGENT - TEST RESULTS")
print("=" * 80)

for scenario in test_scenarios:
    for question in scenario["questions"]:
        print(f"\n{'='*80}")
        print(f"PERSONA: {scenario['persona']}")
        print(f"QUESTION: {question}")
        print("-" * 80)
        
        try:
            result = agent.query_with_debug(question)
            print(f"\nCLASSIFICATION: {result['classification']['type']}")
            print(f"INDEXES: {[i.split('.')[-1] for i in result['classification']['indexes']]}")
            print(f"\nRESPONSE:\n{result['response'][:1000]}...")
        except Exception as e:
            print(f"ERROR: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Log Agent to MLflow

# COMMAND ----------

# Re-define configuration (needed for MLflow wrapper class)
CATALOG = "ai_systems"
SCHEMA_SILVER = "stihl_silver"
ENDPOINT_NAME = "stihl_inventory_endpoint"
LLM_ENDPOINT = "databricks-meta-llama-3-3-70b-instruct"

INDEXES = {
    "product_details": f"{CATALOG}.{SCHEMA_SILVER}.product_details_index",
    "inventory_status": f"{CATALOG}.{SCHEMA_SILVER}.inventory_status_index",
    "sales_summary": f"{CATALOG}.{SCHEMA_SILVER}.sales_summary_index",
    "executive_insights": f"{CATALOG}.{SCHEMA_SILVER}.executive_insights_index"
}

class STIHLAgentWrapper(mlflow.pyfunc.PythonModel):
    """MLflow wrapper for the STIHL Inventory Agent"""
    
    def load_context(self, context):
        """Load the agent when model is loaded"""
        # Re-import and recreate agent at load time
        from databricks.vector_search.client import VectorSearchClient
        from langchain_community.chat_models import ChatDatabricks
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.runnables import RunnablePassthrough, RunnableLambda
        from langchain_core.output_parsers import StrOutputParser
        
        # Store config for the agent
        self.config = {
            "catalog": "ai_systems",
            "schema": "stihl_silver",
            "endpoint": "stihl_inventory_endpoint",
            "llm_endpoint": "databricks-meta-llama-3-3-70b-instruct"
        }
        
        # Agent will be initialized on first predict call
        self._agent = None
    
    def _get_agent(self):
        """Lazy initialization of the agent"""
        if self._agent is None:
            self._agent = STIHLInventoryAgent(use_llm_classifier=False)
        return self._agent
    
    def predict(self, context, model_input):
        """Process queries"""
        if isinstance(model_input, dict):
            questions = [model_input.get("question", model_input.get("query", ""))]
        elif hasattr(model_input, 'to_dict'):
            questions = model_input.get("question", model_input.get("query", [])).tolist()
        else:
            questions = [str(model_input)]
        
        agent = self._get_agent()
        results = []
        for q in questions:
            if q:
                result = agent.query(q)
                results.append(result)
        
        return results

# Log the agent to MLflow
with mlflow.start_run(run_name="stihl_inventory_agent") as run:
    
    # Log model parameters
    mlflow.log_params({
        "llm_endpoint": LLM_ENDPOINT,
        "num_indexes": len(INDEXES),
        "indexes": list(INDEXES.keys()),
        "classification_method": "keyword_based",
        "catalog": CATALOG,
        "schema": SCHEMA_SILVER
    })
    
    # Create input example and signature
    input_example = {"question": "What products are low on stock?"}
    
    from mlflow.models.signature import ModelSignature
    from mlflow.types.schema import Schema, ColSpec
    
    input_schema = Schema([ColSpec("string", "question")])
    output_schema = Schema([ColSpec("string")])
    signature = ModelSignature(inputs=input_schema, outputs=output_schema)
    
    # Log the model
    mlflow.pyfunc.log_model(
        artifact_path="stihl_agent",
        python_model=STIHLAgentWrapper(),
        signature=signature,
        input_example=input_example,
        registered_model_name=f"{CATALOG}.{SCHEMA_SILVER}.stihl_inventory_agent"
    )
    
    print(f"✓ Model logged to MLflow run: {run.info.run_id}")
    print(f"✓ Registered as: {CATALOG}.{SCHEMA_SILVER}.stihl_inventory_agent")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 60)
print("STIHL INVENTORY AGENT - SETUP COMPLETE")
print("=" * 60)

print(f"""
Configuration:
  Catalog: {CATALOG}
  Schema: {SCHEMA_SILVER}
  Vector Search Endpoint: {ENDPOINT_NAME}
  LLM Endpoint: {LLM_ENDPOINT}

Indexes:
  • product_details_index - Product specs and features
  • inventory_status_index - Stock levels and pricing
  • sales_summary_index - Sales performance data
  • executive_insights_index - Category summaries and trends

Agent Capabilities:
  • Automatic query classification (4 categories)
  • Multi-index retrieval
  • Context-aware response generation
  • MLflow model registration

Usage Example:
  agent = STIHLInventoryAgent()
  response = agent.query("What chainsaws are best sellers?")
  print(response)

Model Registered:
  {CATALOG}.{SCHEMA_SILVER}.stihl_inventory_agent
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Quick Test Cell
# MAGIC Run this cell anytime to test the agent

# COMMAND ----------

# Quick test - run this cell to test the agent
print("Testing STIHL Inventory Agent...")
print("=" * 50)

test_question = "What are the top selling products and which ones should we invest in?"
print(f"Question: {test_question}\n")

response = agent.query(test_question)
print(f"Response:\n{response}")
