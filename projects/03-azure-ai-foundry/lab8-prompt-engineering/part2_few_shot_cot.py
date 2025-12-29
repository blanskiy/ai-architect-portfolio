"""
Lab 8: Prompt Engineering - Part 2
Few-Shot and Chain-of-Thought Experiments

UPDATED: December 29, 2025
- Fixed few-shot examples to use placeholders instead of fake data
- Prevents hallucination when tool calls fail
"""

import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass

from config import TEST_SCENARIOS, eval_config, validate_config
from evaluator import PromptEvaluator, FullEvaluation, compare_evaluations, print_comparison_report
from agent_integration import STIHLSalesAgent, AgentResponse


# =============================================================================
# PROMPT VARIANTS - UPDATED TO PREVENT HALLUCINATION
# =============================================================================

PROMPT_VARIANTS = {
    "baseline": """You are a sales analytics assistant for STIHL. 
Answer questions about sales data using the available tools.
Be helpful and accurate. 
IMPORTANT: Only report data that is actually returned by the tools. If a tool returns an error, explain the issue - do not make up data.""",

    "few_shot": """You are a STIHL Sales Analytics Expert. Your role is to provide accurate, data-driven insights.

RESPONSE FORMAT EXAMPLES (use actual data from tools, not these placeholder values):

EXAMPLE 1 - Product Rankings:
User: What are our best-selling products?
Assistant: Based on the sales data, here are your top performers:

1. **[Product Name]** - $[X] revenue ([Y] units)
   - Growth: [Z]% YoY
   - Rank: #[N] overall

2. **[Product Name]** - $[X] revenue ([Y] units)
   - Growth: [Z]% YoY

[Continue for requested number of products]

Key Insight: [Observation about the data pattern]

EXAMPLE 2 - Trend Analysis:
User: How is [category] trending?
Assistant: [Category] performance over the past [time period]:

**Summary:**
- Total Revenue: $[X] 
- Growth: [Y]% vs prior period
- Top Product: [Name]

**Monthly Breakdown:**
[List months with revenue and growth]

**Recommendation:** [Actionable insight based on data]

---

CRITICAL RULES:
1. ONLY use data returned by the tools - never invent numbers
2. If a tool returns an error, explain the error and suggest alternatives
3. Always cite the actual values from the retrieved data
4. Use the format above but populate with REAL data only""",

    "chain_of_thought": """You are a STIHL Sales Analytics Expert.

When answering questions, follow this analytical process:

STEP 1: UNDERSTAND THE QUESTION
- What metric or insight is being requested?
- What time period is relevant?
- Are there any filters needed (region, category)?

STEP 2: GATHER THE DATA
- Use the appropriate tool(s) to retrieve relevant data
- If a tool fails, try an alternative approach or explain the limitation

STEP 3: ANALYZE THE DATA
- Look at the ACTUAL data returned by the tools
- Calculate relevant metrics from the real numbers
- Identify patterns in the retrieved data

STEP 4: FORMULATE YOUR RESPONSE
- Lead with the direct answer using ACTUAL data
- Support with specific numbers FROM THE TOOL RESULTS
- Add context based on what the data shows

STEP 5: VERIFY
- Are all numbers in my response from the tool results?
- Did I avoid making up any data?
- If data was unavailable, did I explain why?

CRITICAL: Never fabricate data. Only report what the tools return.""",

    "few_shot_cot": """You are a STIHL Sales Analytics Expert providing data-driven business insights.

ANALYTICAL FRAMEWORK:
1. What exactly is being asked? (metric, timeframe, scope)
2. What data do I need? (which tools, what filters)
3. What does the ACTUAL data show? (from tool results only)
4. What's the business implication?

RESPONSE FORMAT (populate with REAL data from tools):

**[Direct Answer to Question]**

**Data Summary:**
- [Metric 1]: [Actual value from tools]
- [Metric 2]: [Actual value from tools]
- [Metric 3]: [Actual value from tools]

**Analysis:**
[Insights based on the actual retrieved data]

**Recommendation:**
[Action based on real data patterns]

---

CRITICAL RULES:
1. WAIT for tool results before writing numbers
2. If tools return errors, explain the issue honestly
3. Never copy numbers from these examples - use only real data
4. If you can't get the data, say so and suggest alternatives

Apply analytical rigor while maintaining strict data accuracy.""",
}


# =============================================================================
# EXPERIMENT RUNNER (unchanged logic)
# =============================================================================

@dataclass
class ExperimentResult:
    """Results from a single experiment run."""
    scenario_id: str
    query: str
    prompt_variant: str
    agent_response: AgentResponse
    evaluation: FullEvaluation
    

