"""
MLOps Evaluation Script
Compares challenger model against champion (production) model.

Usage:
    python evaluate.py --challenger-uri runs:/xxx/model --champion-model models:/name/Production
"""

import argparse
import json
import time
from pathlib import Path
from typing import Optional

import mlflow
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score


def load_model(model_uri: str):
    """Load model from MLflow."""
    print(f"Loading model from: {model_uri}")
    return mlflow.sklearn.load_model(model_uri)


def load_test_data(data_path: str) -> tuple[pd.DataFrame, pd.Series]:
    """Load evaluation data."""
    if not Path(data_path).exists():
        print(f"Test data not found: {data_path}. Generating synthetic data...")
        np.random.seed(123)  # Different seed than training
        n_samples = 200
        
        X = pd.DataFrame({
            'feature_1': np.random.randn(n_samples),
            'feature_2': np.random.randn(n_samples),
            'feature_3': np.random.randn(n_samples),
            'feature_4': np.random.randn(n_samples),
            'feature_5': np.random.randn(n_samples),
        })
        
        y = (X['feature_1'] + X['feature_2'] * 0.5 + np.random.randn(n_samples) * 0.3 > 0).astype(int)
        
        return X, pd.Series(y, name='target')
    
    df = pd.read_csv(data_path)
    X = df.drop('target', axis=1)
    y = df['target']
    return X, y


def evaluate_model(model, X: pd.DataFrame, y: pd.Series, n_latency_samples: int = 100) -> dict:
    """Evaluate a model and return metrics."""
    
    # Predictions
    y_pred = model.predict(X)
    
    # Latency measurement
    latencies = []
    for i in range(min(n_latency_samples, len(X))):
        sample = X.iloc[[i]]
        start = time.time()
        model.predict(sample)
        latencies.append((time.time() - start) * 1000)  # ms
    
    return {
        'accuracy': float(accuracy_score(y, y_pred)),
        'f1_score': float(f1_score(y, y_pred, average='weighted')),
        'precision': float(precision_score(y, y_pred, average='weighted')),
        'recall': float(recall_score(y, y_pred, average='weighted')),
        'latency_p50_ms': float(np.percentile(latencies, 50)),
        'latency_p95_ms': float(np.percentile(latencies, 95)),
        'latency_p99_ms': float(np.percentile(latencies, 99)),
        'samples_evaluated': len(X),
    }


def compare_models(challenger_metrics: dict, champion_metrics: Optional[dict]) -> dict:
    """Compare challenger and champion metrics."""
    
    if champion_metrics is None:
        return {
            'accuracy_diff': 0.0,
            'f1_diff': 0.0,
            'latency_diff_ms': 0.0,
            'challenger_is_better': True,
            'notes': 'No champion model - challenger is first version'
        }
    
    return {
        'accuracy_diff': challenger_metrics['accuracy'] - champion_metrics['accuracy'],
        'f1_diff': challenger_metrics['f1_score'] - champion_metrics['f1_score'],
        'latency_diff_ms': challenger_metrics['latency_p95_ms'] - champion_metrics['latency_p95_ms'],
        'challenger_is_better': challenger_metrics['accuracy'] >= champion_metrics['accuracy'],
    }


def main():
    parser = argparse.ArgumentParser(description='Evaluate ML model')
    parser.add_argument('--challenger-uri', type=str, required=True,
                        help='URI of challenger model')
    parser.add_argument('--champion-model', type=str, default=None,
                        help='URI of champion model (optional)')
    parser.add_argument('--test-data', type=str, default='data/eval/',
                        help='Path to test data')
    parser.add_argument('--output-file', type=str, default='evaluation_results.json',
                        help='Output file for results')
    
    args = parser.parse_args()
    
    # Load test data
    test_data_path = Path(args.test_data)
    if test_data_path.is_dir():
        test_data_path = test_data_path / 'test.csv'
    
    X_test, y_test = load_test_data(str(test_data_path))
    print(f"Loaded {len(X_test)} test samples")
    
    # Evaluate challenger
    print("\n📊 Evaluating Challenger Model...")
    challenger_model = load_model(args.challenger_uri)
    challenger_metrics = evaluate_model(challenger_model, X_test, y_test)
    
    print(f"  Accuracy: {challenger_metrics['accuracy']:.4f}")
    print(f"  F1 Score: {challenger_metrics['f1_score']:.4f}")
    print(f"  Latency P95: {challenger_metrics['latency_p95_ms']:.2f}ms")
    
    # Evaluate champion (if exists)
    champion_metrics = None
    if args.champion_model:
        try:
            print("\n📊 Evaluating Champion Model...")
            champion_model = load_model(args.champion_model)
            champion_metrics = evaluate_model(champion_model, X_test, y_test)
            
            print(f"  Accuracy: {champion_metrics['accuracy']:.4f}")
            print(f"  F1 Score: {champion_metrics['f1_score']:.4f}")
            print(f"  Latency P95: {champion_metrics['latency_p95_ms']:.2f}ms")
        except Exception as e:
            print(f"  ⚠️ Could not load champion model: {e}")
            print("  Proceeding without champion comparison")
    
    # Compare
    comparison = compare_models(challenger_metrics, champion_metrics)
    
    print("\n📈 Comparison:")
    print(f"  Accuracy Diff: {comparison['accuracy_diff']:+.4f}")
    print(f"  Challenger is Better: {comparison['challenger_is_better']}")
    
    # Build results
    results = {
        'challenger': {
            'model_uri': args.challenger_uri,
            **challenger_metrics
        },
        'champion': {
            'model_uri': args.champion_model,
            **(champion_metrics or {})
        } if champion_metrics else None,
        'comparison': comparison,
        'test_data': str(test_data_path),
    }
    
    # Save results
    with open(args.output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Evaluation complete. Results saved to {args.output_file}")


if __name__ == '__main__':
    main()
