# 🧠 Databricks AI Notes

A concise reference for **Databricks AI**, **Mr. Bricks**, **Feature Store**, **Model Serving**, and **Unity Catalog** — core components of a production-grade Lakehouse AI architecture.

---

## 🧩 1. Databricks AI Overview

**Databricks AI** extends the Lakehouse Platform with built-in tooling for:
- End-to-end **machine learning lifecycle management**
- **LLM integration** with OpenAI, Hugging Face, Azure OpenAI
- Generative AI capabilities (vector search, embeddings, RAG)
- Collaboration via **Mr. Bricks**, the AI assistant for Databricks users

**Key Lakehouse AI components:**
| Layer | Purpose | Example |
|-------|----------|----------|
| **Data Intelligence Engine** | Semantic layer that applies AI to metadata | Auto schema detection, query recommendations |
| **Model Serving** | Serve ML/LLM models directly via REST | `/model/serve/predict` endpoint |
| **Feature Store** | Manage reusable features across models | `fs.create_feature_table()` |
| **Unity Catalog** | Centralized data governance for all assets | Cross-workspace permissions, lineage tracking |

---

## 🤖 2. Mr. Bricks – Databricks AI Assistant

**What it is:**  
Mr. Bricks is a **built-in AI coding assistant** inside Databricks (similar to GitHub Copilot, but Lakehouse-aware).

**Capabilities:**
- Suggests **PySpark**, **SQL**, and **Delta Live Tables** code
- Diagnoses errors and offers **remediation suggestions**
- Generates **ETL templates** and **AI/ML pipelines**
- Summarizes notebooks and helps with documentation

**Example workflow:**
1. Start typing a Spark DataFrame transformation.
2. Mr. Bricks suggests optimized PySpark syntax.
3. Accept the suggestion → execute directly in the notebook.
4. Use `/ask` prompt to debug or generate code.

**Architect value:**  
Accelerates development, enforces best practices, and reduces code-to-production time.

---

## 🧱 3. Feature Store

A managed service that stores **curated features** used for ML model training and inference.

**Benefits:**
- Centralized feature definitions (avoid training–serving skew)
- Built-in integration with MLflow for feature lineage
- Versioned feature tables under Unity Catalog

**Example:**

```python
from databricks.feature_store import FeatureStoreClient

fs = FeatureStoreClient()
# Create or read a feature table
fs.create_feature_table(
    name="fcti.ai.features.customer_behavior",
    primary_keys="customer_id",
    schema="customer_id INT, txn_count INT, avg_amount DOUBLE"
)
