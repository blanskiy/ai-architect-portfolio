"""
LLM Inference Benchmark Script

Compares inference performance across different LLM serving options:
- Azure OpenAI (GPT-4o, GPT-4o-mini)
- Ollama (local Llama models with various quantizations)
- Databricks Foundation Models

Usage:
    python benchmark_inference.py --all
    python benchmark_inference.py --engine ollama --model llama3.1:8b
    python benchmark_inference.py --engine azure --model gpt-4o-mini
"""

import argparse
import json
import os
import time
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime
import statistics

# Optional imports with graceful fallback
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("⚠ Ollama not installed. Run: pip install ollama")

try:
    from openai import AzureOpenAI
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    print("⚠ OpenAI not installed. Run: pip install openai")

try:
    from mlflow.deployments import get_deploy_client
    DATABRICKS_AVAILABLE = True
except ImportError:
    DATABRICKS_AVAILABLE = False
    print("⚠ MLflow not installed for Databricks. Run: pip install mlflow")


@dataclass
class BenchmarkResult:
    """Single benchmark run result"""
    engine: str
    model: str
    quantization: Optional[str]
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    time_to_first_token_ms: float
    total_latency_ms: float
    tokens_per_second: float
    cost_per_1k_tokens: float
    timestamp: str


@dataclass
class BenchmarkSummary:
    """Summary statistics for multiple runs"""
    engine: str
    model: str
    quantization: Optional[str]
    runs: int
    avg_ttft_ms: float
    avg_latency_ms: float
    avg_tps: float
    std_tps: float
    p50_latency_ms: float
    p95_latency_ms: float
    cost_per_1k_tokens: float


# Test prompts of varying complexity
TEST_PROMPTS = [
    {
        "name": "simple",
        "prompt": "What is machine learning in one sentence?",
        "expected_tokens": 30
    },
    {
        "name": "medium",
        "prompt": "Explain the difference between supervised and unsupervised learning. Include examples.",
        "expected_tokens": 150
    },
    {
        "name": "complex",
        "prompt": """You are an AI architect. Design a recommendation system for an e-commerce platform 
        with 10 million users. Include: data pipeline, model architecture, serving infrastructure, 
        and monitoring. Be specific about technologies.""",
        "expected_tokens": 500
    }
]

# Cost per 1K tokens (as of Dec 2024)
COSTS = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "llama3.1:8b": {"input": 0, "output": 0},  # Local, free
    "llama3.1:8b-instruct-q4_0": {"input": 0, "output": 0},
    "llama3.1:8b-instruct-q8_0": {"input": 0, "output": 0},
    "databricks-meta-llama-3-3-70b-instruct": {"input": 0.001, "output": 0.002},
}


class OllamaEngine:
    """Ollama local inference engine"""
    
    def __init__(self, model: str = "llama3.1:8b"):
        if not OLLAMA_AVAILABLE:
            raise RuntimeError("Ollama not installed")
        self.model = model
        self.client = ollama.Client()
        
    def generate(self, prompt: str, max_tokens: int = 500) -> BenchmarkResult:
        start_time = time.perf_counter()
        first_token_time = None
        full_response = ""
        
        # Stream to measure time to first token
        stream = self.client.generate(
            model=self.model,
            prompt=prompt,
            stream=True,
            options={"num_predict": max_tokens}
        )
        
        for chunk in stream:
            if first_token_time is None:
                first_token_time = time.perf_counter()
            full_response += chunk.get("response", "")
        
        end_time = time.perf_counter()
        
        # Calculate metrics
        total_latency_ms = (end_time - start_time) * 1000
        ttft_ms = (first_token_time - start_time) * 1000 if first_token_time else total_latency_ms
        
        # Estimate tokens (rough: 4 chars per token)
        prompt_tokens = len(prompt) // 4
        completion_tokens = len(full_response) // 4
        total_tokens = prompt_tokens + completion_tokens
        
        generation_time = end_time - (first_token_time or start_time)
        tps = completion_tokens / generation_time if generation_time > 0 else 0
        
        # Determine quantization from model name
        quant = None
        if "q4" in self.model:
            quant = "Q4"
        elif "q8" in self.model:
            quant = "Q8"
        elif "q5" in self.model:
            quant = "Q5"
        
        cost = COSTS.get(self.model, {"input": 0, "output": 0})
        cost_per_1k = (cost["input"] * prompt_tokens + cost["output"] * completion_tokens) / 1000
        
        return BenchmarkResult(
            engine="ollama",
            model=self.model,
            quantization=quant,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            time_to_first_token_ms=ttft_ms,
            total_latency_ms=total_latency_ms,
            tokens_per_second=tps,
            cost_per_1k_tokens=cost_per_1k,
            timestamp=datetime.now().isoformat()
        )


