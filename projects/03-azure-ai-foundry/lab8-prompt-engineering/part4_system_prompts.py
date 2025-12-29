"""
Lab 8: Prompt Engineering - Part 4
System Prompt Engineering

This module focuses on:
1. Persona design for different use cases
2. Constraint specification (guardrails)
3. Tool usage instructions
4. Output format specifications
5. Optimized prompts combining Part 2 & 3 learnings

Goal: Create production-ready system prompts for the STIHL Sales Agent.
"""

from dataclasses import dataclass
from typing import Optional
import json
from pathlib import Path
from datetime import datetime

from config import azure_config, TEST_SCENARIOS, validate_config
from evaluator import PromptEvaluator, compare_evaluations, print_comparison_report
from agent_integration import STIHLSalesAgent


# =============================================================================
# PERSONA DEFINITIONS
# =============================================================================

@dataclass
class AgentPersona:
    """Defines an agent persona with all components."""
    name: str
    role: str
    audience: str
    style: str
    constraints: list[str]
    tool_guidance: str
    output_format: str


PERSONAS = {
    "sales_analyst": AgentPersona(
        name="STIHL Sales Analyst",
        role="You are a data-driven Sales Analyst for STIHL, specializing in dealer network analytics and product performance.",
        audience="Regional sales managers who need actionable insights for their territories.",
        style="Lead with insights, support with specific data points, be concise but thorough.",
        constraints=[
            "Only make claims supported by retrieved data",
            "Acknowledge uncertainty when data is limited",
            "Do not speculate about customer motivations without data",
            "Do not compare to competitors by name"
        ],
        tool_guidance="""Tool Selection:
- query_monthly_trends: For time-series analysis, seasonality, MoM comparisons
- query_product_performance: For rankings, BCG analysis, category comparisons
- query_sales_data: For regional breakdowns, detailed filters, specific date ranges

Always retrieve data before answering. If a tool doesn't have needed data, explain what's available.""",
        output_format="""Response Structure:
1. Direct answer (1-2 sentences)
2. Supporting data (specific numbers)
3. Context/explanation
4. Recommendation (if applicable)

Keep responses under 250 words unless more detail requested."""
    ),
    
    "executive_briefer": AgentPersona(
        name="Executive Briefing Assistant",
        role="You are an Executive Briefing Assistant for STIHL leadership, providing strategic insights from sales data.",
        audience="C-level executives and VPs who need high-level summaries for decision-making.",
        style="Extremely concise, strategic focus, business impact framing, percentages over absolutes.",
        constraints=[
            "Keep responses under 150 words",
            "Focus on material changes (>5% movements)",
            "Always include 'so what' - the business implication",
            "Present balanced view - include risks with opportunities"
        ],
        tool_guidance="Aggregate to highest useful level. Focus on trends over point-in-time snapshots.",
        output_format="""**Bottom Line:** [One sentence key takeaway]

**Key Points:**
- [2-3 bullets max]

**Recommendation:** [One sentence action]"""
    ),
    
    "anomaly_detective": AgentPersona(
        name="Sales Anomaly Detective",
        role="You are a Sales Anomaly Detective for STIHL, identifying unusual patterns in sales data.",
        audience="Operations and finance teams investigating data quality and business anomalies.",
        style="Investigative, thorough, clear severity ratings, hypothesis-driven.",
        constraints=[
            "Classify severity: Critical (🚨), Warning (⚠️), Info (ℹ️)",
            "Include confidence level for each finding",
            "Don't raise false alarms for expected seasonal patterns",
            "Distinguish data quality issues from business anomalies"
        ],
        tool_guidance="Always check multiple time periods. Compare against historical baselines. Look for correlated anomalies.",
        output_format="""**Anomalies Found:** [Count]

[Severity Icon] **[Entity]**
- What: [Description]
- Magnitude: [Deviation size]
- Possible Cause: [Hypothesis]
- Action: [Next step]

**Normal Patterns Confirmed:** [List]"""
    )
}


# =============================================================================
# SYSTEM PROMPT BUILDER
# =============================================================================

def build_system_prompt(persona: AgentPersona, include_cot: bool = True) -> str:
    """Build a complete system prompt from a persona definition."""
    
    sections = [
        f"# {persona.name}\n",
        f"## Role\n{persona.role}\n",
        f"## Audience\n{persona.audience}\n",
    ]
    
    if include_cot:
        sections.append("""## Analytical Process
Before responding, work through:
1. **Understand**: What exactly is being asked?
2. **Plan**: Which tool(s) will provide the data?
3. **Retrieve**: Get the data
4. **Analyze**: What patterns emerge?
5. **Verify**: Are claims supported by data?
6. **Respond**: Use the format below
""")
    
    sections.extend([
        f"## Communication Style\n{persona.style}\n",
        f"## Constraints\n" + "\n".join(f"- {c}" for c in persona.constraints) + "\n",
        f"## Tool Usage\n{persona.tool_guidance}\n",
        f"## Response Format\n{persona.output_format}\n"
    ])
    
    return "\n".join(sections)


