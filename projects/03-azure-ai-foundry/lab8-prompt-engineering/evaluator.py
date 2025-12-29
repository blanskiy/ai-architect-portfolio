"""
Lab 8: Prompt Engineering - Evaluator
LLM-as-Judge evaluation framework (integrated from Lab 5).

This module provides the same evaluation approach as Lab 5,
applied to prompt engineering experiments.

Metrics:
- Groundedness: Are claims supported by the retrieved data?
- Relevance: Does the response answer the question?
- Coherence: Is the response logically structured?
- Fluency: Is the language professional and clear?
"""

import json
from typing import Optional
from dataclasses import dataclass, asdict
from openai import AzureOpenAI
from config import azure_config, eval_config


@dataclass
class EvaluationResult:
    """Single metric evaluation result."""
    metric: str
    score: float
    reasoning: str


@dataclass 
class FullEvaluation:
    """Complete evaluation of a response."""
    query: str
    response: str
    context: str
    prompt_variant: str
    groundedness: EvaluationResult
    relevance: EvaluationResult
    coherence: EvaluationResult
    fluency: EvaluationResult
    
    @property
    def average_score(self) -> float:
        """Calculate average across all metrics."""
        scores = [
            self.groundedness.score,
            self.relevance.score,
            self.coherence.score,
            self.fluency.score
        ]
        return sum(scores) / len(scores)
    
    @property
    def passes_threshold(self) -> bool:
        """Check if average meets passing threshold."""
        return self.average_score >= eval_config.passing_threshold
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "query": self.query,
            "response": self.response[:500] + "..." if len(self.response) > 500 else self.response,
            "context": self.context[:500] + "..." if len(self.context) > 500 else self.context,
            "prompt_variant": self.prompt_variant,
            "scores": {
                "groundedness": asdict(self.groundedness),
                "relevance": asdict(self.relevance),
                "coherence": asdict(self.coherence),
                "fluency": asdict(self.fluency),
            },
            "average_score": round(self.average_score, 2),
            "passes_threshold": self.passes_threshold
        }


class PromptEvaluator:
    """
    LLM-as-Judge evaluator for prompt engineering experiments.
    Uses GPT-4o to score responses on multiple quality dimensions.
    
    Based on Lab 5 evaluation framework.
    """
    
    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=azure_config.endpoint,
            api_key=azure_config.api_key,
            api_version=azure_config.api_version
        )
        self.model = azure_config.eval_deployment
    
    def _create_evaluation_prompt(self, metric: str, query: str, 
                                   response: str, context: str) -> str:
        """Create evaluation prompt for a specific metric."""
        
        metric_definitions = {
            "groundedness": """
GROUNDEDNESS measures whether the response's claims are supported by the provided context/data.
- Score 5: All claims directly supported by context, no hallucinations
- Score 4: Most claims supported, minor unsupported details
- Score 3: Mix of supported and unsupported claims
- Score 2: Many claims not supported by context
- Score 1: Response largely fabricated or contradicts context
""",
            "relevance": """
RELEVANCE measures whether the response directly addresses the user's question.
- Score 5: Fully addresses all aspects of the question
- Score 4: Addresses main question with minor gaps
- Score 3: Partially addresses question, misses key aspects
- Score 2: Tangentially related, doesn't answer core question
- Score 1: Completely off-topic or irrelevant
""",
            "coherence": """
COHERENCE measures the logical structure and flow of the response.
- Score 5: Excellent structure, clear progression, well-organized
- Score 4: Good structure with minor organizational issues
- Score 3: Adequate structure but some logical gaps
- Score 2: Disorganized, hard to follow
- Score 1: Incoherent, no logical structure
""",
            "fluency": """
FLUENCY measures the language quality and professionalism.
- Score 5: Professional, clear, appropriate tone for business context
- Score 4: Good language with minor issues
- Score 3: Acceptable but could be clearer
- Score 2: Awkward phrasing, unclear language
- Score 1: Poor grammar, unprofessional
"""
        }
        
        return f"""You are an expert evaluator assessing AI-generated responses for quality.

{metric_definitions[metric]}

CONTEXT (Data retrieved from database):
{context[:2000]}

USER QUESTION:
{query}

AI RESPONSE TO EVALUATE:
{response}

Evaluate the response for {metric.upper()}.

Respond in this exact JSON format:
{{
    "score": <1-5>,
    "reasoning": "<brief explanation of score>"
}}

JSON Response:"""

    def evaluate_metric(self, metric: str, query: str, 
                       response: str, context: str) -> EvaluationResult:
        """Evaluate a single metric using LLM-as-judge."""
        
        prompt = self._create_evaluation_prompt(metric, query, response, context)
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise evaluator. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temp for consistent evaluation
                max_tokens=200
            )
            
            result_text = completion.choices[0].message.content.strip()
            
            # Handle potential markdown code blocks
            if result_text.startswith("```"):
                lines = result_text.split("\n")
                result_text = "\n".join(lines[1:-1])
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            
            result = json.loads(result_text)
            return EvaluationResult(
                metric=metric,
                score=float(result["score"]),
                reasoning=result["reasoning"]
            )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  ⚠️  Could not parse evaluation for {metric}: {e}")
            return EvaluationResult(
                metric=metric,
                score=3.0,  # Default middle score on error
                reasoning=f"Evaluation parse error: {str(e)}"
            )
        except Exception as e:
            print(f"  ❌ Evaluation failed for {metric}: {e}")
            return EvaluationResult(
                metric=metric,
                score=0.0,
                reasoning=f"Evaluation failed: {str(e)}"
            )
    
    def evaluate_response(self, query: str, response: str, 
                         context: str, prompt_variant: str) -> FullEvaluation:
        """
        Run full evaluation on a response.
        
        Args:
            query: The user's original question
            response: The AI-generated response to evaluate
            context: The data/context that was retrieved (for grounding check)
            prompt_variant: Name of the prompt technique used
        
        Returns:
            FullEvaluation with all metric scores
        """
        print(f"\n📊 Evaluating: {prompt_variant}")
        
        results = {}
        for metric in eval_config.metrics:
            print(f"   {metric}...", end=" ", flush=True)
            result = self.evaluate_metric(metric, query, response, context)
            results[metric] = result
            print(f"{result.score:.1f}")
        
        evaluation = FullEvaluation(
            query=query,
            response=response,
            context=context,
            prompt_variant=prompt_variant,
            groundedness=results["groundedness"],
            relevance=results["relevance"],
            coherence=results["coherence"],
            fluency=results["fluency"]
        )
        
        status = "✅" if evaluation.passes_threshold else "⚠️"
        print(f"   {status} Average: {evaluation.average_score:.2f}/5.0")
        
        return evaluation


