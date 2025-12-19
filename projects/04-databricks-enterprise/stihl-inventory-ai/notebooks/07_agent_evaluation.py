# Databricks notebook source
# MAGIC %md
# MAGIC # STIHL Inventory Agent - Evaluation
# MAGIC 
# MAGIC This notebook evaluates the STIHL Inventory Agent using:
# MAGIC 1. **Sample queries** from each persona
# MAGIC 2. **MLflow Agent Evaluation** with AI judges
# MAGIC 3. **Quality metrics** for retrieval and generation
# MAGIC 
# MAGIC **Catalog:** ai_systems
# MAGIC **Schema:** stihl_silver, stihl_gold

# COMMAND ----------

# MAGIC %pip install databricks-vectorsearch mlflow langchain langchain-community

# COMMAND ----------

import mlflow
import pandas as pd
from datetime import datetime
from pyspark.sql.functions import current_timestamp

# Configuration
CATALOG = "ai_systems"
SCHEMA_SILVER = "stihl_silver"
SCHEMA_GOLD = "stihl_gold"

print(f"Catalog: {CATALOG}")
print(f"Silver Schema: {SCHEMA_SILVER}")
print(f"Gold Schema: {SCHEMA_GOLD}")

# COMMAND ----------

# Import the agent (assumes 06_stihl_agent was run first)
# In production, load from MLflow registry instead
%run ./06_stihl_agent

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Evaluation Test Suite

# COMMAND ----------

# Test suite with expected index routing and sample ground truth
EVALUATION_SUITE = [
    # =========================================================================
    # SUPPLY CHAIN MANAGER QUERIES
    # =========================================================================
    {
        "id": "SCM-001",
        "persona": "Supply Chain Manager",
        "query": "Which products are low on stock and need restocking?",
        "expected_index": "inventory_status_index",
        "expected_topics": ["low stock", "reorder", "restocking"],
        "ground_truth": None
    },
    {
        "id": "SCM-002",
        "persona": "Supply Chain Manager",
        "query": "What's our inventory turnover for chainsaws?",
        "expected_index": "inventory_status_index",
        "expected_topics": ["turnover", "chainsaw", "inventory"],
        "ground_truth": None
    },
    {
        "id": "SCM-003",
        "persona": "Supply Chain Manager",
        "query": "Which products have less than 14 days of supply?",
        "expected_index": "inventory_status_index",
        "expected_topics": ["days of supply", "low", "urgent"],
        "ground_truth": None
    },
    
    # =========================================================================
    # SALES DIRECTOR QUERIES
    # =========================================================================
    {
        "id": "SD-001",
        "persona": "Sales Director",
        "query": "What are the best-selling battery products in Q4?",
        "expected_index": "sales_summary_index",
        "expected_topics": ["battery", "best seller", "Q4", "revenue"],
        "ground_truth": None
    },
    {
        "id": "SD-002",
        "persona": "Sales Director",
        "query": "Compare trimmer sales across regions",
        "expected_index": "sales_summary_index",
        "expected_topics": ["trimmer", "region", "East", "West", "Central", "South"],
        "ground_truth": None
    },
    {
        "id": "SD-003",
        "persona": "Sales Director",
        "query": "What's our year-over-year growth by category?",
        "expected_index": "sales_summary_index",
        "expected_topics": ["YoY", "growth", "category"],
        "ground_truth": None
    },
    {
        "id": "SD-004",
        "persona": "Sales Director",
        "query": "Which sales channel is growing fastest?",
        "expected_index": "sales_summary_index",
        "expected_topics": ["channel", "Retail", "Pro Dealer", "Online", "growth"],
        "ground_truth": None
    },
    
    # =========================================================================
    # PRODUCT MANAGER QUERIES
    # =========================================================================
    {
        "id": "PM-001",
        "persona": "Product Manager",
        "query": "Which chainsaw models have the highest margins?",
        "expected_index": "inventory_status_index",
        "expected_topics": ["chainsaw", "margin", "profit"],
        "ground_truth": None
    },
    {
        "id": "PM-002",
        "persona": "Product Manager",
        "query": "Tell me about the MS 271 Farm Boss specifications",
        "expected_index": "product_details_index",
        "expected_topics": ["MS 271", "Farm Boss", "specifications", "engine", "cc"],
        "ground_truth": None
    },
    {
        "id": "PM-003",
        "persona": "Product Manager",
        "query": "What professional products need restocking?",
        "expected_index": "inventory_status_index",
        "expected_topics": ["professional", "low stock", "restock"],
        "ground_truth": None
    },
    {
        "id": "PM-004",
        "persona": "Product Manager",
        "query": "Compare battery vs gas chainsaw features",
        "expected_index": "product_details_index",
        "expected_topics": ["battery", "gas", "chainsaw", "features", "comparison"],
        "ground_truth": None
    },
    
    # =========================================================================
    # EXECUTIVE QUERIES
    # =========================================================================
    {
        "id": "EX-001",
        "persona": "Executive",
        "query": "Give me a summary of company performance",
        "expected_index": "executive_insights_index",
        "expected_topics": ["summary", "revenue", "growth", "performance"],
        "ground_truth": None
    },
    {
        "id": "EX-002",
        "persona": "Executive",
        "query": "What products should we discontinue based on the last 24 months?",
        "expected_index": "executive_insights_index",
        "expected_topics": ["discontinue", "poor performance", "Dog", "divest"],
        "ground_truth": None
    },
    {
        "id": "EX-003",
        "persona": "Executive",
        "query": "What products bring us the most revenue and what should we bet on?",
        "expected_index": "executive_insights_index",
        "expected_topics": ["revenue", "top", "invest", "Star", "growth"],
        "ground_truth": None
    },
    {
        "id": "EX-004",
        "persona": "Executive",
        "query": "How is the battery product category performing vs gas?",
        "expected_index": "executive_insights_index",
        "expected_topics": ["battery", "gas", "comparison", "trend", "growth"],
        "ground_truth": None
    },
    {
        "id": "EX-005",
        "persona": "Executive",
        "query": "What are the key risks in our current inventory position?",
        "expected_index": "executive_insights_index",
        "expected_topics": ["risk", "inventory", "low stock", "out of stock"],
        "ground_truth": None
    },
]