class AzureOpenAIEngine:
    """Azure OpenAI inference engine"""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        if not AZURE_AVAILABLE:
            raise RuntimeError("OpenAI SDK not installed")
        
        self.model = model
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-15-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
    def generate(self, prompt: str, max_tokens: int = 500) -> BenchmarkResult:
        start_time = time.perf_counter()
        first_token_time = None
        
        # Stream to measure time to first token
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            stream=True
        )
        
        full_response = ""
        for chunk in stream:
            if first_token_time is None and chunk.choices and chunk.choices[0].delta.content:
                first_token_time = time.perf_counter()
            if chunk.choices and chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
        
        end_time = time.perf_counter()
        
        # Calculate metrics
        total_latency_ms = (end_time - start_time) * 1000
        ttft_ms = (first_token_time - start_time) * 1000 if first_token_time else total_latency_ms
        
        # Use tiktoken for accurate token count (fallback to estimate)
        try:
            import tiktoken
            enc = tiktoken.encoding_for_model(self.model)
            prompt_tokens = len(enc.encode(prompt))
            completion_tokens = len(enc.encode(full_response))
        except:
            prompt_tokens = len(prompt) // 4
            completion_tokens = len(full_response) // 4
        
        total_tokens = prompt_tokens + completion_tokens
        
        generation_time = end_time - (first_token_time or start_time)
        tps = completion_tokens / generation_time if generation_time > 0 else 0
        
        cost = COSTS.get(self.model, {"input": 0.001, "output": 0.002})
        cost_per_1k = (cost["input"] * prompt_tokens + cost["output"] * completion_tokens) / 1000
        
        return BenchmarkResult(
            engine="azure_openai",
            model=self.model,
            quantization=None,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            time_to_first_token_ms=ttft_ms,
            total_latency_ms=total_latency_ms,
            tokens_per_second=tps,
            cost_per_1k_tokens=cost_per_1k,
            timestamp=datetime.now().isoformat()
        )


