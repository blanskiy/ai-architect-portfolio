# Databricks notebook source
# MAGIC %md
# MAGIC # Mosaic AI Agent Evaluation
# MAGIC 
# MAGIC Evaluate your RAG agent quality using AI judges.
# MAGIC 
# MAGIC This notebook:
# MAGIC 1. Creates an evaluation dataset with ground truth
# MAGIC 2. Runs the agent against test questions
# MAGIC 3. Uses AI judges to score responses
# MAGIC 4. Identifies quality issues
# MAGIC 
# MAGIC ## Prerequisites
# MAGIC - RAG agent deployed (notebook 06)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install Dependencies

# COMMAND ----------

%pip install databricks-agents mlflow pandas
dbutils.library.restartPython()

# COMMAND ----------

import mlflow
import pandas as pd
from mlflow.tracking import MlflowClient

# Configuration
CATALOG = "ai_systems"
SCHEMA = "rag_production"
MODEL_NAME = f"{CATALOG}.{SCHEMA}.rag_agent"

print(f"Evaluating model: {MODEL_NAME}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Create Evaluation Dataset
# MAGIC 
# MAGIC A good evaluation dataset includes:
# MAGIC - **request**: The question to ask
# MAGIC - **expected_response**: Ground truth answer (for correctness scoring)
# MAGIC - **expected_retrieved_context**: Keywords that should appear in retrieved chunks

# COMMAND ----------

# Define evaluation questions with ground truth
eval_data = pd.DataFrame([
    {
        "request": "What is machine learning?",
        "expected_response": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. It uses algorithms to find patterns in data.",
    },
    {
        "request": "How does RAG reduce hallucination in AI systems?",
        "expected_response": "RAG (Retrieval-Augmented Generation) reduces hallucination by grounding LLM responses in retrieved factual information from a knowledge base, rather than relying solely on the model's training data.",
    },
    {
        "request": "What are vector embeddings?",
        "expected_response": "Vector embeddings are numerical representations of text that capture semantic meaning. They convert words or sentences into dense vectors of floating-point numbers, enabling mathematical comparison of meaning.",
    },
    {
        "request": "Explain the difference between supervised and unsupervised learning",
        "expected_response": "Supervised learning uses labeled training data to learn a mapping from inputs to outputs, while unsupervised learning finds patterns in data without labels.",
    },
    {
        "request": "What is a neural network?",
        "expected_response": "A neural network is a computing system inspired by biological neural networks, consisting of connected nodes (neurons) organized in layers that process information.",
    },
    {
        "request": "How do transformers work in NLP?",
        "expected_response": "Transformers use self-attention mechanisms to process sequential data, allowing them to capture long-range dependencies in text more effectively than previous architectures like RNNs.",
    },
    {
        "request": "What is transfer learning?",
        "expected_response": "Transfer learning is a technique where a model pre-trained on one task is fine-tuned for a different but related task, leveraging learned representations.",
    },
    {
        "request": "What algorithms do vector databases use for similarity search?",
        "expected_response": "Vector databases use approximate nearest neighbor (ANN) algorithms like HNSW, IVF, and product quantization for efficient similarity search at scale.",
    }
])

print(f"Evaluation dataset: {len(eval_data)} questions")
display(eval_data)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Get Model URI

# COMMAND ----------

# Get latest model version
mlflow_client = MlflowClient()

model_versions = mlflow_client.get_latest_versions(MODEL_NAME, stages=["None"])
if model_versions:
    latest_version = model_versions[0].version
    model_uri = f"models:/{MODEL_NAME}/{latest_version}"
    print(f"Model URI: {model_uri}")
else:
    raise ValueError(f"No versions found for model {MODEL_NAME}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Run Evaluation with AI Judges
# MAGIC 
# MAGIC Mosaic AI Agent Evaluation provides several AI judges:
# MAGIC 
# MAGIC | Judge | What It Measures |
# MAGIC |-------|-----------------|
# MAGIC | **answer_correctness** | Is the answer factually correct vs ground truth? |
# MAGIC | **groundedness** | Is the answer grounded in retrieved context? |
# MAGIC | **relevance** | Is the answer relevant to the question? |
# MAGIC | **safety** | Is the answer safe and appropriate? |

# COMMAND ----------

# Run evaluation
with mlflow.start_run(run_name="rag-evaluation-v1"):
    
    # Basic evaluation without databricks-agent (which requires specific setup)
    results = mlflow.evaluate(
        model=model_uri,
        data=eval_data,
        targets="expected_response",
        model_type="question-answering",
        evaluators="default"
    )
    
    print("✅ Evaluation complete")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: View Evaluation Metrics

# COMMAND ----------

# Display overall metrics
print("=" * 80)
print("OVERALL METRICS")
print("=" * 80)

for metric_name, metric_value in results.metrics.items():
    if isinstance(metric_value, float):
        print(f"{metric_name}: {metric_value:.4f}")
    else:
        print(f"{metric_name}: {metric_value}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: View Per-Question Results

# COMMAND ----------

# Get detailed results
results_df = results.tables.get("eval_results_table", pd.DataFrame())

if not results_df.empty:
    print("Per-Question Results:")
    display(results_df)
else:
    print("No detailed results table available")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Manual Quality Check
# MAGIC 
# MAGIC Let's also run some manual tests to see actual responses.

# COMMAND ----------

# Load model for manual testing
loaded_model = mlflow.langchain.load_model(model_uri)

def test_and_compare(question, expected):
    """Test a question and compare to expected answer"""
    print(f"\n{'='*80}")
    print(f"Question: {question}")
    print("-" * 40)
    
    # Get actual response
    response = loaded_model.invoke({"query": question})
    actual = response.get("result", "No response")
    
    print(f"Expected: {expected[:200]}...")
    print(f"\nActual: {actual[:200]}...")
    
    return {
        "question": question,
        "expected": expected,
        "actual": actual
    }

# Test a few questions
test_results = []
for _, row in eval_data.head(3).iterrows():
    result = test_and_compare(row["request"], row["expected_response"])
    test_results.append(result)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Identify Quality Issues

# COMMAND ----------

# Analyze test results for potential issues
print("=" * 80)
print("QUALITY ANALYSIS")
print("=" * 80)

issues_found = []

for result in test_results:
    actual_lower = result["actual"].lower()
    expected_lower = result["expected"].lower()
    
    # Check for "I don't know" responses
    if "don't have enough information" in actual_lower or "i don't know" in actual_lower:
        issues_found.append({
            "question": result["question"],
            "issue": "Model couldn't answer - may need more relevant documents"
        })
    
    # Check if key terms from expected are in actual
    expected_keywords = set(expected_lower.split()) - {"the", "a", "is", "are", "to", "and", "of", "in", "that"}
    actual_keywords = set(actual_lower.split())
    
    overlap = len(expected_keywords & actual_keywords) / len(expected_keywords) if expected_keywords else 0
    
    if overlap < 0.3:
        issues_found.append({
            "question": result["question"],
            "issue": f"Low keyword overlap ({overlap:.0%}) - answer may be off-topic"
        })

if issues_found:
    print(f"\n⚠️ Found {len(issues_found)} potential issues:\n")
    for issue in issues_found:
        print(f"  Question: {issue['question'][:50]}...")
        print(f"  Issue: {issue['issue']}\n")
else:
    print("✅ No major issues detected in sample")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 8: Save Evaluation Results

# COMMAND ----------

# Save results to Delta table for tracking
eval_results_table = f"{CATALOG}.{SCHEMA}.evaluation_results"

# Create results DataFrame
eval_summary = pd.DataFrame([{
    "evaluation_id": mlflow.active_run().info.run_id if mlflow.active_run() else "manual",
    "model_name": MODEL_NAME,
    "model_version": latest_version,
    "num_questions": len(eval_data),
    "timestamp": pd.Timestamp.now(),
    **{k: v for k, v in results.metrics.items() if isinstance(v, (int, float))}
}])

# Save to Delta
spark_df = spark.createDataFrame(eval_summary)
spark_df.write.mode("append").saveAsTable(eval_results_table)

print(f"✅ Results saved to {eval_results_table}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Evaluation Best Practices
# MAGIC 
# MAGIC ### Building Good Evaluation Sets
# MAGIC 
# MAGIC 1. **Diverse questions**: Cover different topics in your knowledge base
# MAGIC 2. **Edge cases**: Include questions that should return "I don't know"
# MAGIC 3. **Ground truth**: Have domain experts provide expected answers
# MAGIC 4. **Realistic queries**: Use questions your users actually ask
# MAGIC 
# MAGIC ### Interpreting Results
# MAGIC 
# MAGIC | Metric | Good Score | Action if Low |
# MAGIC |--------|------------|---------------|
# MAGIC | Correctness | > 0.8 | Improve retrieval or add documents |
# MAGIC | Groundedness | > 0.9 | Adjust prompt to stay on context |
# MAGIC | Relevance | > 0.85 | Improve chunking or retrieval |
# MAGIC | Safety | > 0.95 | Add content filtering |
# MAGIC 
# MAGIC ### Iteration Loop
# MAGIC 
# MAGIC ```
# MAGIC Evaluate → Find Issues → Fix (docs/prompt/model) → Re-evaluate → Deploy
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ Evaluation Complete!
# MAGIC 
# MAGIC You now have:
# MAGIC - ✅ Automated quality measurement
# MAGIC - ✅ Per-question analysis
# MAGIC - ✅ Results tracked in MLflow
# MAGIC - ✅ Historical results in Delta table
# MAGIC 
# MAGIC ### Next Steps
# MAGIC 
# MAGIC 1. **Expand evaluation set**: Add more questions covering your use cases
# MAGIC 2. **Set up monitoring**: Run evaluation on a schedule
# MAGIC 3. **Create dashboards**: Visualize quality trends over time
# MAGIC 4. **Iterate**: Use insights to improve retrieval and prompts
