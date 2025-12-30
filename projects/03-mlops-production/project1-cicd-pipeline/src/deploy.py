"""
MLOps Deployment Script
Deploys model to Azure ML managed endpoint.

Usage:
    python deploy.py --model-uri models:/name/1 --environment staging
"""

import argparse
import json
import os
from datetime import datetime

# Azure ML SDK
try:
    from azure.ai.ml import MLClient
    from azure.ai.ml.entities import (
        ManagedOnlineEndpoint,
        ManagedOnlineDeployment,
        Model,
        Environment,
        CodeConfiguration,
    )
    from azure.identity import DefaultAzureCredential
    AZURE_ML_AVAILABLE = True
except ImportError:
    AZURE_ML_AVAILABLE = False
    print("⚠️ azure-ai-ml not installed. Install with: pip install azure-ai-ml")


def get_ml_client(resource_group: str, workspace: str) -> 'MLClient':
    """Get Azure ML client."""
    credential = DefaultAzureCredential()
    
    return MLClient(
        credential=credential,
        subscription_id=os.environ.get('AZURE_SUBSCRIPTION_ID'),
        resource_group_name=resource_group,
        workspace_name=workspace,
    )


def deploy_model(
    model_uri: str,
    environment: str,
    endpoint_name: str,
    resource_group: str,
    workspace: str,
    deployment_strategy: str = 'rolling',
    initial_traffic_percent: int = 100,
) -> dict:
    """Deploy model to Azure ML endpoint."""
    
    print(f"Deploying model to {environment}...")
    print(f"  Model URI: {model_uri}")
    print(f"  Endpoint: {endpoint_name}")
    print(f"  Strategy: {deployment_strategy}")
    
    if not AZURE_ML_AVAILABLE:
        # Return mock results for demo
        print("  ⚠️ Azure ML SDK not available - returning mock results")
        return {
            'endpoint_name': endpoint_name,
            'endpoint_url': f"https://{endpoint_name}.westus2.inference.ml.azure.com/score",
            'deployment_name': f"deployment-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'environment': environment,
            'model_uri': model_uri,
            'traffic_percent': initial_traffic_percent,
            'status': 'mock-success',
        }
    
    # Get ML client
    ml_client = get_ml_client(resource_group, workspace)
    
    # Create or get endpoint
    try:
        endpoint = ml_client.online_endpoints.get(endpoint_name)
        print(f"  Using existing endpoint: {endpoint_name}")
    except Exception:
        print(f"  Creating new endpoint: {endpoint_name}")
        endpoint = ManagedOnlineEndpoint(
            name=endpoint_name,
            description=f"Endpoint for {environment} environment",
            auth_mode="key",
        )
        ml_client.online_endpoints.begin_create_or_update(endpoint).result()
    
    # Create deployment
    deployment_name = f"deployment-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    deployment = ManagedOnlineDeployment(
        name=deployment_name,
        endpoint_name=endpoint_name,
        model=model_uri,
        instance_type="Standard_DS2_v2",
        instance_count=1,
    )
    
    print(f"  Creating deployment: {deployment_name}")
    ml_client.online_deployments.begin_create_or_update(deployment).result()
    
    # Set traffic
    if deployment_strategy == 'blue-green':
        # Blue-green: new deployment gets initial_traffic_percent
        endpoint.traffic = {deployment_name: initial_traffic_percent}
    else:
        # Rolling: new deployment gets 100%
        endpoint.traffic = {deployment_name: 100}
    
    ml_client.online_endpoints.begin_create_or_update(endpoint).result()
    
    # Get endpoint URL
    endpoint = ml_client.online_endpoints.get(endpoint_name)
    
    return {
        'endpoint_name': endpoint_name,
        'endpoint_url': endpoint.scoring_uri,
        'deployment_name': deployment_name,
        'environment': environment,
        'model_uri': model_uri,
        'traffic_percent': initial_traffic_percent if deployment_strategy == 'blue-green' else 100,
        'status': 'success',
    }


def main():
    parser = argparse.ArgumentParser(description='Deploy ML model')
    parser.add_argument('--model-uri', type=str, required=True,
                        help='URI of model to deploy')
    parser.add_argument('--environment', type=str, required=True,
                        choices=['staging', 'production'],
                        help='Target environment')
    parser.add_argument('--endpoint-name', type=str, required=True,
                        help='Name of the endpoint')
    parser.add_argument('--resource-group', type=str, required=True,
                        help='Azure resource group')
    parser.add_argument('--workspace', type=str, required=True,
                        help='Azure ML workspace')
    parser.add_argument('--deployment-strategy', type=str, default='rolling',
                        choices=['rolling', 'blue-green'],
                        help='Deployment strategy')
    parser.add_argument('--initial-traffic-percent', type=int, default=100,
                        help='Initial traffic percentage for blue-green')
    parser.add_argument('--output-file', type=str, default='deploy_results.json',
                        help='Output file for results')
    
    args = parser.parse_args()
    
    # Deploy
    results = deploy_model(
        model_uri=args.model_uri,
        environment=args.environment,
        endpoint_name=args.endpoint_name,
        resource_group=args.resource_group,
        workspace=args.workspace,
        deployment_strategy=args.deployment_strategy,
        initial_traffic_percent=args.initial_traffic_percent,
    )
    
    # Save results
    with open(args.output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Deployment complete")
    print(f"   Endpoint: {results['endpoint_url']}")
    print(f"   Traffic: {results['traffic_percent']}%")


if __name__ == '__main__':
    main()
