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
# MAGIC **Query Router Strategy:**
# MAGIC - Product specs/features → `product_details_index`
# MAGIC - Pricing/inventory/stock → `inventory_status_index`
# MAGIC - Sales performance/trends → `sales_summary_index`
# MAGIC - Executive summaries/recommendations → `executive_insights_index`

# COMMAND ----------

# MAGIC %pip install databricks-vectorsearch mlflow langchain langchain-community

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient
from langchain_community.chat_models import ChatDatabricks
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda
from langchain.schema.output_parser import StrOutputParser
import mlflow
from mlflow.models import infer_signature
import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Configuration
CATALOG = "stihl"
SCHEMA = "silver"
ENDPOINT_NAME = "stihl_inventory_endpoint"

# Index names
INDEXES = {
    "product_details": f"{CATALOG}.{SCHEMA}.product_details_index",
    "inventory_status": f"{CATALOG}.{SCHEMA}.inventory_status_index",
    "sales_summary": f"{CATALOG}.{SCHEMA}.sales_summary_index",
    "executive_insights": f"{CATALOG}.{SCHEMA}.executive_insights_index"
}

# LLM configuration
LLM_ENDPOINT = "databricks-meta-llama-3-1-70b-instruct"  # Or your preferred model

print(f"Indexes: {INDEXES}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Query Classification System
# MAGIC 
# MAGIC Automatic routing based on query analysis.

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
    Classifies incoming queries and routes to appropriate indexes.
    Uses keyword matching + LLM for complex cases.
    """
    
    # Keyword patterns for each query type
    PATTERNS = {
        QueryType.PRODUCT_DETAIL: {
            "keywords": [
                "specs", "specifications", "features", "description",
                "engine", "cc", "bar length", "weight", "power type",
                "what is", "tell me about", "describe", "details",
                "professional", "homeowner", "battery vs gas"
            ],
            "negative": ["price", "cost", "stock", "inventory", "sales", "revenue"]
        },
        QueryType.INVENTORY_STATUS: {
            "keywords": [
                "stock", "inventory", "available", "in stock", "out of stock",
                "low stock", "reorder", "days of supply", "restocking",
                "price", "pricing", "cost", "margin", "msrp",
                "how much", "current price"
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
    
    def __init__(self, use_llm_fallback: bool = True):
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
        """Use LLM for complex query classification"""
        prompt = f"""Classify this inventory analytics query into one category:

Query: "{query}"

Categories:
1. PRODUCT_DETAIL - Questions about product specifications, features, descriptions
2. INVENTORY_STATUS - Questions about stock levels, pricing, availability
3. SALES_PERFORMANCE - Questions about sales data, revenue, trends
4. EXECUTIVE_INSIGHT - Strategic questions, recommendations, summaries

Respond with ONLY the category name (e.g., "PRODUCT_DETAIL")."""

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

# Test the classifier
classifier = QueryClassifier(use_llm_fallback=False)  # Set True for LLM fallback

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
    print(f"  → Type: {result.query_type.value}")
    print(f"  → Indexes: {[i.split('.')[-1] for i in result.indexes_to_search]}")
    print(f"  → Confidence: {result.confidence:.2f}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Multi-Index Retriever
# MAGIC 
# MAGIC Retrieves from one or more indexes based on classification.

# COMMAND ----------

class MultiIndexRetriever:
    """
    Retrieves relevant context from multiple Vector Search indexes.
    """
    
    def __init__(self, endpoint_name: str = ENDPOINT_NAME):
        self.vs_client = VectorSearchClient()
        self.endpoint_name = endpoint_name
    
    def retrieve(
        self, 
        query: str, 
        index_names: List[str],
        num_results_per_index: int = 5
    ) -> List[Dict]:
        """
        Search multiple indexes and combine results.
        
        Returns list of dicts with: text_id, text_content, score, source_index
        """
        all_results = []
        
        for index_name in index_names:
            try:
                index = self.vs_client.get_index(index_name)
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

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. STIHL Inventory Agent
# MAGIC 
# MAGIC Complete agent with classification, retrieval, and generation.

# COMMAND ----------

class STIHLInventoryAgent:
    """
    Complete RAG agent for STIHL inventory analytics.
    
    Flow:
    1. Classify query → Determine index(es)
    2. Retrieve → Search relevant index(es)
    3. Generate → LLM creates response with context
    """
    
    SYSTEM_PROMPT = """You are an expert STIHL inventory and sales analyst. You help managers, 
executives, and supply chain professionals understand product performance, inventory status, 
and sales trends.

Your responses should be:
- Data-driven: Reference specific numbers, percentages, and metrics from the context
- Actionable: Provide clear recommendations when appropriate
- Concise: Get to the point, but be thorough when needed
- Professional: Use business language appropriate for stakeholders

When answering:
- If asked about specific products, include model numbers and key specs
- If asked about inventory, mention stock status and any alerts
- If asked about sales, include revenue figures and growth trends
- If asked for recommendations, justify with data from the context

If the context doesn't contain enough information to fully answer the question,
acknowledge what you can answer and what additional data might be needed."""

    QUERY_PROMPT = """Based on the following context from our inventory and sales systems, 
please answer the user's question.

CONTEXT:
{context}

USER QUESTION: {question}

Provide a clear, data-driven response:"""

    def __init__(
        self, 
        llm_endpoint: str = LLM_ENDPOINT,
        temperature: float = 0.1,
        use_llm_classifier: bool = False
    ):
        self.classifier = QueryClassifier(use_llm_fallback=use_llm_classifier)
        self.retriever = MultiIndexRetriever()
        self.llm = ChatDatabricks(
            endpoint=llm_endpoint,
            temperature=temperature
        )
        
        # Build the prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", self.QUERY_PROMPT)
        ])
    
    def query(
        self, 
        question: str, 
        num_results: int = 5,
        return_sources: bool = False
    ) -> Dict:
        """
        Process a user query end-to-end.
        
        Args:
            question: User's natural language question
            num_results: Number of results per index to retrieve
            return_sources: Include source documents in response
            
        Returns:
            Dict with answer, classification info, and optionally sources
        """
        # Step 1: Classify the query
        classification = self.classifier.classify(question)
        
        # Step 2: Retrieve relevant context
        results = self.retriever.retrieve(
            query=question,
            index_names=classification.indexes_to_search,
            num_results_per_index=num_results
        )
        context = self.retriever.format_context(results)
        
        # Step 3: Generate response
        chain = self.prompt | self.llm | StrOutputParser()
        answer = chain.invoke({
            "context": context,
            "question": question
        })
        
        # Build response
        response = {
            "question": question,
            "answer": answer,
            "classification": {
                "type": classification.query_type.value,
                "indexes_searched": [i.split(".")[-1] for i in classification.indexes_to_search],
                "confidence": classification.confidence,
                "reasoning": classification.reasoning
            }
        }
        
        if return_sources:
            response["sources"] = [
                {
                    "text_id": r["text_id"],
                    "source_index": r["source_index"],
                    "score": r["score"],
                    "preview": r["text_content"][:200] + "..."
                }
                for r in results[:5]
            ]
        
        return response
    
    def chat(self, question: str) -> str:
        """Simple interface that returns just the answer string"""
        result = self.query(question)
        return result["answer"]

# Initialize the agent
agent = STIHLInventoryAgent(use_llm_classifier=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Test the Agent

# COMMAND ----------

# Test queries representing different personas
TEST_QUERIES = [
    # Supply Chain Manager
    ("Supply Chain", "Which products are low on stock and need restocking?"),
    ("Supply Chain", "What's our inventory turnover for chainsaws?"),
    
    # Sales Director  
    ("Sales", "What are the best-selling battery products in Q4?"),
    ("Sales", "Compare trimmer sales across regions"),
    
    # Product Manager
    ("Product", "Which chainsaw models have the highest margins?"),
    ("Product", "Tell me about the MS 271 Farm Boss specifications"),
    
    # Executive
    ("Executive", "Give me a summary of company performance"),
    ("Executive", "What products should we discontinue based on the last 24 months?"),
    ("Executive", "What products bring us the most revenue and what should we bet on?"),
]

print("=" * 80)
print("STIHL INVENTORY AGENT - TEST RESULTS")
print("=" * 80)

for persona, question in TEST_QUERIES:
    print(f"\n{'='*80}")
    print(f"PERSONA: {persona}")
    print(f"QUESTION: {question}")
    print("-" * 80)
    
    try:
        result = agent.query(question, return_sources=True)
        
        print(f"\nCLASSIFICATION:")
        print(f"  Type: {result['classification']['type']}")
        print(f"  Indexes: {result['classification']['indexes_searched']}")
        print(f"  Confidence: {result['classification']['confidence']:.2f}")
        
        print(f"\nANSWER:")
        print(result['answer'][:800])
        if len(result['answer']) > 800:
            print("... [truncated]")
        
        print(f"\nSOURCES USED: {len(result.get('sources', []))}")
        for src in result.get('sources', [])[:2]:
            print(f"  - {src['source_index']}: {src['text_id']} (score: {src['score']:.3f})")
    
    except Exception as e:
        print(f"ERROR: {e}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Log Agent to MLflow

# COMMAND ----------

# Create a pyfunc wrapper for MLflow
class STIHLAgentWrapper(mlflow.pyfunc.PythonModel):
    """MLflow wrapper for the STIHL Inventory Agent"""
    
    def load_context(self, context):
        """Load the agent when model is loaded"""
        self.agent = STIHLInventoryAgent(use_llm_classifier=False)
    
    def predict(self, context, model_input):
        """Process queries"""
        if isinstance(model_input, dict):
            questions = [model_input.get("question", model_input.get("query", ""))]
        elif hasattr(model_input, 'to_dict'):
            # DataFrame input
            questions = model_input.get("question", model_input.get("query", [])).tolist()
        else:
            questions = [str(model_input)]
        
        results = []
        for q in questions:
            if q:
                result = self.agent.query(q)
                results.append(result)
        
        return results

# Log the agent to MLflow
with mlflow.start_run(run_name="stihl_inventory_agent") as run:
    
    # Log model parameters
    mlflow.log_params({
        "llm_endpoint": LLM_ENDPOINT,
        "num_indexes": len(INDEXES),
        "indexes": list(INDEXES.keys()),
        "classification_method": "keyword_based"
    })
    
    # Create signature
    input_example = {"question": "What products are low on stock?"}
    
    # Log the model
    mlflow.pyfunc.log_model(
        artifact_path="stihl_agent",
        python_model=STIHLAgentWrapper(),
        input_example=input_example,
        registered_model_name=f"{CATALOG}.{SCHEMA}.stihl_inventory_agent"
    )
    
    print(f"Model logged to MLflow run: {run.info.run_id}")
    print(f"Registered as: {CATALOG}.{SCHEMA}.stihl_inventory_agent")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Deploy to Model Serving (Optional)

# COMMAND ----------

# Uncomment to deploy to Model Serving endpoint
"""
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ServedEntityInput, EndpointCoreConfigInput

ws = WorkspaceClient()

# Create serving endpoint
endpoint_name = "stihl-inventory-agent"

try:
    ws.serving_endpoints.create(
        name=endpoint_name,
        config=EndpointCoreConfigInput(
            served_entities=[
                ServedEntityInput(
                    entity_name=f"{CATALOG}.{SCHEMA}.stihl_inventory_agent",
                    entity_version="1",
                    scale_to_zero_enabled=True,
                    workload_size="Small"
                )
            ]
        )
    )
    print(f"Created serving endpoint: {endpoint_name}")
except Exception as e:
    print(f"Endpoint may already exist or error: {e}")
"""

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 60)
print("STIHL INVENTORY AGENT - SETUP COMPLETE")
print("=" * 60)

print("""
AGENT CAPABILITIES:
==================

1. AUTOMATIC QUERY CLASSIFICATION
   - Analyzes incoming queries using keyword patterns
   - Routes to appropriate index(es)
   - Supports multi-index queries for complex questions

2. QUERY TYPES SUPPORTED:
   - Product Details: Specs, features, descriptions
   - Inventory Status: Stock levels, pricing, availability
   - Sales Performance: Revenue, trends, comparisons
   - Executive Insights: Summaries, recommendations, strategy

3. INDEXES USED:
   - product_details_index: Static product info (weekly sync)
   - inventory_status_index: Pricing + inventory (daily sync)
   - sales_summary_index: Monthly sales data (daily sync)
   - executive_insights_index: Summaries + recommendations (daily sync)

4. USAGE:
   
   # Simple query
   answer = agent.chat("What products are low on stock?")
   
   # Full response with metadata
   result = agent.query("What products should we discontinue?", return_sources=True)
   print(result['answer'])
   print(result['classification'])
   print(result['sources'])

5. PERSONAS SERVED:
   - Supply Chain Manager: Inventory, restocking, turnover
   - Sales Director: Performance, trends, comparisons
   - Product Manager: Specs, margins, product health
   - Executive: Summaries, recommendations, strategy
""")
