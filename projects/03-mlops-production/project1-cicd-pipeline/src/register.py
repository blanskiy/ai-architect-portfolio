"""
MLOps Model Registration
Registers a model to the MLflow Model Registry.

Usage:
    python register.py --model-uri runs:/xxx/model --model-name my-model
"""

import argparse
import json
from datetime import datetime

import mlflow
from mlflow.tracking import MlflowClient


def register_model(
    model_uri: str,
    model_name: str,
    run_id: str,
    tags: dict = None,
) -> dict:
    """Register model to MLflow Model Registry."""
    
    client = MlflowClient()
    
    # Register model
    print(f"Registering model: {model_name}")
    print(f"  Model URI: {model_uri}")
    
    result = mlflow.register_model(
        model_uri=model_uri,
        name=model_name,
    )
    
    version = result.version
    print(f"  Registered as version: {version}")
    
    # Add tags
    default_tags = {
        'registered_at': datetime.now().isoformat(),
        'source_run_id': run_id,
        'registered_by': 'ci-pipeline',
    }
    
    all_tags = {**default_tags, **(tags or {})}
    
    for key, value in all_tags.items():
        client.set_model_version_tag(model_name, version, key, str(value))
    
    # Transition to staging
    print(f"  Transitioning to Staging stage...")
    client.transition_model_version_stage(
        name=model_name,
        version=version,
        stage="Staging",
        archive_existing_versions=False,
    )
    
    return {
        'model_name': model_name,
        'version': version,
        'stage': 'Staging',
        'model_uri': f"models:/{model_name}/{version}",
        'source_run_id': run_id,
    }


def main():
    parser = argparse.ArgumentParser(description='Register ML model')
    parser.add_argument('--model-uri', type=str, required=True,
                        help='URI of model to register')
    parser.add_argument('--model-name', type=str, required=True,
                        help='Name for the registered model')
    parser.add_argument('--run-id', type=str, required=True,
                        help='MLflow run ID')
    parser.add_argument('--output-file', type=str, default='register_output.json',
                        help='Output file for results')
    
    args = parser.parse_args()
    
    # Register model
    results = register_model(
        model_uri=args.model_uri,
        model_name=args.model_name,
        run_id=args.run_id,
    )
    
    # Save results
    with open(args.output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Model registered successfully")
    print(f"   Name: {results['model_name']}")
    print(f"   Version: {results['version']}")
    print(f"   Stage: {results['stage']}")


if __name__ == '__main__':
    main()
