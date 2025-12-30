# Lab 1: Model Selection Framework

## Overview

Systematic approach to selecting the right LLM for production workloads. This lab demonstrates how to evaluate models across multiple dimensions and make data-driven deployment decisions.

## The Model Selection Challenge

**Scenario:** Building a sales analytics assistant for STIHL dealer network.

**Requirements:**
- Natural language to SQL/insights
- Function calling capability
- Low latency (<3s response)
- Cost-effective at scale
- Content safety compliance

## Selection Framework

### 1. Define Evaluation Criteria

| Criterion | Weight | Why It Matters |
|-----------|--------|----------------|
| Task Accuracy | 30% | Must answer correctly |
| Latency | 20% | User experience |
| Cost per 1K tokens | 20% | Scale economics |
| Function Calling | 15% | Tool integration |
| Context Window | 10% | Document handling |
| Safety/Compliance | 5% | Enterprise requirement |

### 2. Candidate Models

| Model | Provider | Context | Strengths |
|-------|----------|---------|-----------|
| GPT-4o | Azure OpenAI | 128K | Best accuracy, multimodal |
| GPT-4o-mini | Azure OpenAI | 128K | Cost-effective, fast |
| GPT-4 Turbo | Azure OpenAI | 128K | Proven reliability |
| Claude 3.5 Sonnet | Anthropic | 200K | Long context, reasoning |
| Llama 3.1 70B | Meta/Azure | 128K | Open source, customizable |

### 3. Evaluation Results

#### Accuracy Benchmark (Sales Analytics Tasks)

| Model | SQL Generation | Data Analysis | Recommendations | Average |
|-------|----------------|---------------|-----------------|---------|
| GPT-4o | 94% | 92% | 88% | **91.3%** |
| GPT-4o-mini | 87% | 85% | 82% | **84.7%** |
| GPT-4 Turbo | 92% | 90% | 86% | **89.3%** |
| Claude 3.5 Sonnet | 91% | 93% | 90% | **91.3%** |
| Llama 3.1 70B | 82% | 80% | 75% | **79.0%** |

#### Latency (P50 / P95)

| Model | P50 | P95 | Meets <3s? |
|-------|-----|-----|------------|
| GPT-4o | 1.2s | 2.8s | ✅ |
| GPT-4o-mini | 0.6s | 1.4s | ✅ |
| GPT-4 Turbo | 1.8s | 4.2s | ⚠️ |
| Claude 3.5 Sonnet | 1.4s | 3.1s | ⚠️ |
| Llama 3.1 70B | 2.1s | 5.5s | ❌ |

#### Cost Analysis (per 1M tokens)

| Model | Input | Output | Blended* |
|-------|-------|--------|----------|
| GPT-4o | $2.50 | $10.00 | **$5.00** |
| GPT-4o-mini | $0.15 | $0.60 | **$0.30** |
| GPT-4 Turbo | $10.00 | $30.00 | **$16.67** |
| Claude 3.5 Sonnet | $3.00 | $15.00 | **$7.00** |
| Llama 3.1 70B | $0.90 | $0.90 | **$0.90** |

*Blended assumes 2:1 input:output ratio

#### Function Calling Quality

| Model | Tool Selection | Parameter Accuracy | Multi-tool Chains | Score |
|-------|----------------|-------------------|-------------------|-------|
| GPT-4o | Excellent | 98% | Yes | **5/5** |
| GPT-4o-mini | Good | 92% | Yes | **4/5** |
| GPT-4 Turbo | Excellent | 97% | Yes | **5/5** |
| Claude 3.5 Sonnet | Excellent | 96% | Yes | **5/5** |
| Llama 3.1 70B | Good | 85% | Limited | **3/5** |

### 4. Decision Matrix

