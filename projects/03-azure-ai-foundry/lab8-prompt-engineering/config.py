"""
Lab 8: Prompt Engineering - Configuration
Shared settings for Azure OpenAI, Databricks, and evaluation.

Integration:
- Uses same Azure OpenAI deployment as Labs 1-7
- Uses same Databricks tables as Lab 6 agent
- Uses same evaluation metrics as Lab 5
"""

import os
import sys
from dotenv import load_dotenv
from dataclasses import dataclass
from pathlib import Path

# Load environment variables from project root
# Supports running from lab folder or project root
env_paths = [
    Path(__file__).parent.parent.parent.parent / ".env",  # Project root
    Path(__file__).parent / ".env",  # Lab folder
    Path.cwd() / ".env"  # Current directory
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break


@dataclass
class AzureOpenAIConfig:
    """Azure OpenAI configuration."""
    endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    api_version: str = "2024-12-01-preview"
    deployment_name: str = "gpt-4o"  # Main model for agent
    eval_deployment: str = "gpt-4o"  # Model for evaluation (LLM-as-judge)


@dataclass
class DatabricksConfig:
    """Databricks Unity Catalog configuration."""
    host: str = os.getenv("DATABRICKS_HOST", "")
    http_path: str = os.getenv("DATABRICKS_HTTP_PATH", "")
    token: str = os.getenv("DATABRICKS_TOKEN", "")
    catalog: str = os.getenv("DATABRICKS_CATALOG", "ai_systems")
    schema: str = os.getenv("DATABRICKS_SCHEMA", "stihl_gold")
    
    @property
    def connection_params(self) -> dict:
        """Return connection parameters for databricks-sql-connector."""
        return {
            "server_hostname": self.host,
            "http_path": self.http_path,
            "access_token": self.token,
        }


@dataclass
class EvaluationConfig:
    """Evaluation settings based on Lab 5 framework."""
    metrics: tuple = ("groundedness", "relevance", "coherence", "fluency")
    scale_min: int = 1
    scale_max: int = 5
    passing_threshold: float = 4.0
    

# Test scenarios for prompt engineering experiments
TEST_SCENARIOS = [
    {
        "id": "Q1",
        "query": "What were the top 3 products by revenue last quarter?",
        "complexity": "simple",
        "expected_elements": ["product names", "revenue figures", "ranking"],
        "ground_truth_query": """
            SELECT product_name, SUM(revenue) as total_revenue
            FROM ai_systems.stihl_silver.fact_sales
            WHERE sale_date >= DATE_ADD(CURRENT_DATE(), -90)
            GROUP BY product_name
            ORDER BY total_revenue DESC
            LIMIT 3
        """
    },
    {
        "id": "Q2", 
        "query": "Analyze the chainsaw category sales trend over the past 6 months and explain the pattern.",
        "complexity": "medium",
        "expected_elements": ["trend direction", "monthly breakdown", "explanation"],
        "ground_truth_query": """
            SELECT DATE_TRUNC('month', sale_date) as month,
                   SUM(revenue) as monthly_revenue,
                   COUNT(*) as transaction_count
            FROM ai_systems.stihl_silver.fact_sales
            WHERE product_category = 'Chainsaws'
              AND sale_date >= DATE_ADD(CURRENT_DATE(), -180)
            GROUP BY DATE_TRUNC('month', sale_date)
            ORDER BY month
        """
    },
    {
        "id": "Q3",
        "query": "Compare regional sales performance and recommend which regions should be our focus for next quarter.",
        "complexity": "complex",
        "expected_elements": ["regional comparison", "metrics", "recommendation", "reasoning"],
        "ground_truth_query": """
            SELECT region,
                   SUM(revenue) as total_revenue,
                   COUNT(DISTINCT customer_id) as unique_customers,
                   AVG(revenue) as avg_order_value
            FROM ai_systems.stihl_silver.fact_sales
            WHERE sale_date >= DATE_ADD(CURRENT_DATE(), -90)
            GROUP BY region
            ORDER BY total_revenue DESC
        """
    },
    {
        "id": "Q4",
        "query": "Identify any unusual patterns or anomalies in the recent sales data that we should investigate.",
        "complexity": "complex", 
        "expected_elements": ["anomaly identification", "supporting data", "investigation suggestion"],
        "ground_truth_query": """
            SELECT product_category,
                   DATE_TRUNC('week', sale_date) as week,
                   SUM(revenue) as weekly_revenue,
                   LAG(SUM(revenue)) OVER (PARTITION BY product_category ORDER BY DATE_TRUNC('week', sale_date)) as prev_week
            FROM ai_systems.stihl_silver.fact_sales
            WHERE sale_date >= DATE_ADD(CURRENT_DATE(), -60)
            GROUP BY product_category, DATE_TRUNC('week', sale_date)
            ORDER BY week DESC
            LIMIT 20
        """
    },
]


# Instantiate configs
azure_config = AzureOpenAIConfig()
databricks_config = DatabricksConfig()
eval_config = EvaluationConfig()


def validate_config() -> bool:
    """Validate that all required configuration is present."""
    errors = []
    
    if not azure_config.endpoint:
        errors.append("AZURE_OPENAI_ENDPOINT not set")
    if not azure_config.api_key:
        errors.append("AZURE_OPENAI_API_KEY not set")
    if not databricks_config.host:
        errors.append("DATABRICKS_HOST not set")
    if not databricks_config.token:
        errors.append("DATABRICKS_TOKEN not set")
    
    if errors:
        print("❌ Configuration errors:")
        for e in errors:
            print(f"   - {e}")
        return False
    
    print("✅ Configuration validated successfully")
    return True


if __name__ == "__main__":
    print("Lab 8: Prompt Engineering - Configuration Check")
    print("="*50)
    
    if validate_config():
        print(f"\nAzure OpenAI Endpoint: {azure_config.endpoint[:50]}...")
        print(f"Databricks Host: {databricks_config.host}")
        print(f"Catalog.Schema: {databricks_config.catalog}.{databricks_config.schema}")
        print(f"\nTest scenarios defined: {len(TEST_SCENARIOS)}")
        for s in TEST_SCENARIOS:
            print(f"  - {s['id']}: {s['query'][:50]}... ({s['complexity']})")
