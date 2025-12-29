# Lab 8: Prompt Engineering

## Overview
Systematic prompt engineering experiments applied to STIHL sales analytics, with LLM-as-judge evaluation (Lab 5) and agent integration (Lab 6).

## Objectives
1. **Part 2:** Master few-shot and chain-of-thought techniques
2. **Part 3:** Implement structured JSON outputs with validation
3. **Part 4:** Engineer optimized system prompts for the sales agent

## Prerequisites
- Lab 5: Evaluation framework (LLM-as-judge)
- Lab 6: STIHL Sales Agent (Databricks function calling)
- Lab 7: MCP patterns (tool descriptions)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Prompt Engineering Pipeline                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   Test Query ──▶ Prompt Variant ──▶ Lab 6 Agent        │
│                                          │              │
│                                          ▼              │
│                                   Databricks SQL        │
│                                          │              │
│                                          ▼              │
│                                    Response             │
│                                          │              │
│                                          ▼              │
│                              Lab 5 Evaluator            │
│                           (Groundedness, Relevance,     │
│                            Coherence, Fluency)          │
│                                          │              │
│                                          ▼              │
│                              Results Dashboard          │
└─────────────────────────────────────────────────────────┘
```

## Test Scenarios

| ID | Query | Complexity |
|----|-------|------------|
| Q1 | Top 3 products by revenue last quarter | Simple |
| Q2 | Analyze chainsaw category trend and explain why | Medium |
| Q3 | Compare regional performance and recommend focus areas | Complex |
| Q4 | Identify anomalies in recent sales patterns | Complex |

## Project Structure

```
03-azure-ai-foundry/
├── lab5-evaluation/          # LLM-as-judge framework
├── lab6-agent/               # STIHL Sales Agent
├── lab7-mcp/                 # MCP integration
└── lab8-prompt-engineering/  # ◀ THIS LAB
    ├── config.py             # Azure OpenAI & Databricks config
    ├── evaluator.py          # Lab 5 integration
    ├── agent_integration.py  # Lab 6 integration
    ├── part2_few_shot_cot.py # Few-shot & CoT experiments
    ├── part3_structured_outputs.py
    ├── part4_system_prompts.py
    ├── prompts/
    │   ├── baseline/         # Control prompts
    │   ├── few_shot/         # Few-shot examples
    │   ├── cot/              # Chain-of-thought templates
    │   ├── structured/       # JSON schemas
    │   └── system/           # Optimized personas
    └── results/
        └── evaluation_results.json
```

## Quick Start

```bash
# From project root
cd projects/03-azure-ai-foundry/lab8-prompt-engineering

# Quick test (1 scenario, all 4 variants)
python part2_few_shot_cot.py --quick

# Full experiment (2 scenarios)
python part2_few_shot_cot.py

# Test system prompts
python part4_system_prompts.py
```

## Prompt Variants Tested

| Variant | Description | Expected Benefit |
|---------|-------------|------------------|
| Baseline | Minimal instruction | Control group |
| Few-shot | Example Q&A pairs | Better format, consistency |
| Chain-of-thought | Step-by-step reasoning | Improved accuracy on complex queries |
| Few-shot + CoT | Combined approach | Best overall quality |

## Key Metrics (from Lab 5)

- **Groundedness:** Claims supported by retrieved data (target: 4.5+)
- **Relevance:** Directly answers the question (target: 4.5+)
- **Coherence:** Logical structure and flow (target: 4.0+)
- **Fluency:** Professional language quality (target: 4.0+)

## Dependencies

```bash
pip install openai databricks-sql-connector python-dotenv pandas
```

## Integration Points

| This Lab | Integrates With | How |
|----------|-----------------|-----|
| `evaluator.py` | Lab 5 | Reuses LLM-as-judge evaluation metrics |
| `agent_integration.py` | Lab 6 | Wraps STIHL Sales Agent for testing |
| Tool descriptions | Lab 7 | CANNOT sections prevent hallucination |

## Expected Outcomes

1. **Quantified improvement:** Baseline vs. optimized prompt scores
2. **Best practices:** Which techniques work for which query types
3. **Production prompt:** Optimized system prompt for Lab 6 agent
4. **Portfolio artifact:** Comparative analysis demonstrating prompt engineering skill

---
*Part of AI Architect Portfolio - Month 2, Azure AI Foundry Labs*
