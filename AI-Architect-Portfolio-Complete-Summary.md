# AI-Architect-Portfolio - Complete Project Summary

## Handoff Document for New Chat Session
**Updated:** December 29, 2025  
**Purpose:** Portfolio tracking and interview preparation  
**GitHub:** https://github.com/blanskiy/ai-architect-portfolio

---

## 🎯 Portfolio Overview

### Target Role
**Microsoft AI Architect** - Azure AI/ML Platform, Azure OpenAI, Microsoft Fabric

### 4-Month Learning Plan Structure
| Month | Focus | Status |
|-------|-------|--------|
| Month 1 | Foundations (ML Systems, Serving) | ✅ COMPLETE |
| Month 2 | LLMs & Data Engineering | 🔄 IN PROGRESS |
| Month 3 | MLOps & Production | ⏳ Not Started |
| Month 4 | Databricks & Jobs | ⏳ Not Started |

### Success Metrics
- Design end-to-end ML system for 1M+ users in 45min whiteboard
- Deploy model serving 1000 RPS with <100ms latency
- Build production RAG system with evaluation framework ✅
- Implement full MLOps pipeline with CI/CD, monitoring, drift detection
- Pass Azure AI Engineer Associate (AI-102) certification

---

## 📁 Local Project Structure

```
C:\Users\blans\source\repos\ai-architect-portfolio\
├── .claude/                           # Claude settings
├── .github/workflows/                 # CI/CD pipelines
├── architecture-diagrams/             # System design diagrams
├── projects/
│   ├── 01-foundations/                # ✅ COMPLETE
│   │   └── high-throughput-serving/   # ResNet-50 API (deployed)
│   ├── 02-llm-mastery/                # 🔄 IN PROGRESS
│   ├── 03-azure-ai-foundry/           # ✅ LABS COMPLETE
│   │   ├── lab1-model-selection/      # ✅ Complete
│   │   ├── lab2-chat-app/             # ✅ Complete
│   │   ├── lab3-rag/                  # ✅ Complete
│   │   ├── lab4-content-filters/      # ✅ Complete
│   │   ├── lab5-evaluation/           # ✅ Complete
│   │   └── lab6-agent/                # ✅ Complete (Main deliverable)
│   ├── 03-mlops-production/           # ⏳ Month 3
│   └── 03-nlp-transformers/           # NLP/Transformer work
├── README.md
└── requirements.txt
```

---

## ✅ MONTH 1 - COMPLETE: Foundations

### Project 1-3: High-Throughput ML Serving System

**Live Production API:**
```
https://resnet-api.mangobay-4d613d45.westus2.azurecontainerapps.io
```

**Achievements:**
| Component | Technology | Result |
|-----------|------------|--------|
| Model | ResNet-50 (ImageNet) | 1000-class classification |
| Framework | PyTorch → ONNX | 1.89× speedup |
| API | FastAPI + Async | 7 RPS throughput |
| Caching | Redis | 80% hit rate |
| Container | Docker | Production-ready |
| Orchestration | Kubernetes | Auto-scaling 1-10 pods |
| Cloud | Azure Container Apps | Live deployment |
| CI/CD | GitHub Actions | Automated testing |
| MLOps | MLflow | Model versioning |

**Key Metrics:**
- ONNX Speedup: 1.89× (PyTorch 697ms → ONNX 368ms)
- Distributed Speedup: 9.3× (4 workers vs 1)
- Model Size: 97.79 MB → 48.90 MB (FP16 quantized)

---

## 🔄 MONTH 2 - IN PROGRESS: LLMs & Data

### Week 1-2: Transformer Fundamentals (Partial)
- Transformer architecture
- Self-attention mechanism
- Embeddings and tokenization
- Located in: `projects/03-nlp-transformers/`

### Week 2-3: Azure AI Foundry Project ✅ COMPLETE

**Project Goal:** Build STIHL Sales Analytics Agent using Azure AI Foundry

**Data Source:** Databricks Lakehouse (ai_systems catalog)
- `ai_systems.stihl_silver.fact_sales` - 89,342 transactions
- `ai_systems.stihl_gold.monthly_trends` - Aggregated monthly data
- `ai_systems.stihl_gold.product_performance` - BCG matrix rankings

#### Azure AI Foundry Labs Status - ALL COMPLETE ✅

| Lab | Topic | Status | Key Deliverable |
|-----|-------|--------|-----------------|
| Lab 1 | Model Selection & Deployment | ✅ | 3 models deployed (gpt-4o, gpt-4o-mini, embeddings) |
| Lab 2 | Chat Application | ✅ | Python chat with Azure OpenAI SDK |
| Lab 3 | RAG Demo | ✅ | 50-doc Azure AI Search index |
| Lab 4 | Content Filters | ✅ | Custom safety policy for business terms |
| Lab 5 | Evaluation | ✅ | LLM-as-judge quality framework |
| Lab 6 | Agent Service | ✅ | Databricks function calling agent |

---

