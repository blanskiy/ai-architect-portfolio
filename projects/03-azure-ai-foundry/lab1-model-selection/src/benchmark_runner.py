"""
Lab 1: Model Selection - Benchmark Runner
Evaluates multiple LLM models on standardized tasks.

Usage:
    python benchmark_runner.py --models gpt-4o,gpt-4o-mini --tasks all
"""

import json
import time
import asyncio
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
import os
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()


@dataclass
class BenchmarkResult:
    """Result from a single benchmark run."""
    model: str
    task_type: str
    task_id: str
    prompt: str
    expected: str
    actual: str
    correct: bool
    latency_ms: float
    input_tokens: int
    output_tokens: int
    timestamp: str


@dataclass
class ModelMetrics:
    """Aggregated metrics for a model."""
    model: str
    total_tasks: int
    correct: int
    accuracy: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    total_input_tokens: int
    total_output_tokens: int
    estimated_cost: float


# Evaluation dataset - Sales Analytics tasks
EVAL_TASKS = [
    # SQL Generation tasks
    {
        "id": "sql_001",
        "type": "sql_generation",
        "prompt": "Write a SQL query to find the top 5 products by revenue in the last 30 days. Tables: products(id, name, category), sales(id, product_id, revenue, sale_date)",
        "expected_contains": ["SELECT", "ORDER BY", "DESC", "LIMIT 5", "revenue"],
        "criteria": "Must include SELECT, ORDER BY DESC, LIMIT, and reference revenue"
    },
    {
        "id": "sql_002", 
        "type": "sql_generation",
        "prompt": "Write a SQL query to calculate month-over-month revenue growth. Tables: sales(id, revenue, sale_date)",
        "expected_contains": ["LAG", "OVER", "PARTITION", "ORDER BY"],
        "criteria": "Must use window function for MoM calculation"
    },
    {
        "id": "sql_003",
        "type": "sql_generation",
        "prompt": "Write a SQL query to find customers who haven't purchased in 90 days. Tables: customers(id, name, email), orders(id, customer_id, order_date)",
        "expected_contains": ["LEFT JOIN", "WHERE", "NULL", "DATE"],
        "criteria": "Must identify inactive customers using date comparison"
    },
    
    # Data Analysis tasks
    {
        "id": "analysis_001",
        "type": "data_analysis",
        "prompt": "Given monthly revenue: Jan=$100K, Feb=$95K, Mar=$110K, Apr=$108K, May=$125K, Jun=$140K. Describe the trend and calculate average growth rate.",
        "expected_contains": ["upward", "growth", "increase", "%"],
        "criteria": "Must identify upward trend and provide growth calculation"
    },
    {
        "id": "analysis_002",
        "type": "data_analysis", 
        "prompt": "Product A: 1000 units, $50K revenue. Product B: 500 units, $75K revenue. Which product has better unit economics and why?",
        "expected_contains": ["Product B", "higher", "price", "margin", "$150", "$50"],
        "criteria": "Must identify Product B has higher revenue per unit ($150 vs $50)"
    },
    {
        "id": "analysis_003",
        "type": "data_analysis",
        "prompt": "Sales by region: North=$2M (was $1.8M), South=$1.5M (was $1.6M), East=$1M (was $0.9M), West=$0.8M (was $0.8M). Which region needs attention?",
        "expected_contains": ["South", "decline", "decrease", "-"],
        "criteria": "Must identify South as concerning (declining) region"
    },
    
    # Recommendation tasks
    {
        "id": "rec_001",
        "type": "recommendation",
        "prompt": "Q4 inventory: Chainsaws at 150% of target, Blowers at 60% of target, Trimmers at 100%. What inventory actions do you recommend?",
        "expected_contains": ["chainsaw", "reduce", "blower", "increase", "reorder"],
        "criteria": "Must recommend reducing chainsaw inventory and increasing blowers"
    },
    {
        "id": "rec_002",
        "type": "recommendation",
        "prompt": "New product launch options: A) Premium chainsaw ($800, 15% margin) for professionals, B) Budget trimmer ($150, 25% margin) for homeowners. Market is 70% homeowners. Which should we prioritize?",
        "expected_contains": ["trimmer", "homeowner", "market", "volume"],
        "criteria": "Should recommend trimmer based on market size alignment"
    },
    
    # Function calling tasks (simulated)
    {
        "id": "func_001",
        "type": "function_calling",
        "prompt": "I need to know our top products. What tool would you use: A) query_monthly_trends, B) query_product_performance, C) query_sales_data?",
        "expected_contains": ["B", "product_performance"],
        "criteria": "Must select query_product_performance"
    },
    {
        "id": "func_002",
        "type": "function_calling",
        "prompt": "For regional sales comparison over the last quarter, which tool: A) query_monthly_trends, B) query_product_performance, C) query_sales_data?",
        "expected_contains": ["C", "sales_data"],
        "criteria": "Must select query_sales_data for regional filtering"
    },
]


# Pricing per 1M tokens (as of Dec 2024)
MODEL_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-35-turbo": {"input": 0.50, "output": 1.50},
}


