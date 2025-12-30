"""
MLOps Training Script
Trains a model and logs to MLflow.

Usage:
    python train.py --config configs/train_config.yaml --experiment-name my-experiment
"""

import argparse
import json
import time
from pathlib import Path
from datetime import datetime
import yaml

import mlflow
import mlflow.sklearn
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
import pandas as pd
import numpy as np
import joblib


def load_config(config_path: str) -> dict:
    """Load training configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_data(data_path: str) -> tuple[pd.DataFrame, pd.Series]:
    """Load training data."""
    # For demo, generate synthetic data if file doesn't exist
    if not Path(data_path).exists():
        print(f"Data file not found: {data_path}. Generating synthetic data...")
        np.random.seed(42)
        n_samples = 1000
        
        X = pd.DataFrame({
            'feature_1': np.random.randn(n_samples),
            'feature_2': np.random.randn(n_samples),
            'feature_3': np.random.randn(n_samples),
            'feature_4': np.random.randn(n_samples),
            'feature_5': np.random.randn(n_samples),
        })
        
        # Create target based on features
        y = (X['feature_1'] + X['feature_2'] * 0.5 + np.random.randn(n_samples) * 0.3 > 0).astype(int)
        
        return X, pd.Series(y, name='target')
    
    df = pd.read_csv(data_path)
    X = df.drop('target', axis=1)
    y = df['target']
    return X, y


def get_model(model_type: str, params: dict):
    """Get model instance based on type."""
    models = {
        'random_forest': RandomForestClassifier,
        'gradient_boosting': GradientBoostingClassifier,
        'logistic_regression': LogisticRegression,
    }
    
    if model_type not in models:
        raise ValueError(f"Unknown model type: {model_type}. Available: {list(models.keys())}")
    
    return models[model_type](**params)


def evaluate_model(model, X_test, y_test) -> dict:
    """Evaluate model and return metrics."""
    
    # Predictions
    y_pred = model.predict(X_test)
    
    # Latency measurement
    latencies = []
    for _ in range(100):
        sample = X_test.iloc[[0]]
        start = time.time()
        model.predict(sample)
        latencies.append((time.time() - start) * 1000)  # ms
    
    return {
        'accuracy': accuracy_score(y_test, y_pred),
        'f1_score': f1_score(y_test, y_pred, average='weighted'),
        'precision': precision_score(y_test, y_pred, average='weighted'),
        'recall': recall_score(y_test, y_pred, average='weighted'),
        'latency_p50_ms': np.percentile(latencies, 50),
        'latency_p95_ms': np.percentile(latencies, 95),
        'latency_p99_ms': np.percentile(latencies, 99),
    }


def train(config: dict, experiment_name: str) -> dict:
    """Main training function."""
    
    print(f"Starting training with experiment: {experiment_name}")
    
    # Set experiment
    mlflow.set_experiment(experiment_name)
    
    # Load data
    X, y = load_data(config.get('data_path', 'data/train.csv'))
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, 
        test_size=config.get('test_size', 0.2),
        random_state=config.get('random_seed', 42)
    )
    
    print(f"Training data: {len(X_train)} samples")
    print(f"Test data: {len(X_test)} samples")
    
    with mlflow.start_run() as run:
        run_id = run.info.run_id
        print(f"MLflow Run ID: {run_id}")
        
        # Log parameters
        model_type = config.get('model_type', 'random_forest')
        model_params = config.get('model_params', {})
        
        mlflow.log_param('model_type', model_type)
        mlflow.log_params(model_params)
        mlflow.log_param('train_samples', len(X_train))
        mlflow.log_param('test_samples', len(X_test))
        
        # Train model
        print(f"Training {model_type}...")
        model = get_model(model_type, model_params)
        
        train_start = time.time()
        model.fit(X_train, y_train)
        train_time = time.time() - train_start
        
        mlflow.log_metric('training_time_seconds', train_time)
        print(f"Training completed in {train_time:.2f}s")
        
        # Evaluate
        print("Evaluating model...")
        metrics = evaluate_model(model, X_test, y_test)
        
        # Log metrics
        for metric_name, value in metrics.items():
            mlflow.log_metric(metric_name, value)
            print(f"  {metric_name}: {value:.4f}")
        
        # Log model
        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            registered_model_name=None,  # Don't auto-register
        )
        
        # Save model size
        model_path = Path("temp_model.joblib")
        joblib.dump(model, model_path)
        model_size_mb = model_path.stat().st_size / (1024 * 1024)
        mlflow.log_metric('model_size_mb', model_size_mb)
        model_path.unlink()
        
        # Log tags
        mlflow.set_tags({
            'trained_by': 'ci-pipeline',
            'timestamp': datetime.now().isoformat(),
            'data_version': config.get('data_version', 'unknown'),
        })
        
        model_uri = f"runs:/{run_id}/model"
        
        return {
            'run_id': run_id,
            'model_uri': model_uri,
            'experiment_name': experiment_name,
            'metrics': metrics,
            'model_type': model_type,
            'training_time_seconds': train_time,
            'model_size_mb': model_size_mb,
        }


def main():
    parser = argparse.ArgumentParser(description='Train ML model')
    parser.add_argument('--config', type=str, default='configs/train_config.yaml',
                        help='Path to training config')
    parser.add_argument('--experiment-name', type=str, default='default-experiment',
                        help='MLflow experiment name')
    parser.add_argument('--output-file', type=str, default='training_output.json',
                        help='Output file for results')
    
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config) if Path(args.config).exists() else {}
    
    # Train
    results = train(config, args.experiment_name)
    
    # Save results
    with open(args.output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Training complete. Results saved to {args.output_file}")
    print(f"   Accuracy: {results['metrics']['accuracy']:.4f}")
    print(f"   Model URI: {results['model_uri']}")


if __name__ == '__main__':
    main()
