# Lab 8: Prompt Engineering - Findings Summary

## Executive Summary

Systematic prompt engineering experiments on STIHL sales analytics revealed that **GPT-4o with well-designed function calling achieves high quality without elaborate prompts**. Advanced techniques (Chain-of-Thought, Few-Shot) changed response *style* but not *accuracy* on structured queries.

## Experiment Overview

| Part | Focus | Scenarios | Variants Tested |
|------|-------|-----------|-----------------|
| Part 2 | Few-Shot & CoT | Q1, Q2 | 4 variants × 2 scenarios |
| Part 3 | Structured Outputs | Q1 | Natural vs JSON |
| Part 4 | System Prompts | Q2 | Baseline vs Optimized |

## Key Results

### Part 2: Few-Shot and Chain-of-Thought

| Variant | Q1 (Simple) | Q2 (Medium) | Average |
|---------|-------------|-------------|---------|
| Baseline | 5.0 | 5.0 | **5.0** |
| Chain-of-Thought | 5.0 | 5.0 | **5.0** |
| Few-Shot + CoT | 5.0 | 5.0 | **5.0** |
| Few-Shot | 4.5 | 5.0 | 4.75 |

**Finding:** All prompts achieved near-perfect scores. Few-shot alone slightly underperformed due to added complexity without benefit.

### Part 3: Structured Outputs

| Format | JSON Valid | Evaluation Score |
|--------|------------|------------------|
| Natural Language | N/A | 5.0 |
| Structured JSON | ✅ Yes | 3.25 |

**Finding:** JSON output was schema-valid but scored lower on natural language metrics. This revealed evaluator-format mismatch, not output quality issues.

**Insight:** Evaluation criteria must match output format. Use schema validation for JSON, LLM-as-judge for prose.

### Part 4: System Prompt Engineering

| Prompt | Response Length | Score |
|--------|-----------------|-------|
| Baseline (2 lines) | 1,566 chars | 5.0 |
| Optimized (detailed) | 1,639 chars | 5.0 |

**Finding:** Elaborate system prompts did not improve accuracy over minimal prompts.

## Critical Discovery: Schema Matters More Than Prompts

Early experiments showed catastrophic failures (scores 1.5-2.0) due to **tool schema mismatches**, not prompt quality:

| Issue | Impact | Resolution |
|-------|--------|------------|
| Wrong column names in tools | Tools returned errors | Updated to match actual Databricks schema |
| Few-shot with fake data | Model hallucinated when tools failed | Used placeholders + "only use real data" constraints |

**Lesson:** Robust tool definitions are more critical than sophisticated prompts.

## Production Recommendations

### 1. Keep Prompts Simple
```
❌ Elaborate: 500+ token system prompt with CoT framework
✅ Effective: "You are a sales analyst. Answer using the tools. Be accurate."
```

### 2. Invest in Tool Quality
- Accurate schema descriptions
- Clear CANNOT constraints (from Lab 7 MCP patterns)
- Helpful error messages

### 3. Match Evaluation to Use Case
| Use Case | Output Format | Evaluation Method |
|----------|---------------|-------------------|
| Chat interface | Natural language | LLM-as-judge |
| API integration | JSON | Schema validation |
| Reports | Markdown | Human review |

### 4. When to Use Advanced Prompts
- **Few-shot:** When specific output format is critical
- **Chain-of-thought:** For multi-step reasoning tasks (not simple lookups)
- **System personas:** For consistent tone/style across conversations

## Cost-Benefit Analysis

| Approach | Prompt Tokens | Quality | Recommendation |
|----------|---------------|---------|----------------|
| Baseline | ~100 | Excellent | ✅ Use for production |
| CoT | ~300 | Excellent | Use for complex reasoning |
| Few-shot | ~600 | Good | Use sparingly |
| Few-shot + CoT | ~800 | Excellent | Overkill for most cases |

**Estimated savings:** 5-8x token reduction by using baseline over elaborate prompts.

## Interview Talking Points

1. **Methodology:** "I built an automated prompt evaluation framework using LLM-as-judge with four metrics: groundedness, relevance, coherence, and fluency."

2. **Discovery:** "Initial experiments revealed that schema mismatches caused hallucinations. Few-shot examples with fake data made the model MORE likely to fabricate when tools failed."

3. **Insight:** "GPT-4o with well-designed function calling achieved excellent results without elaborate prompts. This informed our production decision to prioritize tool quality over prompt complexity."

4. **Trade-off:** "Advanced prompts change output STYLE but not necessarily ACCURACY. The choice depends on use case - structured JSON for APIs, natural language for chat."

## Files and Artifacts

```
lab8-prompt-engineering/
├── results/
│   └── part2_results.json    # Full evaluation data
├── prompts/
│   ├── few_shot/templates.md
│   ├── cot/templates.md
│   └── system/production_prompt.json
└── FINDINGS.md               # This document
```

## Next Steps

1. **Test on edge cases:** Ambiguous queries, missing data scenarios
2. **A/B test in production:** Compare user satisfaction with different prompts
3. **Evaluate cost:** Track token usage per prompt variant over time

---

*Lab 8 completed: December 29, 2025*
*Part of AI Architect Portfolio - Month 2*