class ModelBenchmark:
    """Benchmarks LLM models on evaluation tasks."""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-12-01-preview"
        )
        self.results: list[BenchmarkResult] = []
    
    def evaluate_task(self, task: dict) -> BenchmarkResult:
        """Run a single evaluation task."""
        
        start_time = time.time()
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful data analyst. Be concise and accurate."},
                    {"role": "user", "content": task["prompt"]}
                ],
                max_tokens=500,
                temperature=0.1  # Low temp for consistency
            )
            
            latency_ms = (time.time() - start_time) * 1000
            actual = response.choices[0].message.content or ""
            
            # Check if response contains expected elements
            correct = all(
                keyword.lower() in actual.lower() 
                for keyword in task["expected_contains"]
            )
            
            return BenchmarkResult(
                model=self.model_name,
                task_type=task["type"],
                task_id=task["id"],
                prompt=task["prompt"],
                expected=str(task["expected_contains"]),
                actual=actual,
                correct=correct,
                latency_ms=latency_ms,
                input_tokens=response.usage.prompt_tokens if response.usage else 0,
                output_tokens=response.usage.completion_tokens if response.usage else 0,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            return BenchmarkResult(
                model=self.model_name,
                task_type=task["type"],
                task_id=task["id"],
                prompt=task["prompt"],
                expected=str(task["expected_contains"]),
                actual=f"ERROR: {str(e)}",
                correct=False,
                latency_ms=(time.time() - start_time) * 1000,
                input_tokens=0,
                output_tokens=0,
                timestamp=datetime.now().isoformat()
            )
    
    def run_all_tasks(self, tasks: list[dict] = None) -> list[BenchmarkResult]:
        """Run all evaluation tasks."""
        
        tasks = tasks or EVAL_TASKS
        print(f"\n🔄 Benchmarking {self.model_name} on {len(tasks)} tasks...")
        
        for i, task in enumerate(tasks, 1):
            print(f"   [{i}/{len(tasks)}] {task['id']}...", end=" ", flush=True)
            result = self.evaluate_task(task)
            self.results.append(result)
            status = "✅" if result.correct else "❌"
            print(f"{status} ({result.latency_ms:.0f}ms)")
        
        return self.results
    
    def get_metrics(self) -> ModelMetrics:
        """Calculate aggregate metrics from results."""
        
        if not self.results:
            raise ValueError("No results to calculate metrics from")
        
        latencies = [r.latency_ms for r in self.results]
        latencies_sorted = sorted(latencies)
        
        total_input = sum(r.input_tokens for r in self.results)
        total_output = sum(r.output_tokens for r in self.results)
        
        # Calculate cost
        pricing = MODEL_PRICING.get(self.model_name, {"input": 0, "output": 0})
        cost = (total_input * pricing["input"] / 1_000_000) + \
               (total_output * pricing["output"] / 1_000_000)
        
        return ModelMetrics(
            model=self.model_name,
            total_tasks=len(self.results),
            correct=sum(1 for r in self.results if r.correct),
            accuracy=sum(1 for r in self.results if r.correct) / len(self.results) * 100,
            avg_latency_ms=sum(latencies) / len(latencies),
            p50_latency_ms=latencies_sorted[len(latencies) // 2],
            p95_latency_ms=latencies_sorted[int(len(latencies) * 0.95)],
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            estimated_cost=cost
        )


def run_comparison(models: list[str]) -> dict:
    """Run benchmark comparison across multiple models."""
    
    print("="*60)
    print("🚀 MODEL SELECTION BENCHMARK")
    print("="*60)
    print(f"\nModels: {models}")
    print(f"Tasks: {len(EVAL_TASKS)}")
    
    all_results = {}
    all_metrics = {}
    
    for model in models:
        benchmark = ModelBenchmark(model)
        benchmark.run_all_tasks()
        
        metrics = benchmark.get_metrics()
        all_results[model] = [asdict(r) for r in benchmark.results]
        all_metrics[model] = asdict(metrics)
    
    # Print comparison
    print("\n" + "="*60)
    print("📊 RESULTS SUMMARY")
    print("="*60)
    
    print(f"\n{'Model':<20} {'Accuracy':<12} {'P50 (ms)':<12} {'P95 (ms)':<12} {'Cost ($)':<10}")
    print("-"*66)
    
    for model, metrics in all_metrics.items():
        print(f"{model:<20} {metrics['accuracy']:.1f}%{'':<7} "
              f"{metrics['p50_latency_ms']:.0f}{'':<8} "
              f"{metrics['p95_latency_ms']:.0f}{'':<8} "
              f"${metrics['estimated_cost']:.4f}")
    
    # Find winner
    best_model = max(all_metrics.items(), key=lambda x: x[1]['accuracy'])
    print(f"\n🏆 Best Accuracy: {best_model[0]} ({best_model[1]['accuracy']:.1f}%)")
    
    fastest_model = min(all_metrics.items(), key=lambda x: x[1]['p50_latency_ms'])
    print(f"⚡ Fastest (P50): {fastest_model[0]} ({fastest_model[1]['p50_latency_ms']:.0f}ms)")
    
    cheapest_model = min(all_metrics.items(), key=lambda x: x[1]['estimated_cost'])
    print(f"💰 Most Cost-Effective: {cheapest_model[0]} (${cheapest_model[1]['estimated_cost']:.4f})")
    
    return {
        "results": all_results,
        "metrics": all_metrics,
        "timestamp": datetime.now().isoformat()
    }


def save_results(data: dict, output_dir: str = "results"):
    """Save benchmark results to JSON."""
    
    Path(output_dir).mkdir(exist_ok=True)
    
    output_file = Path(output_dir) / "benchmark_results.json"
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n💾 Results saved: {output_file}")


if __name__ == "__main__":
    import sys
    
    # Default models to compare
    models = ["gpt-4o", "gpt-4o-mini"]
    
    # Override from command line
    if len(sys.argv) > 1:
        models = sys.argv[1].split(",")
    
    # Check for API credentials
    if not os.getenv("AZURE_OPENAI_ENDPOINT"):
        print("❌ AZURE_OPENAI_ENDPOINT not set")
        print("   Set environment variables or create .env file")
        sys.exit(1)
    
    # Run comparison
    results = run_comparison(models)
    save_results(results)
    
    print("\n✅ Benchmark complete!")
