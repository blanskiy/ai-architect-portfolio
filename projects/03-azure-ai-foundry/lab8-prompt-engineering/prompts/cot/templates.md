# Chain-of-Thought Prompt Templates

## Purpose
Step-by-step reasoning frameworks to improve response accuracy on complex queries.

---

## Template: Standard 5-Step CoT

```text
When answering questions, follow this analytical process:

STEP 1: UNDERSTAND THE QUESTION
- What metric or insight is being requested?
- What time period is relevant?
- Are there filters (region, category, product)?

STEP 2: PLAN DATA RETRIEVAL
- Which tool(s) will provide needed data?
- What parameters should I use?

STEP 3: ANALYZE THE DATA
- What patterns or trends emerge?
- What calculations are needed? (growth rates, percentages)
- Are there anomalies?

STEP 4: FORMULATE RESPONSE
- Lead with direct answer
- Support with specific data points
- Add context and recommendations

STEP 5: VERIFY
- Does this fully answer the question?
- Are all claims supported by data?
```

---

## Template: Comparison CoT

Use for questions comparing products, regions, or time periods.

```text
For comparison questions:

1. IDENTIFY COMPARISON
   - Items being compared: [list]
   - Metric(s): [revenue, growth, etc.]
   - Time period: [specify]

2. GATHER COMPARABLE DATA
   - Same time periods for all items
   - Consistent metrics
   - Note any data gaps

3. ANALYZE DIFFERENCES
   - Absolute: Item A is $X more than B
   - Relative: Item A is X% higher than B
   - Rank order: 1st, 2nd, 3rd

4. EXPLAIN DIFFERENCES
   - What drives the gap?
   - Is this expected or surprising?

5. SYNTHESIZE
   - Clear winner(s)
   - Trade-offs
   - Recommendations
```

---

## Template: Trend Analysis CoT

Use for time-series and trend questions.

```text
For trend questions:

1. IDENTIFY THE TREND
   - Metric: [revenue, units, etc.]
   - Time range: [last N months]
   - Granularity: [daily, weekly, monthly]

2. MEASURE THE TREND
   - Direction: up / down / flat / volatile
   - Magnitude: X% change over period
   - Consistency: steady or irregular

3. CONTEXTUALIZE
   - Seasonality: expected for this time?
   - vs. Last year: better or worse?
   - vs. Company average: above or below?

4. IMPLICATIONS
   - If trend continues: [projection]
   - Risks: [what could reverse it]
   - Opportunities: [what could accelerate]

5. RECOMMEND
   - Actions to consider
   - What to monitor
```

---

## Template: Self-Verification CoT

Add to any prompt for accuracy improvement.

```text
After formulating your response, verify:

CHECK 1: Data Source
- Did I use the right tool for this question?
- Is the data fresh enough?

CHECK 2: Accuracy
- Are my calculations correct?
- Did I answer what was actually asked?

CHECK 3: Grounding
- Are there any claims not supported by data?
- Should I hedge any statements?

If issues found, revise before delivering.
```

---

## When to Use CoT

| Query Type | Recommended Template |
|------------|---------------------|
| Simple factual | Skip CoT (overhead not worth it) |
| Rankings/comparisons | Comparison CoT |
| Trend analysis | Trend Analysis CoT |
| Complex multi-part | Standard 5-Step + Self-Verification |
| Anomaly detection | Standard + extra verification |
