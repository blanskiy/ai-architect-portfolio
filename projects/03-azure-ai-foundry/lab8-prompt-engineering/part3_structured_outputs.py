"""
Lab 8: Prompt Engineering - Part 3
Structured Outputs

This module focuses on:
1. JSON mode for consistent output formats
2. Schema validation for sales insights
3. Structured tool responses
4. Format adherence evaluation

Builds on Part 2 findings to implement structured output patterns.
"""

import json
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from config import azure_config, databricks_config, TEST_SCENARIOS, validate_config
from evaluator import PromptEvaluator, compare_evaluations, print_comparison_report
from agent_integration import STIHLSalesAgent

# Try importing Pydantic for schema validation
try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    print("⚠️  pydantic not installed. Install with: pip install pydantic")


# =============================================================================
# OUTPUT SCHEMAS (using Pydantic for validation)
# =============================================================================

if PYDANTIC_AVAILABLE:
    
    class TrendDirection(str, Enum):
        UP = "up"
        DOWN = "down"
        FLAT = "flat"
        VOLATILE = "volatile"

    class ConfidenceLevel(str, Enum):
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"

    class SalesTrendInsight(BaseModel):
        """Schema for trend analysis responses."""
        metric: str = Field(description="The metric being analyzed")
        time_period: str = Field(description="Time period analyzed")
        direction: TrendDirection = Field(description="Overall trend direction")
        change_percentage: float = Field(description="Percentage change over period")
        confidence: ConfidenceLevel = Field(description="Confidence in analysis")
        key_drivers: list[str] = Field(description="Factors driving the trend")
        recommendation: Optional[str] = Field(default=None, description="Actionable recommendation")

    class ProductRanking(BaseModel):
        """Schema for a single product in ranking."""
        rank: int = Field(description="Position in ranking")
        product_name: str = Field(description="Name of the product")
        category: str = Field(description="Product category")
        revenue: float = Field(description="Revenue value")
        growth_rate: Optional[float] = Field(default=None, description="Growth rate")

    class ProductRankingResponse(BaseModel):
        """Schema for product ranking responses."""
        query: str = Field(description="Original question")
        time_period: str = Field(description="Time period")
        products: list[ProductRanking] = Field(description="Ranked products")
        insight: str = Field(description="Key insight")

    class RegionalMetrics(BaseModel):
        """Schema for regional data."""
        region: str = Field(description="Region name")
        total_revenue: float = Field(description="Total revenue")
        revenue_share: float = Field(description="Percentage of total")
        growth_rate: float = Field(description="Growth rate")
        performance: str = Field(description="Performance rating: strong/average/weak")

    class RegionalComparisonResponse(BaseModel):
        """Schema for regional comparison."""
        query: str = Field(description="Original question")
        regions: list[RegionalMetrics] = Field(description="Regional breakdown")
        top_performer: str = Field(description="Best region")
        recommendation: str = Field(description="Strategic recommendation")


# =============================================================================
# STRUCTURED OUTPUT SYSTEM PROMPTS
# =============================================================================