def compare_evaluations(evaluations: list[FullEvaluation]) -> dict:
    """
    Compare multiple evaluations to find the best prompt variant.
    
    Returns summary with rankings and improvements.
    """
    if not evaluations:
        return {"error": "No evaluations to compare"}
    
    # Sort by average score
    sorted_evals = sorted(evaluations, key=lambda e: e.average_score, reverse=True)
    
    comparison = {
        "ranking": [],
        "best_variant": sorted_evals[0].prompt_variant,
        "best_score": sorted_evals[0].average_score,
        "metric_winners": {},
        "improvement_from_baseline": None
    }
    
    # Build ranking
    for i, eval in enumerate(sorted_evals, 1):
        comparison["ranking"].append({
            "rank": i,
            "variant": eval.prompt_variant,
            "average_score": round(eval.average_score, 2),
            "scores": {
                "groundedness": eval.groundedness.score,
                "relevance": eval.relevance.score,
                "coherence": eval.coherence.score,
                "fluency": eval.fluency.score
            }
        })
    
    # Find best variant per metric
    for metric in eval_config.metrics:
        best = max(evaluations, key=lambda e: getattr(e, metric).score)
        comparison["metric_winners"][metric] = {
            "variant": best.prompt_variant,
            "score": getattr(best, metric).score
        }
    
    # Calculate improvement from baseline if present
    baseline = next((e for e in evaluations if e.prompt_variant == "baseline"), None)
    if baseline and sorted_evals[0].prompt_variant != "baseline":
        improvement = sorted_evals[0].average_score - baseline.average_score
        comparison["improvement_from_baseline"] = {
            "absolute": round(improvement, 2),
            "percentage": round((improvement / baseline.average_score) * 100, 1)
        }
    
    return comparison


def print_comparison_report(comparison: dict):
    """Print a formatted comparison report."""
    print("\n" + "="*60)
    print("📈 PROMPT VARIANT COMPARISON")
    print("="*60)
    
    print(f"\n🏆 Best Variant: {comparison['best_variant']}")
    print(f"   Score: {comparison['best_score']:.2f}/5.0")
    
    if comparison.get("improvement_from_baseline"):
        imp = comparison["improvement_from_baseline"]
        print(f"\n📊 Improvement over baseline: +{imp['absolute']:.2f} ({imp['percentage']:.1f}%)")
    
    print("\n📋 Ranking:")
    print("-"*50)
    medals = ["🥇", "🥈", "🥉", "  "]
    for entry in comparison["ranking"]:
        medal = medals[min(entry["rank"]-1, 3)]
        print(f"{medal} #{entry['rank']} {entry['variant']}: {entry['average_score']:.2f}")
        s = entry["scores"]
        print(f"      G:{s['groundedness']:.1f} R:{s['relevance']:.1f} C:{s['coherence']:.1f} F:{s['fluency']:.1f}")
    
    print("\n🎯 Best per Metric:")
    for metric, winner in comparison["metric_winners"].items():
        print(f"   {metric.capitalize()}: {winner['variant']} ({winner['score']:.1f})")
    
    print("="*60)


if __name__ == "__main__":
    from config import validate_config
    
    print("Lab 8: Evaluator Test")
    print("="*50)
    
    if not validate_config():
        print("\n⚠️  Fix configuration before running evaluator")
        exit(1)
    
    # Quick test
    evaluator = PromptEvaluator()
    
    test_eval = evaluator.evaluate_response(
        query="What were the top products last quarter?",
        response="Based on the sales data, the top 3 products were: 1) MS 261 Chainsaw ($450K), 2) BR 600 Blower ($380K), 3) FS 91 Trimmer ($320K).",
        context="Product sales Q4: MS 261 Chainsaw - $450,000, BR 600 Blower - $380,000, FS 91 Trimmer - $320,000",
        prompt_variant="test"
    )
    
    print(f"\n✅ Evaluator working! Test score: {test_eval.average_score:.2f}")