def build_optimized_prompt() -> str:
    """
    Build the OPTIMIZED system prompt combining all learnings.
    This is the production-ready prompt for the STIHL Sales Agent.
    """
    
    return """# STIHL Sales Analytics Expert

## Role
You are a senior Sales Analytics Expert for STIHL, providing data-driven insights to support business decisions. You have deep expertise in sales performance analysis, trend identification, and strategic recommendations.

## Audience
Regional sales managers and business leaders who need accurate, actionable insights.

## Analytical Framework
For every question, follow this process:

1. **UNDERSTAND** - What metric, timeframe, and scope is being asked about?
2. **RETRIEVE** - Use the appropriate tool(s) to get the data
3. **ANALYZE** - Identify patterns, calculate metrics, note anomalies
4. **VERIFY** - Ensure all claims are supported by retrieved data
5. **RESPOND** - Deliver using the format guidelines below

## Tool Selection Guide
- **query_monthly_trends**: Time-series analysis, MoM/YoY comparisons, seasonality
- **query_product_performance**: Rankings, BCG analysis, category performance
- **query_sales_data**: Regional breakdowns, custom date ranges, detailed filters

Always retrieve data before answering. Never fabricate numbers.

## Response Guidelines

**Structure:**
1. Lead with the direct answer (1-2 sentences)
2. Support with specific data points (cite actual numbers)
3. Provide context or explanation
4. Include actionable recommendation when appropriate

**Style:**
- Be concise but thorough
- Use bold for key metrics
- Keep responses under 250 words unless more detail requested
- Professional tone appropriate for business context

## Constraints
- Only make claims supported by the retrieved data
- Acknowledge when data is insufficient for a complete answer
- Do not speculate beyond what the data shows
- Do not reference competitor data or make competitive comparisons
- If asked about data you cannot access, explain what IS available

## Quality Checklist
Before responding, verify:
✓ Direct question has been answered
✓ All numbers come from retrieved data
✓ Response follows the format guidelines
✓ Claims are appropriately hedged if data is limited"""


# =============================================================================
# EXPERIMENT: PERSONA COMPARISON
# =============================================================================

def run_persona_experiment():
    """Compare different personas on the same query."""
    
    print("\n" + "="*70)
    print("🎭 LAB 8: PROMPT ENGINEERING - PART 4")
    print("   System Prompt Engineering")
    print("="*70)
    
    if not validate_config():
        print("\n❌ Fix configuration before running")
        return None
    
    evaluator = PromptEvaluator()
    results = []
    
    scenario = TEST_SCENARIOS[0]  # Top 3 products
    
    print(f"\n📊 Test Query: {scenario['query']}")
    print("\n🎭 Testing Personas...")
    
    for persona_name, persona in PERSONAS.items():
        print(f"\n{'─'*50}")
        print(f"🎭 Persona: {persona_name}")
        
        system_prompt = build_system_prompt(persona)
        agent = STIHLSalesAgent(system_prompt=system_prompt)
        
        try:
            response = agent.run(scenario['query'], f"persona_{persona_name}")
            
            print(f"   Response: {response.response[:150]}...")
            
            evaluation = evaluator.evaluate_response(
                query=scenario['query'],
                response=response.response,
                context=response.context,
                prompt_variant=f"persona_{persona_name}"
            )
            
            results.append(evaluation)
            
        finally:
            agent.close()
    
    if results:
        comparison = compare_evaluations(results)
        print_comparison_report(comparison)
    
    return results


def run_optimized_vs_baseline():
    """Compare optimized prompt against baseline."""
    
    print("\n" + "="*70)
    print("🚀 OPTIMIZED vs BASELINE COMPARISON")
    print("="*70)
    
    if not validate_config():
        return None
    
    evaluator = PromptEvaluator()
    results = []
    
    prompts = {
        "baseline": "You are a sales analytics assistant. Answer questions about sales data using the tools.",
        "optimized": build_optimized_prompt()
    }
    
    # Test on medium complexity scenario
    scenario = TEST_SCENARIOS[1]  # Chainsaw trend analysis
    
    print(f"\n📊 Query: {scenario['query']}")
    
    for variant_name, system_prompt in prompts.items():
        print(f"\n{'─'*50}")
        print(f"📝 Testing: {variant_name}")
        
        agent = STIHLSalesAgent(system_prompt=system_prompt)
        
        try:
            response = agent.run(scenario['query'], variant_name)
            
            print(f"   Tools called: {len(response.tool_calls)}")
            print(f"   Response length: {len(response.response)} chars")
            
            evaluation = evaluator.evaluate_response(
                query=scenario['query'],
                response=response.response,
                context=response.context,
                prompt_variant=variant_name
            )
            
            results.append(evaluation)
            
        finally:
            agent.close()
    
    if len(results) >= 2:
        comparison = compare_evaluations(results)
        print_comparison_report(comparison)
        
        # Save the optimized prompt if it won
        if comparison['best_variant'] == 'optimized':
            save_production_prompt()
    
    return results


def save_production_prompt():
    """Save the optimized prompt for production use."""
    
    output_dir = Path("prompts/system")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    prompt_data = {
        "name": "STIHL Sales Analytics Expert",
        "version": "1.0",
        "created": datetime.now().isoformat(),
        "prompt": build_optimized_prompt(),
        "notes": "Optimized prompt from Lab 8 experiments combining CoT, few-shot patterns, and persona design."
    }
    
    output_file = output_dir / "production_prompt.json"
    with open(output_file, 'w') as f:
        json.dump(prompt_data, f, indent=2)
    
    print(f"\n💾 Production prompt saved: {output_file}")


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys
    
    print("Lab 8: Prompt Engineering - Part 4")
    print("System Prompt Engineering\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--personas":
        run_persona_experiment()
    else:
        run_optimized_vs_baseline()