## 🆕 Lab 5: RAG Evaluation Framework

**Built:** Programmatic evaluation system using Azure AI Foundry SDK with LLM-as-judge pattern.

### Metrics Measured
| Metric | Purpose | Scale |
|--------|---------|-------|
| Groundedness | Response stays true to context | 1-5 |
| Relevance | Answers the actual question | 1-5 |
| Coherence | Logically structured | 1-5 |
| Fluency | Well-written and readable | 1-5 |

### Key Results

| Dataset | Groundedness | Relevance | Coherence | Fluency | Overall |
|---------|--------------|-----------|-----------|---------|---------|
| v1 (sparse context) | 5.0 | 2.25 | 3.38 | 3.88 | 3.63 |
| v2 (rich context) | 5.0 | **4.25** | 4.00 | 3.38 | **4.16** |

### Key Insight
> Relevance improved from 2.25 to 4.25 (+89%) simply by providing better retrieval context. This proves **retrieval quality is the bottleneck** in RAG systems, not generation quality.

### Files
- `lab5-evaluation/evaluate_rag.py` - Main evaluation script
- `lab5-evaluation/data/eval_dataset_v2.jsonl` - Rich context test set
- `lab5-evaluation/results/` - JSON evaluation outputs

### Interview Talking Point
> "I built a RAG evaluation framework measuring Groundedness, Relevance, Coherence, and Fluency using Azure AI's LLM-as-judge approach. Initial evaluation revealed low relevance scores (2.25/5), which I diagnosed as insufficient context in the retrieval step. After improving context quality, relevance jumped to 4.25/5. This demonstrated that evaluation metrics help identify whether problems are in retrieval vs generation—a critical insight for debugging RAG systems."

---

## 🆕 Lab 6: STIHL Sales Analytics Agent

**Built:** AI agent using Azure OpenAI GPT-4o with function calling to query Databricks SQL Warehouse in real-time.

### Architecture
```
┌─────────────────────────────────────────────────────────┐
│                   User Question                         │
│      "What were our top products last quarter?"         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Azure AI Agent (GPT-4o)                    │
│         Understands intent, selects tools               │
└─────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │ query_      │ │ query_      │ │ query_      │
   │ monthly_    │ │ product_    │ │ sales_      │
   │ trends()    │ │ performance()│ │ data()      │
   └─────────────┘ └─────────────┘ └─────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│            Databricks SQL Warehouse                     │
│    ai_systems.stihl_gold / ai_systems.stihl_silver     │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Synthesized Response                       │
│   "Top products in Q4: MS 500i Chainsaw ($1.34M)..."   │
└─────────────────────────────────────────────────────────┘
```

### Tools Implemented

| Function | Purpose | Databricks Table |
|----------|---------|------------------|
| `query_monthly_trends` | Time-based analysis (MoM, YoY, quarterly) | stihl_gold.monthly_trends |
| `query_product_performance` | Product analysis (BCG matrix, rankings) | stihl_gold.product_performance |
| `query_sales_data` | Transaction details, regional breakdown | stihl_silver.fact_sales |

### Sample Agent Interactions

**Q: "What were our sales trends in Q4 2024?"**
- Tool called: `query_monthly_trends(year=2024, quarter=4)`
- Result: $1.2M December revenue, Trimmers +3% MoM, detailed category breakdown

**Q: "Which products are Stars?"**
- Tool called: `query_product_performance(performance_tier='Star')`
- Result: 10 Star products identified, battery tools dominating with 75% YoY growth

**Q: "How did the West region perform?"**
- Tool called: `query_sales_data(region='West')`
- Result: $12.7M revenue, 38K units, 50.1% margin, regional breakdown

**Q: "What products should we invest in?"**
- No tool call—synthesized from conversation context
- Result: Strategic recommendations based on prior data queries

### Key Features
- ✅ Multi-turn conversation with context retention
- ✅ Automatic tool selection based on question intent
- ✅ Rich markdown responses with insights and recommendations
- ✅ Error handling for Databricks connectivity
- ✅ Iterative tool calling for complex queries

### Files
- `lab6-agent/stihl_agent.py` - Main agent with function calling
- `lab6-agent/debug_tables.py` - Schema inspection utility

### Interview Talking Point
> "I built a sales analytics agent using Azure OpenAI with function calling to Databricks. The agent understands natural language questions, selects the appropriate data tool (monthly trends, product performance, or sales data), executes SQL queries against our lakehouse, and synthesizes insights with actionable recommendations. It handles multi-turn conversations and can chain multiple tool calls for complex analytical questions."

---

## 🎤 Complete Interview Talking Points

### 1. High-Throughput ML Serving (Month 1)
> "I deployed a ResNet-50 image classification API to Azure Container Apps achieving 7 RPS with 80% cache hit rate. Key optimizations included ONNX Runtime (1.89× speedup), Redis caching with content-based hashing, and dynamic batching. The distributed inference setup achieved 9.3× throughput improvement with 4 workers."