| Model | Accuracy (30%) | Latency (20%) | Cost (20%) | Function (15%) | Context (10%) | Safety (5%) | **Total** |
|-------|----------------|---------------|------------|----------------|---------------|-------------|-----------|
| GPT-4o | 27.4 | 18 | 14 | 15 | 10 | 5 | **89.4** |
| GPT-4o-mini | 25.4 | 20 | 20 | 12 | 10 | 5 | **92.4** |
| GPT-4 Turbo | 26.8 | 14 | 8 | 15 | 10 | 5 | **78.8** |
| Claude 3.5 Sonnet | 27.4 | 16 | 12 | 15 | 10 | 5 | **85.4** |
| Llama 3.1 70B | 23.7 | 10 | 18 | 9 | 10 | 4 | **74.7** |

### 5. Final Recommendation

**Primary: GPT-4o-mini** (Score: 92.4)
- Best balance of cost, speed, and accuracy
- Excellent for high-volume production workloads
- 84.7% accuracy sufficient for most queries

**Fallback: GPT-4o** (Score: 89.4)
- Use for complex multi-step reasoning
- When GPT-4o-mini confidence is low
- Critical business decisions

**Architecture:**
```
User Query → Complexity Router → GPT-4o-mini (90% of traffic)
                              → GPT-4o (10% complex queries)
```

## Key Insights

### 1. Cost vs Accuracy Tradeoff
GPT-4o-mini is **17x cheaper** than GPT-4o with only **7% accuracy drop**. For most production use cases, this tradeoff is worth it.

### 2. Latency Matters for UX
P95 latency >3s significantly impacts user satisfaction. GPT-4 Turbo's 4.2s P95 makes it unsuitable despite high accuracy.

### 3. Function Calling is Table Stakes
All top models now support function calling well. This is no longer a differentiator—focus on accuracy and cost.

### 4. Open Source Gap
Llama 3.1 70B trails proprietary models by ~10% on complex reasoning tasks. Consider for cost-sensitive, less critical workloads.

### 5. Context Window Rarely Limiting
128K tokens is sufficient for 99% of enterprise use cases. Larger context (Claude's 200K) rarely provides practical advantage.

## Files in This Lab

```
lab1-model-selection/
├── README.md                    # This document
├── notebooks/
│   └── model_comparison.ipynb   # Benchmarking notebook
├── src/
│   ├── benchmark_runner.py      # Evaluation framework
│   └── cost_calculator.py       # Cost analysis tools
├── data/
│   └── eval_dataset.jsonl       # Test cases
└── results/
    ├── benchmark_results.json   # Raw results
    └── decision_matrix.xlsx     # Scoring spreadsheet
```

## Interview Talking Points

### Q: "How do you approach model selection?"

**Answer:**
"I use a weighted decision matrix with five key criteria: accuracy, latency, cost, capability requirements, and compliance. For our sales analytics project, I benchmarked five models across 50 test cases. GPT-4o-mini scored highest overall—it's 17x cheaper than GPT-4o with only 7% accuracy drop, and P95 latency under 1.5 seconds. I implemented a routing architecture where complex queries fall back to GPT-4o, optimizing both cost and quality."

### Q: "Why not just use the most powerful model?"

**Answer:**
"Three reasons: cost, latency, and diminishing returns. GPT-4o costs $5/million tokens vs $0.30 for GPT-4o-mini. At scale—say 10M tokens/month—that's $47K annual savings. Latency also suffers with larger models. And for 85% of queries, the accuracy difference is negligible. The key is routing complex queries to powerful models while handling routine queries efficiently."

### Q: "How do you handle model updates and deprecation?"

**Answer:**
"I build abstraction layers so the application isn't tightly coupled to a specific model. We maintain evaluation datasets to quickly benchmark new models. When GPT-4o-mini launched, we re-ran our benchmarks within a day and migrated from GPT-3.5-turbo within a week. The evaluation framework made this low-risk."

### Q: "What about open source models?"

**Answer:**
"I evaluated Llama 3.1 70B—it's compelling at $0.90/M tokens, but trailed by 10% on complex reasoning. For our use case requiring function calling and SQL generation, the gap was too large. However, for simpler tasks or when data privacy requires on-premise deployment, open source models are increasingly viable. I'd reassess with each major release."

---

*Lab 1 - Part of AI Architect Portfolio*
*Azure AI Foundry Learning Path*