print(f"Total test cases: {len(EVALUATION_SUITE)}")
print(f"By persona: {pd.DataFrame(EVALUATION_SUITE).groupby('persona').size().to_dict()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Run Evaluation

# COMMAND ----------

def evaluate_query(agent, test_case: dict) -> dict:
    """
    Evaluate a single query against the agent.
    """
    import time
    
    start_time = time.time()
    
    try:
        result = agent.query(test_case["query"], return_sources=True)
        response_time = (time.time() - start_time) * 1000
        
        # Check routing
        indexes_searched = result["classification"]["indexes_searched"]
        expected_index = test_case["expected_index"].replace("_index", "")
        routing_correct = any(expected_index in idx for idx in indexes_searched)
        
        # Check topic coverage
        answer_lower = result["answer"].lower()
        topics_found = [t for t in test_case["expected_topics"] if t.lower() in answer_lower]
        topic_coverage = len(topics_found) / len(test_case["expected_topics"]) * 100
        
        return {
            "id": test_case["id"],
            "persona": test_case["persona"],
            "query": test_case["query"],
            "answer": result["answer"],
            "routing_correct": routing_correct,
            "indexes_searched": indexes_searched,
            "expected_index": expected_index,
            "response_time_ms": round(response_time, 2),
            "answer_length": len(result["answer"]),
            "topics_found": topics_found,
            "topics_expected": test_case["expected_topics"],
            "topic_coverage_pct": round(topic_coverage, 1),
            "classification_confidence": result["classification"]["confidence"],
            "num_sources": len(result.get("sources", [])),
            "error": None
        }
    except Exception as e:
        return {
            "id": test_case["id"],
            "persona": test_case["persona"],
            "query": test_case["query"],
            "answer": None,
            "routing_correct": False,
            "indexes_searched": [],
            "expected_index": test_case["expected_index"],
            "response_time_ms": None,
            "answer_length": 0,
            "topics_found": [],
            "topics_expected": test_case["expected_topics"],
            "topic_coverage_pct": 0,
            "classification_confidence": 0,
            "num_sources": 0,
            "error": str(e)
        }

# Run evaluation
print("Running evaluation suite...")
print("=" * 60)

evaluation_results = []
for i, test_case in enumerate(EVALUATION_SUITE, 1):
    print(f"\n[{i}/{len(EVALUATION_SUITE)}] {test_case['id']}: {test_case['query'][:50]}...")
    result = evaluate_query(agent, test_case)
    evaluation_results.append(result)
    
    # Print quick summary
    status = "PASS" if result["routing_correct"] else "FAIL"
    print(f"  {status} Routing: {result['indexes_searched']} (expected: {result['expected_index']})")
    print(f"  Topics: {result['topic_coverage_pct']}% | Time: {result['response_time_ms']}ms")

# Convert to DataFrame
eval_df = pd.DataFrame(evaluation_results)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Evaluation Metrics Summary

# COMMAND ----------

print("=" * 60)
print("EVALUATION RESULTS SUMMARY")
print("=" * 60)

# Overall metrics
total_tests = len(eval_df)
routing_accuracy = eval_df["routing_correct"].sum() / total_tests * 100
avg_topic_coverage = eval_df["topic_coverage_pct"].mean()
avg_response_time = eval_df["response_time_ms"].mean()
avg_answer_length = eval_df["answer_length"].mean()
error_rate = eval_df["error"].notna().sum() / total_tests * 100

print(f"""
OVERALL METRICS:
===============
Total Test Cases:     {total_tests}
Routing Accuracy:     {routing_accuracy:.1f}%
Avg Topic Coverage:   {avg_topic_coverage:.1f}%
Avg Response Time:    {avg_response_time:.0f}ms
Avg Answer Length:    {avg_answer_length:.0f} chars
Error Rate:           {error_rate:.1f}%
""")

# By persona
print("\nMETRICS BY PERSONA:")
print("-" * 60)
persona_metrics = eval_df.groupby("persona").agg({
    "routing_correct": lambda x: f"{x.sum()}/{len(x)} ({x.mean()*100:.0f}%)",
    "topic_coverage_pct": lambda x: f"{x.mean():.1f}%",
    "response_time_ms": lambda x: f"{x.mean():.0f}ms"
}).rename(columns={
    "routing_correct": "Routing",
    "topic_coverage_pct": "Topic Coverage",
    "response_time_ms": "Avg Time"
})
print(persona_metrics.to_string())

# Failed routing cases
print("\n\nROUTING ISSUES:")
print("-" * 60)
routing_issues = eval_df[~eval_df["routing_correct"]]
if len(routing_issues) > 0:
    for _, row in routing_issues.iterrows():
        print(f"  {row['id']}: Expected '{row['expected_index']}', got {row['indexes_searched']}")
        print(f"       Query: {row['query'][:60]}...")
else:
    print("  All queries routed correctly!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. MLflow Logging

# COMMAND ----------

# Run MLflow evaluation with AI judges
with mlflow.start_run(run_name="stihl_agent_evaluation"):
    
    # Log basic metrics
    mlflow.log_metrics({
        "routing_accuracy": routing_accuracy,
        "avg_topic_coverage": avg_topic_coverage,
        "avg_response_time_ms": avg_response_time,
        "error_rate": error_rate,
        "total_tests": total_tests
    })
    
    # Log evaluation results as artifact
    eval_df.to_csv("/tmp/evaluation_results.csv", index=False)
    mlflow.log_artifact("/tmp/evaluation_results.csv")
    
    # Log per-persona metrics
    for persona in eval_df["persona"].unique():
        persona_data = eval_df[eval_df["persona"] == persona]
        mlflow.log_metrics({
            f"{persona.lower().replace(' ', '_')}_routing_accuracy": 
                persona_data["routing_correct"].mean() * 100,
            f"{persona.lower().replace(' ', '_')}_topic_coverage": 
                persona_data["topic_coverage_pct"].mean()
        })
    
    # Log config
    mlflow.log_params({
        "catalog": CATALOG,
        "schema_silver": SCHEMA_SILVER,
        "schema_gold": SCHEMA_GOLD,
        "num_test_cases": total_tests
    })
    
    print("Evaluation metrics logged to MLflow")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Sample Responses Review

# COMMAND ----------

# Display sample responses for manual review
print("=" * 80)
print("SAMPLE RESPONSES FOR REVIEW")
print("=" * 80)

# Show one response per persona
for persona in eval_df["persona"].unique():
    persona_row = eval_df[eval_df["persona"] == persona].iloc[0]
    
    print(f"\n{'='*80}")
    print(f"PERSONA: {persona}")
    print(f"QUERY: {persona_row['query']}")
    print(f"{'='*80}")
    print(f"\nROUTING: {persona_row['indexes_searched']}")
    print(f"TOPICS FOUND: {persona_row['topics_found']}")
    print(f"TOPIC COVERAGE: {persona_row['topic_coverage_pct']}%")
    print(f"\nRESPONSE:")
    print("-" * 40)
    print(persona_row["answer"][:1000] if persona_row["answer"] else "ERROR")
    if persona_row["answer"] and len(persona_row["answer"]) > 1000:
        print("... [truncated]")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Save Results to Delta

# COMMAND ----------

# Save detailed results to Delta table for tracking over time
eval_df_spark = spark.createDataFrame(eval_df.astype(str))
eval_df_spark = eval_df_spark.withColumn("evaluation_timestamp", current_timestamp())

# Create table if not exists
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA_GOLD}.agent_evaluation_history (
        id STRING,
        persona STRING,
        query STRING,
        answer STRING,
        routing_correct STRING,
        indexes_searched STRING,
        expected_index STRING,
        response_time_ms STRING,
        answer_length STRING,
        topics_found STRING,
        topics_expected STRING,
        topic_coverage_pct STRING,
        classification_confidence STRING,
        num_sources STRING,
        error STRING,
        evaluation_timestamp TIMESTAMP
    )
    USING DELTA
""")

eval_df_spark.write.mode("append").saveAsTable(f"{CATALOG}.{SCHEMA_GOLD}.agent_evaluation_history")

print(f"Results saved to {CATALOG}.{SCHEMA_GOLD}.agent_evaluation_history")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 60)
print("EVALUATION COMPLETE")
print("=" * 60)

print(f"""
CONFIGURATION:
=============
Catalog: {CATALOG}
Silver Schema: {SCHEMA_SILVER}
Gold Schema: {SCHEMA_GOLD}

KEY FINDINGS:
============
1. Routing Accuracy: {routing_accuracy:.1f}%
   {'EXCELLENT' if routing_accuracy >= 90 else 'NEEDS IMPROVEMENT' if routing_accuracy >= 70 else 'POOR'}
   
2. Topic Coverage: {avg_topic_coverage:.1f}%
   {'GOOD' if avg_topic_coverage >= 60 else 'PARTIAL' if avg_topic_coverage >= 40 else 'LOW'}

3. Response Time: {avg_response_time:.0f}ms
   {'FAST' if avg_response_time < 2000 else 'ACCEPTABLE' if avg_response_time < 5000 else 'SLOW'}

RECOMMENDATIONS:
===============
""")

if routing_accuracy < 90:
    print("- Review query classification patterns for missed cases")
if avg_topic_coverage < 60:
    print("- Improve text representations to include more relevant terms")
if avg_response_time > 3000:
    print("- Consider optimizing retrieval or using smaller LLM")
if error_rate > 5:
    print("- Investigate error cases and add error handling")

print(f"""
NEXT STEPS:
==========
1. Review failed routing cases in detail
2. Add more test cases for edge scenarios
3. Set up automated evaluation in CI/CD pipeline
4. Monitor production queries for new patterns
""")