class PromptExperiment:
    """Runs prompt engineering experiments with evaluation."""
    
    def __init__(self, output_dir: str = "results"):
        self.evaluator = PromptEvaluator()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results: list[ExperimentResult] = []
    
    def run_variant(self, scenario: dict, variant_name: str, 
                    system_prompt: str) -> ExperimentResult:
        """Run a single scenario with a specific prompt variant."""
        
        print(f"\n{'─'*60}")
        print(f"🧪 {scenario['id']} × {variant_name}")
        print(f"   Query: {scenario['query'][:55]}...")
        
        agent = STIHLSalesAgent(system_prompt=system_prompt)
        
        try:
            response = agent.run(scenario['query'], variant_name)
            
            print(f"   Tools called: {len(response.tool_calls)}")
            print(f"   Response length: {len(response.response)} chars")
            
            evaluation = self.evaluator.evaluate_response(
                query=scenario['query'],
                response=response.response,
                context=response.context,
                prompt_variant=variant_name
            )
            
            result = ExperimentResult(
                scenario_id=scenario['id'],
                query=scenario['query'],
                prompt_variant=variant_name,
                agent_response=response,
                evaluation=evaluation
            )
            
            self.results.append(result)
            return result
            
        finally:
            agent.close()
    
    def run_all_variants(self, scenario: dict) -> list[ExperimentResult]:
        """Run all prompt variants for a single scenario."""
        
        scenario_results = []
        
        for variant_name, system_prompt in PROMPT_VARIANTS.items():
            result = self.run_variant(scenario, variant_name, system_prompt)
            scenario_results.append(result)
        
        return scenario_results
    
    def run_full_experiment(self, scenarios: list[dict] = None):
        """Run complete experiment across all scenarios and variants."""
        
        scenarios = scenarios or TEST_SCENARIOS
        
        print("\n" + "="*70)
        print("🚀 LAB 8: PROMPT ENGINEERING EXPERIMENT")
        print("   Part 2: Few-Shot and Chain-of-Thought (Updated)")
        print("="*70)
        print(f"\n📋 Scenarios: {len(scenarios)}")
        print(f"📝 Variants: {list(PROMPT_VARIANTS.keys())}")
        print(f"🔢 Total runs: {len(scenarios) * len(PROMPT_VARIANTS)}")
        
        all_results = {}
        
        for scenario in scenarios:
            print(f"\n\n{'═'*70}")
            print(f"📊 SCENARIO: {scenario['id']} ({scenario['complexity'].upper()})")
            print(f"   {scenario['query']}")
            print(f"{'═'*70}")
            
            scenario_results = self.run_all_variants(scenario)
            all_results[scenario['id']] = scenario_results
            
            evaluations = [r.evaluation for r in scenario_results]
            comparison = compare_evaluations(evaluations)
            print_comparison_report(comparison)
        
        self._save_results(all_results)
        self._print_overall_summary(all_results)
        
        return all_results
    
    def _save_results(self, all_results: dict):
        """Save experiment results to JSON."""
        
        output = {
            "experiment": "Lab 8 Part 2: Few-Shot and Chain-of-Thought (Updated)",
            "timestamp": datetime.now().isoformat(),
            "variants_tested": list(PROMPT_VARIANTS.keys()),
            "scenarios": {}
        }
        
        for scenario_id, results in all_results.items():
            output["scenarios"][scenario_id] = {
                "query": results[0].query,
                "results": []
            }
            
            for result in results:
                output["scenarios"][scenario_id]["results"].append({
                    "variant": result.prompt_variant,
                    "response": result.agent_response.response,
                    "tool_calls": result.agent_response.tool_calls,
                    "tokens_used": result.agent_response.tokens_used,
                    "evaluation": result.evaluation.to_dict()
                })
        
        output_file = self.output_dir / "part2_results.json"
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        print(f"\n💾 Results saved: {output_file}")
    
    def _print_overall_summary(self, all_results: dict):
        """Print overall experiment summary."""
        
        print("\n" + "="*70)
        print("📊 OVERALL EXPERIMENT SUMMARY")
        print("="*70)
        
        variant_scores = {v: [] for v in PROMPT_VARIANTS.keys()}
        
        for scenario_results in all_results.values():
            for result in scenario_results:
                variant_scores[result.prompt_variant].append(
                    result.evaluation.average_score
                )
        
        print("\n📈 Average Scores by Variant:")
        print("-"*50)
        
        variant_averages = []
        for variant, scores in variant_scores.items():
            avg = sum(scores) / len(scores) if scores else 0
            variant_averages.append((variant, avg))
        
        variant_averages.sort(key=lambda x: x[1], reverse=True)
        
        for i, (variant, avg) in enumerate(variant_averages):
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "  "
            bar = "█" * int(avg * 4)
            print(f"   {medal} {variant:15} {avg:.2f} {bar}")
        
        winner_name, winner_score = variant_averages[0]
        baseline_score = next(s for v, s in variant_averages if v == "baseline")
        
        print(f"\n🏆 Best Overall: {winner_name}")
        print(f"   Score: {winner_score:.2f}/5.0")
        
        if winner_name != "baseline":
            improvement = winner_score - baseline_score
            pct = (improvement / baseline_score) * 100
            print(f"   vs Baseline: +{improvement:.2f} ({pct:.1f}% improvement)")
        
        print("\n🎯 Best Variant per Scenario:")
        for scenario_id, results in all_results.items():
            best = max(results, key=lambda r: r.evaluation.average_score)
            print(f"   {scenario_id}: {best.prompt_variant} ({best.evaluation.average_score:.2f})")
        
        print("\n" + "="*70)


def run_quick_test():
    """Run quick test with just one scenario."""
    print("🧪 Quick Test Mode: Q1 only, all variants")
    experiment = PromptExperiment()
    return experiment.run_full_experiment([TEST_SCENARIOS[0]])


def run_standard_experiment():
    """Run standard experiment with Q1 and Q2."""
    print("📊 Standard Mode: Q1 + Q2, all variants")
    experiment = PromptExperiment()
    return experiment.run_full_experiment(TEST_SCENARIOS[:2])


def run_full_experiment():
    """Run full experiment with all scenarios."""
    print("🔬 Full Mode: All scenarios, all variants")
    experiment = PromptExperiment()
    return experiment.run_full_experiment()


if __name__ == "__main__":
    import sys
    
    print("Lab 8: Prompt Engineering - Part 2 (Updated)")
    print("="*50)
    
    if not validate_config():
        print("\n❌ Fix configuration before running experiment")
        sys.exit(1)
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "--quick":
            run_quick_test()
        elif mode == "--full":
            run_full_experiment()
        else:
            print(f"Unknown mode: {mode}")
            print("Usage: python part2_few_shot_cot.py [--quick|--full]")
    else:
        run_standard_experiment()