STRUCTURED_PROMPTS = {
    "json_ranking": '''You are a STIHL Sales Analytics Expert.

When asked about product rankings or top performers, respond ONLY with valid JSON matching this schema:

{
    "query": "string - the original question",
    "time_period": "string - the time period analyzed",
    "products": [
        {
            "rank": number,
            "product_name": "string",
            "category": "string",
            "revenue": number,
            "growth_rate": number or null
        }
    ],
    "insight": "string - key takeaway from the data"
}

Instructions:
1. Use the tools to retrieve the actual data
2. Format your response as JSON only - no additional text
3. Ensure all numeric values are actual numbers, not strings
4. Include exactly the fields shown above''',

    "json_regional": '''You are a STIHL Sales Analytics Expert.

For regional comparison questions, respond ONLY with valid JSON matching this schema:

{
    "query": "string - the original question",
    "regions": [
        {
            "region": "string",
            "total_revenue": number,
            "revenue_share": number (percentage as decimal, e.g., 0.25 for 25%),
            "growth_rate": number (percentage as decimal),
            "performance": "strong" | "average" | "weak"
        }
    ],
    "top_performer": "string - name of best performing region",
    "recommendation": "string - strategic recommendation"
}

Instructions:
1. Retrieve data using the available tools
2. Respond with JSON only - no markdown, no explanation
3. Calculate revenue_share as each region's portion of total
4. Rate performance based on growth and revenue contribution''',

    "json_trend": '''You are a STIHL Sales Analytics Expert.

For trend analysis questions, respond ONLY with valid JSON:

{
    "metric": "string - what is being measured",
    "time_period": "string - period analyzed",
    "direction": "up" | "down" | "flat" | "volatile",
    "change_percentage": number,
    "confidence": "high" | "medium" | "low",
    "key_drivers": ["array", "of", "factors"],
    "recommendation": "string or null"
}

Instructions:
1. Query the data using appropriate tools
2. Analyze the trend direction and magnitude
3. Return pure JSON only'''
}


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def extract_json_from_response(response: str) -> Optional[dict]:
    """Extract JSON from a response that might have extra text."""
    
    # Try direct parse first
    try:
        return json.loads(response.strip())
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON in markdown code block
    if "```" in response:
        try:
            start = response.find("```json")
            if start == -1:
                start = response.find("```")
            start = response.find("\n", start) + 1
            end = response.find("```", start)
            json_str = response[start:end].strip()
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass
    
    # Try to find JSON object in response
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            json_str = response[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    return None


def validate_against_schema(data: dict, schema_name: str) -> tuple[bool, list[str]]:
    """Validate data against a Pydantic schema."""
    
    if not PYDANTIC_AVAILABLE:
        return True, ["Pydantic not available - skipping validation"]
    
    schema_map = {
        "ranking": ProductRankingResponse,
        "regional": RegionalComparisonResponse,
        "trend": SalesTrendInsight
    }
    
    schema_class = schema_map.get(schema_name)
    if not schema_class:
        return False, [f"Unknown schema: {schema_name}"]
    
    try:
        schema_class(**data)
        return True, []
    except Exception as e:
        return False, [str(e)]


# =============================================================================
# EXPERIMENT: STRUCTURED VS NATURAL
# =============================================================================

def run_structured_experiment():
    """
    Compare structured JSON outputs with natural language responses.
    Tests format adherence and data accuracy.
    """
    
    print("\n" + "="*70)
    print("🏗️  LAB 8: PROMPT ENGINEERING - PART 3")
    print("    Structured Outputs Experiment")
    print("="*70)
    
    if not validate_config():
        print("\n❌ Fix configuration before running")
        return None
    
    evaluator = PromptEvaluator()
    results = []
    
    # Test Q1 (ranking) with both natural and structured prompts
    scenario = TEST_SCENARIOS[0]  # Top 3 products
    
    prompts_to_test = {
        "natural": """You are a STIHL Sales Analytics Expert. 
Answer questions clearly with specific data points.""",
        
        "structured_json": STRUCTURED_PROMPTS["json_ranking"]
    }
    
    print(f"\n📊 Scenario: {scenario['id']}")
    print(f"   Query: {scenario['query']}")
    
    for variant_name, system_prompt in prompts_to_test.items():
        print(f"\n{'─'*50}")
        print(f"🧪 Testing: {variant_name}")
        
        agent = STIHLSalesAgent(system_prompt=system_prompt)
        
        try:
            response = agent.run(scenario['query'], variant_name)
            
            print(f"   Response preview: {response.response[:100]}...")
            
            # For structured output, try to validate
            if variant_name.startswith("structured"):
                json_data = extract_json_from_response(response.response)
                if json_data:
                    is_valid, errors = validate_against_schema(json_data, "ranking")
                    print(f"   JSON Valid: {'✅' if is_valid else '❌'}")
                    if errors:
                        print(f"   Errors: {errors[:2]}")
                else:
                    print("   ❌ Could not extract JSON from response")
            
            # Evaluate
            evaluation = evaluator.evaluate_response(
                query=scenario['query'],
                response=response.response,
                context=response.context,
                prompt_variant=variant_name
            )
            
            results.append(evaluation)
            
        finally:
            agent.close()
    
    # Compare
    if len(results) >= 2:
        comparison = compare_evaluations(results)
        print_comparison_report(comparison)
    
    return results


if __name__ == "__main__":
    print("Lab 8: Prompt Engineering - Part 3")
    print("Structured Outputs\n")
    
    run_structured_experiment()
