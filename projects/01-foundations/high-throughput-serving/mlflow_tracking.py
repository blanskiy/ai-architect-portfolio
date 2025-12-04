"""
MLflow Experiment Tracking for ResNet-50 Model
Week 3 Day 13: Model Versioning
"""

import mlflow
import mlflow.pytorch
import torch
import torchvision.models as models
import time
import os
from datetime import datetime

# Set experiment name
EXPERIMENT_NAME = "resnet50-image-classification"

def setup_mlflow():
    """Initialize MLflow tracking"""
    # Set tracking URI (local folder)
    mlflow.set_tracking_uri("file:./mlruns")
    
    # Create or get experiment
    experiment = mlflow.set_experiment(EXPERIMENT_NAME)
    print(f"Experiment: {experiment.name}")
    print(f"Experiment ID: {experiment.experiment_id}")
    print(f"Artifact Location: {experiment.artifact_location}")
    return experiment

def load_model():
    """Load ResNet-50 model"""
    print("\nLoading ResNet-50 model...")
    model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V1)
    model.eval()
    return model

def benchmark_inference(model, num_runs=10):
    """Benchmark model inference speed"""
    print(f"\nRunning {num_runs} inference benchmarks...")
    
    # Create dummy input (batch of 1 image)
    dummy_input = torch.randn(1, 3, 224, 224)
    
    # Warmup
    with torch.no_grad():
        for _ in range(3):
            _ = model(dummy_input)
    
    # Benchmark
    latencies = []
    with torch.no_grad():
        for i in range(num_runs):
            start = time.perf_counter()
            _ = model(dummy_input)
            end = time.perf_counter()
            latencies.append((end - start) * 1000)  # Convert to ms
    
    return {
        "mean_latency_ms": sum(latencies) / len(latencies),
        "min_latency_ms": min(latencies),
        "max_latency_ms": max(latencies),
        "std_latency_ms": (sum((x - sum(latencies)/len(latencies))**2 for x in latencies) / len(latencies)) ** 0.5
    }

def run_experiment(model_variant="pytorch", batch_size=1, num_benchmark_runs=10):
    """Run a single experiment and log to MLflow"""
    
    print(f"\n{'='*60}")
    print(f"Running experiment: {model_variant}, batch_size={batch_size}")
    print(f"{'='*60}")
    
    with mlflow.start_run(run_name=f"{model_variant}_bs{batch_size}_{datetime.now().strftime('%H%M%S')}"):
        
        # Log parameters
        mlflow.log_param("model_name", "ResNet-50")
        mlflow.log_param("model_variant", model_variant)
        mlflow.log_param("batch_size", batch_size)
        mlflow.log_param("num_benchmark_runs", num_benchmark_runs)
        mlflow.log_param("input_size", "224x224")
        mlflow.log_param("num_classes", 1000)
        mlflow.log_param("pretrained", True)
        mlflow.log_param("device", "cpu")
        
        # Load model
        model = load_model()
        
        # Get model info
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        mlflow.log_param("total_parameters", total_params)
        mlflow.log_param("trainable_parameters", trainable_params)
        
        # Run benchmark
        metrics = benchmark_inference(model, num_benchmark_runs)
        
        # Log metrics
        mlflow.log_metric("mean_latency_ms", metrics["mean_latency_ms"])
        mlflow.log_metric("min_latency_ms", metrics["min_latency_ms"])
        mlflow.log_metric("max_latency_ms", metrics["max_latency_ms"])
        mlflow.log_metric("std_latency_ms", metrics["std_latency_ms"])
        mlflow.log_metric("throughput_rps", 1000 / metrics["mean_latency_ms"])
        
        # Log model accuracy (ImageNet top-1)
        mlflow.log_metric("imagenet_top1_accuracy", 76.13)
        mlflow.log_metric("imagenet_top5_accuracy", 92.86)
        
        # Log model size
        model_size_mb = total_params * 4 / (1024 * 1024)  # Float32 = 4 bytes
        mlflow.log_metric("model_size_mb", model_size_mb)
        
        # Create and log a summary artifact
        summary = f"""
Model Summary
=============
Model: ResNet-50
Variant: {model_variant}
Parameters: {total_params:,}
Size: {model_size_mb:.2f} MB

Performance
===========
Mean Latency: {metrics['mean_latency_ms']:.2f} ms
Min Latency: {metrics['min_latency_ms']:.2f} ms
Max Latency: {metrics['max_latency_ms']:.2f} ms
Throughput: {1000 / metrics['mean_latency_ms']:.2f} RPS

Accuracy (ImageNet)
==================
Top-1: 76.13%
Top-5: 92.86%
"""
        
        # Save summary to file and log as artifact
        os.makedirs("artifacts", exist_ok=True)
        summary_path = "artifacts/model_summary.txt"
        with open(summary_path, "w") as f:
            f.write(summary)
        mlflow.log_artifact(summary_path)
        
        # Log the model itself
        print("\nLogging model to MLflow...")
        mlflow.pytorch.log_model(model, "model")
        
        print(f"\n✅ Experiment logged successfully!")
        print(f"   Mean Latency: {metrics['mean_latency_ms']:.2f} ms")
        print(f"   Throughput: {1000 / metrics['mean_latency_ms']:.2f} RPS")
        
        return mlflow.active_run().info.run_id

def main():
    """Main function to run multiple experiments"""
    print("="*60)
    print("MLflow Experiment Tracking Demo")
    print("="*60)
    
    # Setup MLflow
    setup_mlflow()
    
    # Run experiments with different configurations
    run_ids = []
    
    # Experiment 1: PyTorch baseline
    run_id = run_experiment(
        model_variant="pytorch",
        batch_size=1,
        num_benchmark_runs=10
    )
    run_ids.append(run_id)
    
    # Experiment 2: Different batch size
    run_id = run_experiment(
        model_variant="pytorch",
        batch_size=4,
        num_benchmark_runs=10
    )
    run_ids.append(run_id)
    
    # Experiment 3: Simulate ONNX variant
    run_id = run_experiment(
        model_variant="onnx",
        batch_size=1,
        num_benchmark_runs=10
    )
    run_ids.append(run_id)
    
    print("\n" + "="*60)
    print("All experiments completed!")
    print("="*60)
    print(f"\nRun IDs: {run_ids}")
    print("\n🚀 To view results, run:")
    print("   mlflow ui")
    print("\n   Then open: http://localhost:5000")

if __name__ == "__main__":
    main()