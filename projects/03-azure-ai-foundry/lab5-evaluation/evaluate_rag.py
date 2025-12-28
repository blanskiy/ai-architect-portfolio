"""
Lab 5: RAG Evaluation with Azure AI Foundry
Evaluates response quality using Groundedness, Relevance, Coherence, Fluency
"""

import os
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from azure.ai.evaluation import (
    GroundednessEvaluator,
    RelevanceEvaluator,
    CoherenceEvaluator,
    FluencyEvaluator,
)
from openai import AzureOpenAI

load_dotenv()

# Configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://blans-mjiyrqgp-westus.openai.azure.com/")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")  # Add this to .env
MODEL_DEPLOYMENT = "gpt-4o"
JUDGE_MODEL = "gpt-4o"


def get_azure_openai_client():
    """Create Azure OpenAI client with API key"""
    return AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version="2024-10-21"
    )


def load_evaluation_data(filepath: str) -> list[dict]:
    """Load JSONL evaluation dataset"""
    data = []
    with open(filepath, 'r') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    print(f"Loaded {len(data)} evaluation samples")
    return data


def generate_rag_response(client: AzureOpenAI, question: str, context: str) -> str:
    """Generate response using RAG pattern"""
    
    system_prompt = """You are a STIHL sales analytics assistant. 
    Answer questions based on the provided context from our sales data.
    Be specific with numbers and trends when available.
    If the context doesn't contain enough information, say so."""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"}
    ]
    
    response = client.chat.completions.create(
        model=MODEL_DEPLOYMENT,
        messages=messages,
        temperature=0.3,
        max_tokens=500
    )
    
    return response.choices[0].message.content


def run_evaluation():
    """Run full evaluation pipeline"""
    
    print("=" * 60)
    print("Lab 5: RAG Evaluation with Azure AI Foundry")
    print("=" * 60)
    
    # Check for API key
    if not AZURE_OPENAI_API_KEY:
        print("ERROR: AZURE_OPENAI_API_KEY not found in .env")
        print("Get it from: Azure Portal → Azure OpenAI → Keys and Endpoint")
        return
    
    # Initialize client
    client = get_azure_openai_client()
    print("✓ Azure OpenAI client initialized")
    
    # Load evaluation data
    eval_data = load_evaluation_data("data/eval_dataset_v2.jsonl")
    
    # Generate responses for each question
    print("\nGenerating RAG responses...")
    results = []
    
    for i, sample in enumerate(eval_data, 1):
        print(f"  [{i}/{len(eval_data)}] {sample['question'][:50]}...")
        
        response = generate_rag_response(
            client, 
            sample['question'], 
            sample['context']
        )
        
        results.append({
            "question": sample['question'],
            "context": sample['context'],
            "ground_truth": sample['ground_truth'],
            "response": response
        })
    
    print(f"✓ Generated {len(results)} responses")
    
    # Initialize evaluators with API key auth
    print("\nInitializing evaluators...")
    
    model_config = {
        "azure_endpoint": AZURE_OPENAI_ENDPOINT,
        "azure_deployment": JUDGE_MODEL,
        "api_version": "2024-10-21",
        "api_key": AZURE_OPENAI_API_KEY,
    }
    
    # Create evaluators
    groundedness = GroundednessEvaluator(model_config=model_config)
    relevance = RelevanceEvaluator(model_config=model_config)
    coherence = CoherenceEvaluator(model_config=model_config)
    fluency = FluencyEvaluator(model_config=model_config)
    
    print("✓ Evaluators initialized (Groundedness, Relevance, Coherence, Fluency)")
    
    # Run evaluations
    print("\nEvaluating responses with LLM-as-judge...")
    evaluation_results = []
    
    for i, result in enumerate(results, 1):
        print(f"  [{i}/{len(results)}] Evaluating...")
        
        scores = {
            "groundedness": None,
            "relevance": None,
            "coherence": None,
            "fluency": None
        }
        
        try:
            # Groundedness: needs response, context, query
            g_result = groundedness(
                response=result['response'],
                context=result['context'],
                query=result['question']
            )
            scores["groundedness"] = g_result.get('groundedness', g_result.get('gpt_groundedness'))
        except Exception as e:
            print(f"    Groundedness error: {str(e)[:50]}")
        
        try:
            # Relevance: needs response, query
            r_result = relevance(
                response=result['response'],
                query=result['question']
            )
            scores["relevance"] = r_result.get('relevance', r_result.get('gpt_relevance'))
        except Exception as e:
            print(f"    Relevance error: {str(e)[:50]}")
        
        try:
            # Coherence: needs response, query
            c_result = coherence(
                response=result['response'],
                query=result['question']
            )
            scores["coherence"] = c_result.get('coherence', c_result.get('gpt_coherence'))
        except Exception as e:
            print(f"    Coherence error: {str(e)[:50]}")
        
        try:
            # Fluency: needs response, query
            f_result = fluency(
                response=result['response'],
                query=result['question']
            )
            scores["fluency"] = f_result.get('fluency', f_result.get('gpt_fluency'))
        except Exception as e:
            print(f"    Fluency error: {str(e)[:50]}")
        
        eval_result = {**result, **scores}
        evaluation_results.append(eval_result)
        
        # Print individual scores
        valid_scores = [f"{k}={v}" for k, v in scores.items() if v is not None]
        if valid_scores:
            print(f"    Scores: {', '.join(valid_scores)}")
    
    # Calculate aggregate metrics
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    
    metrics = ['groundedness', 'relevance', 'coherence', 'fluency']
    aggregates = {}
    
    for metric in metrics:
        scores = [r[metric] for r in evaluation_results if r[metric] is not None]
        if scores:
            avg = sum(scores) / len(scores)
            aggregates[metric] = {
                'average': round(avg, 2),
                'min': min(scores),
                'max': max(scores),
                'count': len(scores)
            }
            print(f"\n{metric.upper()}:")
            print(f"  Average: {avg:.2f}/5")
            print(f"  Range: {min(scores):.1f} - {max(scores):.1f}")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"results/evaluation_{timestamp}.json"
    
    output = {
        "timestamp": timestamp,
        "model": MODEL_DEPLOYMENT,
        "judge_model": JUDGE_MODEL,
        "num_samples": len(evaluation_results),
        "aggregate_metrics": aggregates,
        "detailed_results": evaluation_results
    }
    
    Path("results").mkdir(exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✓ Results saved to: {output_file}")
    
    # Print summary table
    if aggregates:
        print("\n" + "-" * 60)
        print("SUMMARY: Quality Scores (1-5 scale)")
        print("-" * 60)
        print(f"{'Metric':<15} {'Score':<10} {'Status'}")
        print("-" * 60)
        
        for metric, data in aggregates.items():
            score = data['average']
            status = "✓ Good" if score >= 4 else ("⚠ Needs Work" if score >= 3 else "✗ Poor")
            print(f"{metric:<15} {score:<10.2f} {status}")
        
        overall = sum(d['average'] for d in aggregates.values()) / len(aggregates)
        print("-" * 60)
        print(f"{'OVERALL':<15} {overall:<10.2f}")
    else:
        print("\n⚠ No metrics were successfully calculated")
    
    return evaluation_results


if __name__ == "__main__":
    run_evaluation()
