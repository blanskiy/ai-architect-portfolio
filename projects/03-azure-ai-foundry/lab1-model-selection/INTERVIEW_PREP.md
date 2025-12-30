# Model Selection - Interview Cheat Sheet

## Quick Framework (30-second answer)

"I use a **weighted decision matrix** with 5 criteria:
1. **Accuracy** (30%) - Task-specific benchmarks
2. **Latency** (20%) - P50 and P95 response times
3. **Cost** (20%) - Per-token pricing at scale
4. **Capabilities** (15%) - Function calling, context window
5. **Compliance** (15%) - Safety, enterprise requirements

Then I implement **intelligent routing** - simple queries go to cost-effective models, complex ones to premium models."

---

## Key Numbers to Remember

| Comparison | GPT-4o | GPT-4o-mini |
|------------|--------|-------------|
| Accuracy | ~93% | ~85% |
| P50 Latency | 1.2s | 0.6s |
| Cost/1M tokens | $5.00 | $0.30 |
| **Cost ratio** | 17x more | **Baseline** |

**Bottom line:** GPT-4o-mini is 17x cheaper with only 8% accuracy drop.

---

## Three Scenarios

### "We need the best quality"
→ "Best ≠ most expensive. I'd benchmark on YOUR tasks. Often GPT-4o-mini at 85% accuracy is sufficient for 90% of queries. Route the complex 10% to GPT-4o."

### "Budget is tight"
→ "GPT-4o-mini at $0.30/M tokens. At 10M tokens/month, that's $36/year vs $600 for GPT-4o. For simple tasks, even Llama 3.1 8B at $0.20/M works."

### "We need real-time responses"
→ "Latency matters. GPT-4 Turbo has 4.2s P95—too slow for chat. GPT-4o-mini at 1.4s P95 is best. Larger ≠ faster."

---

## Handling Tricky Questions

### "Why not just use the best model?"
"Three reasons: cost (17x more), latency (2x slower), and diminishing returns. 85% of queries don't need GPT-4o's capabilities."

### "What about open source?"
"Evaluated Llama 3.1 70B—10% accuracy gap on complex reasoning. Great for cost-sensitive or on-premise needs. I'd reassess each major release."

### "How do you handle model deprecation?"
"Abstraction layers. We maintain eval datasets to benchmark new models quickly. When GPT-4o-mini launched, we migrated from 3.5-turbo in a week."

### "How do you know which queries need the premium model?"
"Query complexity classifier. Long prompts, multi-step reasoning, ambiguous questions → GPT-4o. Factual lookups, simple formatting → mini."

---

## Real Example from Portfolio

"For our STIHL sales analytics agent, I benchmarked 5 models on 50 tasks across SQL generation, data analysis, and recommendations.

**Results:**
- GPT-4o: 91% accuracy, $5/M tokens
- GPT-4o-mini: 85% accuracy, $0.30/M tokens

**Decision:** GPT-4o-mini as primary (90% of traffic), GPT-4o as fallback for complex SQL and multi-step analysis.

**Impact:** $47K annual savings at 10M tokens/month scale, <1.5s P95 latency, acceptable quality tradeoff."

---

## Red Flags to Avoid

❌ "I always use GPT-4 because it's the best"
❌ "We don't track costs"
❌ "Latency doesn't matter for our use case"
❌ "We picked based on the website marketing"

✅ "I benchmark on our specific tasks"
✅ "I model costs at production scale"
✅ "I measure P95 latency, not just averages"
✅ "I have fallback strategies for complex queries"
