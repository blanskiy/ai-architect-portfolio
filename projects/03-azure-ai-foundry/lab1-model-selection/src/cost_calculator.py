"""
Lab 1: Model Selection - Cost Calculator
Estimates and compares costs for different LLM models at scale.

Usage:
    python cost_calculator.py --tokens 10000000 --ratio 2:1
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ModelPricing:
    """Pricing information for a model (per 1M tokens)."""
    name: str
    input_price: float
    output_price: float
    context_window: int
    provider: str
    tier: str  # "premium", "standard", "budget"


# Current pricing as of December 2024
MODELS = [
    # Azure OpenAI
    ModelPricing("gpt-4o", 2.50, 10.00, 128000, "Azure OpenAI", "premium"),
    ModelPricing("gpt-4o-mini", 0.15, 0.60, 128000, "Azure OpenAI", "standard"),
    ModelPricing("gpt-4-turbo", 10.00, 30.00, 128000, "Azure OpenAI", "premium"),
    ModelPricing("gpt-35-turbo", 0.50, 1.50, 16385, "Azure OpenAI", "budget"),
    
    # Anthropic
    ModelPricing("claude-3.5-sonnet", 3.00, 15.00, 200000, "Anthropic", "premium"),
    ModelPricing("claude-3-haiku", 0.25, 1.25, 200000, "Anthropic", "budget"),
    
    # Open Source (Azure ML / Inference Endpoints)
    ModelPricing("llama-3.1-70b", 0.90, 0.90, 128000, "Azure ML", "standard"),
    ModelPricing("llama-3.1-8b", 0.20, 0.20, 128000, "Azure ML", "budget"),
    ModelPricing("mistral-large", 2.00, 6.00, 128000, "Azure ML", "standard"),
]


def calculate_monthly_cost(
    model: ModelPricing,
    monthly_input_tokens: int,
    monthly_output_tokens: int
) -> dict:
    """Calculate monthly cost for a model."""
    
    input_cost = (monthly_input_tokens / 1_000_000) * model.input_price
    output_cost = (monthly_output_tokens / 1_000_000) * model.output_price
    total_cost = input_cost + output_cost
    
    return {
        "model": model.name,
        "provider": model.provider,
        "tier": model.tier,
        "input_tokens": monthly_input_tokens,
        "output_tokens": monthly_output_tokens,
        "input_cost": round(input_cost, 2),
        "output_cost": round(output_cost, 2),
        "total_cost": round(total_cost, 2),
        "annual_cost": round(total_cost * 12, 2)
    }


def compare_models(
    monthly_total_tokens: int,
    input_output_ratio: float = 2.0,  # 2:1 means 2 input tokens per 1 output
    models: Optional[list[ModelPricing]] = None
) -> list[dict]:
    """Compare costs across models for given token volume."""
    
    models = models or MODELS
    
    # Calculate token split based on ratio
    monthly_output_tokens = int(monthly_total_tokens / (input_output_ratio + 1))
    monthly_input_tokens = monthly_total_tokens - monthly_output_tokens
    
    results = []
    for model in models:
        cost = calculate_monthly_cost(model, monthly_input_tokens, monthly_output_tokens)
        results.append(cost)
    
    # Sort by total cost
    results.sort(key=lambda x: x["total_cost"])
    
    return results


def print_comparison_table(results: list[dict]):
    """Print formatted comparison table."""
    
    print(f"\n{'Model':<20} {'Provider':<15} {'Tier':<10} {'Monthly':<12} {'Annual':<12}")
    print("-" * 69)
    
    for r in results:
        print(f"{r['model']:<20} {r['provider']:<15} {r['tier']:<10} "
              f"${r['total_cost']:>9,.2f} ${r['annual_cost']:>9,.2f}")


def scenario_analysis():
    """Run cost analysis for different usage scenarios."""
    
    scenarios = [
        {"name": "Startup MVP", "tokens": 1_000_000, "description": "Light usage, testing"},
        {"name": "Growth Stage", "tokens": 10_000_000, "description": "Production, moderate load"},
        {"name": "Enterprise", "tokens": 100_000_000, "description": "High volume, multiple apps"},
        {"name": "Platform Scale", "tokens": 1_000_000_000, "description": "SaaS product, millions of users"},
    ]
    
    print("=" * 70)
    print("💰 MODEL COST ANALYSIS - SCENARIO COMPARISON")
    print("=" * 70)
    
    for scenario in scenarios:
        print(f"\n\n📊 Scenario: {scenario['name']}")
        print(f"   {scenario['description']}")
        print(f"   Monthly tokens: {scenario['tokens']:,}")
        
        results = compare_models(scenario['tokens'])
        print_comparison_table(results[:5])  # Top 5 cheapest
        
        # Calculate potential savings
        cheapest = results[0]
        most_expensive = results[-1]
        savings = most_expensive['annual_cost'] - cheapest['annual_cost']
        
        print(f"\n   💡 Switching from {most_expensive['model']} to {cheapest['model']}:")
        print(f"      Annual savings: ${savings:,.2f}")


def routing_cost_analysis():
    """Analyze costs for intelligent routing architectures."""
    
    print("\n" + "=" * 70)
    print("🔀 INTELLIGENT ROUTING COST ANALYSIS")
    print("=" * 70)
    
    monthly_tokens = 50_000_000  # 50M tokens/month
    
    # Scenario 1: All GPT-4o
    all_premium = calculate_monthly_cost(
        MODELS[0],  # gpt-4o
        int(monthly_tokens * 0.67),
        int(monthly_tokens * 0.33)
    )
    
    # Scenario 2: All GPT-4o-mini
    all_budget = calculate_monthly_cost(
        MODELS[1],  # gpt-4o-mini
        int(monthly_tokens * 0.67),
        int(monthly_tokens * 0.33)
    )
    
    # Scenario 3: 90% mini, 10% full (routing)
    gpt4o_tokens = int(monthly_tokens * 0.10)
    mini_tokens = int(monthly_tokens * 0.90)
    
    premium_cost = calculate_monthly_cost(
        MODELS[0],
        int(gpt4o_tokens * 0.67),
        int(gpt4o_tokens * 0.33)
    )
    budget_cost = calculate_monthly_cost(
        MODELS[1],
        int(mini_tokens * 0.67),
        int(mini_tokens * 0.33)
    )
    
    routed_total = premium_cost['total_cost'] + budget_cost['total_cost']
    
    print(f"\n📈 Monthly Volume: {monthly_tokens:,} tokens")
    print(f"\n{'Strategy':<35} {'Monthly Cost':<15} {'Annual Cost':<15}")
    print("-" * 65)
    print(f"{'100% GPT-4o (Premium)':<35} ${all_premium['total_cost']:>12,.2f} ${all_premium['annual_cost']:>12,.2f}")
    print(f"{'100% GPT-4o-mini (Budget)':<35} ${all_budget['total_cost']:>12,.2f} ${all_budget['annual_cost']:>12,.2f}")
    print(f"{'90% mini + 10% GPT-4o (Routed)':<35} ${routed_total:>12,.2f} ${routed_total * 12:>12,.2f}")
    
    savings_vs_premium = (all_premium['annual_cost'] - routed_total * 12)
    quality_cost = (routed_total * 12 - all_budget['annual_cost'])
    
    print(f"\n💡 Routing Strategy Insights:")
    print(f"   • Saves ${savings_vs_premium:,.2f}/year vs all-premium")
    print(f"   • Costs ${quality_cost:,.2f}/year more than all-budget")
    print(f"   • Quality premium: {(quality_cost / all_budget['annual_cost']) * 100:.1f}% more for 10% complex queries")


if __name__ == "__main__":
    scenario_analysis()
    routing_cost_analysis()
    
    print("\n\n✅ Cost analysis complete!")
    print("   Use these insights for model selection decisions.")