class DatabricksEngine:
    """Databricks Foundation Model inference engine"""
    
    def __init__(self, model: str = "databricks-meta-llama-3-3-70b-instruct"):
        if not DATABRICKS_AVAILABLE:
            raise RuntimeError("MLflow not installed for Databricks")
        
        self.model = model
        self.client = get_deploy_client("databricks")
        
    def generate(self, prompt: str, max_tokens: int = 500) -> BenchmarkResult:
        start_time = time.perf_counter()
        
        response = self.client.predict(
            endpoint=self.model,
            inputs={
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            }
        )
        
        end_time = time.perf_counter()
        
        # Extract response
        full_response = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = response.get("usage", {})
        
        prompt_tokens = usage.get("prompt_tokens", len(prompt) // 4)
        completion_tokens = usage.get("completion_tokens", len(full_response) // 4)
        total_tokens = prompt_tokens + completion_tokens
        
        total_latency_ms = (end_time - start_time) * 1000
        ttft_ms = total_latency_ms * 0.3  # Estimate TTFT as 30% of total
        
        generation_time = total_latency_ms / 1000 * 0.7  # Generation is ~70% of time
        tps = completion_tokens / generation_time if generation_time > 0 else 0
        
        cost = COSTS.get(self.model, {"input": 0.001, "output": 0.002})
        cost_per_1k = (cost["input"] * prompt_tokens + cost["output"] * completion_tokens) / 1000
        
        return BenchmarkResult(
            engine="databricks",
            model=self.model,
            quantization=None,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            time_to_first_token_ms=ttft_ms,
            total_latency_ms=total_latency_ms,
            tokens_per_second=tps,
            cost_per_1k_tokens=cost_per_1k,
            timestamp=datetime.now().isoformat()
        )


def run_benchmark(engine, prompts: List[dict], runs_per_prompt: int = 3) -> List[BenchmarkResult]:
    """Run benchmark across all prompts"""
    results = []
    
    for prompt_info in prompts:
        print(f"\n  Testing: {prompt_info['name']} prompt...")
        
        for run in range(runs_per_prompt):
            try:
                result = engine.generate(
                    prompt_info["prompt"],
                    max_tokens=prompt_info["expected_tokens"]
                )
                results.append(result)
                print(f"    Run {run+1}: {result.tokens_per_second:.1f} TPS, {result.total_latency_ms:.0f}ms latency")
            except Exception as e:
                print(f"    Run {run+1}: ERROR - {e}")
    
    return results


def calculate_summary(results: List[BenchmarkResult]) -> BenchmarkSummary:
    """Calculate summary statistics"""
    if not results:
        return None
    
    latencies = [r.total_latency_ms for r in results]
    tps_values = [r.tokens_per_second for r in results]
    ttft_values = [r.time_to_first_token_ms for r in results]
    
    return BenchmarkSummary(
        engine=results[0].engine,
        model=results[0].model,
        quantization=results[0].quantization,
        runs=len(results),
        avg_ttft_ms=statistics.mean(ttft_values),
        avg_latency_ms=statistics.mean(latencies),
        avg_tps=statistics.mean(tps_values),
        std_tps=statistics.stdev(tps_values) if len(tps_values) > 1 else 0,
        p50_latency_ms=statistics.median(latencies),
        p95_latency_ms=sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0],
        cost_per_1k_tokens=results[0].cost_per_1k_tokens
    )


def print_summary(summaries: List[BenchmarkSummary]):
    """Print comparison table"""
    print("\n" + "=" * 100)
    print("BENCHMARK SUMMARY")
    print("=" * 100)
    print(f"{'Engine':<15} {'Model':<35} {'Quant':<6} {'Avg TPS':<10} {'TTFT (ms)':<12} {'P95 Lat (ms)':<14} {'Cost/1K':<10}")
    print("-" * 100)
    
    for s in summaries:
        print(f"{s.engine:<15} {s.model:<35} {s.quantization or 'N/A':<6} {s.avg_tps:<10.1f} {s.avg_ttft_ms:<12.0f} {s.p95_latency_ms:<14.0f} ${s.cost_per_1k_tokens:<9.5f}")
    
    print("=" * 100)


def main():
    parser = argparse.ArgumentParser(description="LLM Inference Benchmark")
    parser.add_argument("--engine", choices=["ollama", "azure", "databricks", "all"], default="all")
    parser.add_argument("--model", type=str, help="Specific model to test")
    parser.add_argument("--runs", type=int, default=3, help="Runs per prompt")
    parser.add_argument("--output", type=str, default="results/benchmark_results.json")
    args = parser.parse_args()
    
    all_results = []
    summaries = []
    
    # Define models to test
    engines_to_test = []
    
    if args.engine in ["ollama", "all"] and OLLAMA_AVAILABLE:
        ollama_models = ["llama3.1:8b"] if not args.model else [args.model]
        for model in ollama_models:
            engines_to_test.append(("ollama", model, OllamaEngine))
    
    if args.engine in ["azure", "all"] and AZURE_AVAILABLE:
        azure_models = ["gpt-4o-mini"] if not args.model else [args.model]
        for model in azure_models:
            engines_to_test.append(("azure", model, AzureOpenAIEngine))
    
    if args.engine in ["databricks", "all"] and DATABRICKS_AVAILABLE:
        db_models = ["databricks-meta-llama-3-3-70b-instruct"] if not args.model else [args.model]
        for model in db_models:
            engines_to_test.append(("databricks", model, DatabricksEngine))
    
    # Run benchmarks
    for engine_name, model, engine_class in engines_to_test:
        print(f"\n{'='*60}")
        print(f"Testing: {engine_name} / {model}")
        print(f"{'='*60}")
        
        try:
            engine = engine_class(model)
            results = run_benchmark(engine, TEST_PROMPTS, runs_per_prompt=args.runs)
            all_results.extend(results)
            
            summary = calculate_summary(results)
            if summary:
                summaries.append(summary)
        except Exception as e:
            print(f"ERROR: {e}")
    
    # Print and save results
    print_summary(summaries)
    
    # Save to JSON
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "summaries": [asdict(s) for s in summaries],
        "raw_results": [asdict(r) for r in all_results]
    }
    
    with open(args.output, "w") as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