### 2. RAG Evaluation (Lab 5)
> "I built a RAG evaluation framework measuring Groundedness, Relevance, Coherence, and Fluency. Initial evaluation showed low relevance (2.25/5). After improving retrieval context, relevance jumped to 4.25/5, proving that retrieval quality—not generation—was the bottleneck."

### 3. Agent Architecture (Lab 6)
> "I built a sales analytics agent using Azure AI Foundry with function calling to Databricks SQL. The agent decides which tool to call based on question intent, executes queries against our lakehouse, and synthesizes insights. For complex questions, it chains multiple tools automatically."

### 4. RAG Platform Comparison
> "I've built RAG systems on both Databricks and Azure. Databricks Vector Search with automatic Delta Sync is ideal when data lives in the lakehouse. Azure AI Search is better for document-heavy workloads with semantic ranking. Key insight: embeddings aren't portable—different models create incompatible vector spaces."

### 5. System Design Approach
> "For ML system design, I follow: 1) Clarify requirements, 2) High-level architecture with data flow, 3) Deep dive on scaling, caching, monitoring, 4) Trade-offs analysis. For example, choosing batch vs real-time inference depends on latency requirements, cost constraints, and data freshness needs."

---

## 🔧 Current Azure Resources

| Resource | Name | Location | Status |
|----------|------|----------|--------|
| Resource Group | `rg-ai-foundry-learning` | West US 2 | Active |
| AI Foundry Hub | `bl-az-foundry` | West US 2 | Active |
| Azure OpenAI | `blans-mjpzpu7l-westus3` | West US 3 | Active (gpt-4o deployed) |
| Databricks | `databricks-unity-ml` | West US 2 | Active |
| Azure AI Search | `stihl-sales-search` | West US 2 | Can delete (labs complete) |

### Active Endpoints
```
# Azure OpenAI (Lab 5-6)
Endpoint: https://blans-mjpzpu7l-westus3.openai.azure.com/
Model: gpt-4o

# Databricks SQL Warehouse
Host: adb-2503836992218403.3.azuredatabricks.net
HTTP Path: /sql/1.0/warehouses/4ae07b0a976375c7
Catalog: ai_systems
```

---

## ⏳ REMAINING WORK

### Month 2 Remaining (After Labs 5-6) ✅
| Project | Description | Status |
|---------|-------------|--------|
| Azure AI Foundry Labs | Labs 1-6 | ✅ COMPLETE |
| PROJECT 4 | Prompt Engineering Lab | ⏳ Next |
| PROJECT 6 | Fine-tune LLM (QLoRA) | ⏳ |
| PROJECT 7 | Real-time Feature Pipeline | ⏳ |
| AI-102 Prep | Certification study start | ⏳ |

### Month 3: MLOps & Production
| Week | Focus | Projects |
|------|-------|----------|
| Week 1 | Azure ML Pipelines, CI/CD | PROJECT 8: MLOps Pipeline |
| Week 2 | Drift Detection, Cost Optimization | PROJECT 9: Drift Detection |
| Week 2 | **TAKE AI-102 EXAM** | Certification |
| Week 3 | Security & Compliance, Interview Prep | Mock interviews |
| Week 4 | **CAPSTONE: Customer Churn Prediction** | End-to-end production system |

### Month 4: Databricks & Jobs
| Week | Focus | Projects |
|------|-------|----------|
| Week 1 | Medallion Architecture, Unity Catalog | PROJECT 10: DLT Pipeline |
| Week 2 | Feature Store, Mosaic AI, DABs | PROJECT 11: Feature Store |
| Week 3 | **FINAL CAPSTONE: Microsoft Fabric** | PROJECT 12: End-to-end AI |
| Week 4 | Portfolio Polish, Interview Blitz | Apply to positions |

---

## 💰 Cost Management

### Current Spend
| Resource | Estimated |
|----------|-----------|
| Month 1 (Azure Container Apps) | ~$15-20 |
| Labs 1-6 (Azure AI Foundry) | ~$10 |
| Azure AI Search (if still running) | ~$2.40/day |

### Cleanup Commands
```bash
# Delete AI Search after labs complete (saves ~$2.40/day)
az search service delete --name stihl-sales-search --resource-group rg-ai-foundry-learning

# Delete unused Foundry hub
az cognitiveservices account delete --name blans-mjiyrqgp-westus --resource-group rg-ai-foundry-learning
```

---

## 📋 Post Labs 5-6 Checklist

- [x] Lab 5: RAG Evaluation Framework complete
- [x] Lab 6: Sales Analytics Agent complete
- [x] Push lab code to GitHub
- [x] Update portfolio summary with Labs 5-6
- [ ] Delete Azure AI Search service (save costs)
- [ ] Delete unused Foundry hub (blans-mjiyrqgp-westus)
- [ ] Create architecture diagram for agent system
- [ ] Continue to PROJECT 4 (Prompt Engineering)
- [ ] Start AI-102 certification study

---

*Last Updated: December 29, 2025*
