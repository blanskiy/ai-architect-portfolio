# Lab 5: RAG Evaluation Framework

## Overview
Built programmatic evaluation system using Azure AI Foundry SDK with LLM-as-judge pattern.

## Metrics Measured
- **Groundedness**: Does response stay true to context?
- **Relevance**: Does it answer the question?
- **Coherence**: Is it logically structured?
- **Fluency**: Is it well-written?

## Key Results

| Dataset | Groundedness | Relevance | Coherence | Fluency | Overall |
|---------|--------------|-----------|-----------|---------|---------|
| v1 (sparse context) | 5.0 | 2.25 | 3.38 | 3.88 | 3.63 |
| v2 (rich context) | 5.0 | 4.25 | 4.00 | 3.38 | 4.16 |

## Key Insight
Relevance improved +2.0 points with better context, proving retrieval quality is the bottleneck in RAG systems.

## Files
- `evaluate_rag.py` - Main evaluation script
- `data/eval_dataset.jsonl` - Sparse context test
- `data/eval_dataset_v2.jsonl` - Rich context test  
- `results/` - JSON evaluation outputs

## Azure Resources
- Endpoint: https://blans-mjpzpu7l-westus3.openai.azure.com/
- Model: gpt-4o (for generation and judging)

## Interview Talking Point
> "I built a RAG evaluation framework measuring Groundedness, Relevance, Coherence, and Fluency. Initial evaluation showed low relevance (2.25/5). After improving retrieval context, relevance jumped to 4.25/5. This demonstrated that evaluation metrics help identify whether problems are in retrieval vs generation - critical for debugging RAG systems."
