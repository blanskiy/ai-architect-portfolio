"""
ML Pipeline Orchestration
Week 4 Day 19: Automated ML Workflows
"""

import time
import random
import threading
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import json


class StepStatus(Enum):
    """Status of a pipeline step"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    """Result of a pipeline step execution"""
    step_name: str
    status: StepStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    logs: List[str] = field(default_factory=list)


@dataclass
class PipelineStep:
    """Defines a step in the ML pipeline"""
    name: str
    function: Callable
    dependencies: List[str] = field(default_factory=list)
    description: str = ""
    timeout_seconds: int = 300
    retries: int = 0
    
    def __hash__(self):
        return hash(self.name)


class MLPipeline:
    """
    ML Pipeline Orchestrator that manages step execution,
    dependencies, and failure handling.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.steps: Dict[str, PipelineStep] = {}
        self.results: Dict[str, StepResult] = {}
        self.context: Dict[str, Any] = {}  # Shared context between steps
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        print(f"\n{'='*60}")
        print(f"🔧 Pipeline Created: {name}")
        print(f"{'='*60}")
    
    def add_step(self, step: PipelineStep):
        """Add a step to the pipeline"""
        self.steps[step.name] = step
        print(f"   ➕ Added step: {step.name}")
        if step.dependencies:
            print(f"      Dependencies: {', '.join(step.dependencies)}")
    
    def _get_execution_order(self) -> List[str]:
        """
        Topological sort to determine execution order based on dependencies.
        """
        # Build dependency graph
        in_degree = {name: 0 for name in self.steps}
        graph = {name: [] for name in self.steps}
        
        for name, step in self.steps.items():
            for dep in step.dependencies:
                if dep in graph:
                    graph[dep].append(name)
                    in_degree[name] += 1
        
        # Kahn's algorithm for topological sort
        queue = [name for name, degree in in_degree.items() if degree == 0]
        order = []
        
        while queue:
            current = queue.pop(0)
            order.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(order) != len(self.steps):
            raise ValueError("Circular dependency detected in pipeline!")
        
        return order
    
    def _execute_step(self, step: PipelineStep) -> StepResult:
        """Execute a single pipeline step"""
        result = StepResult(
            step_name=step.name,
            status=StepStatus.RUNNING,
            start_time=datetime.now()
        )
        
        print(f"\n   ▶ Running: {step.name}")
        result.logs.append(f"Started at {result.start_time}")
        
        # Check dependencies
        for dep in step.dependencies:
            if dep in self.results:
                if self.results[dep].status != StepStatus.COMPLETED:
                    result.status = StepStatus.SKIPPED
                    result.error = f"Dependency '{dep}' did not complete successfully"
                    result.end_time = datetime.now()
                    print(f"     ⏭️ Skipped (dependency failed)")
                    return result
        
        # Execute with retries
        attempts = 0
        max_attempts = step.retries + 1
        
        while attempts < max_attempts:
            attempts += 1
            try:
                # Run the step function with context
                outputs = step.function(self.context)
                
                # Update context with outputs
                if outputs:
                    self.context.update(outputs)
                    result.outputs = outputs
                
                result.status = StepStatus.COMPLETED
                result.end_time = datetime.now()
                result.duration_seconds = (result.end_time - result.start_time).total_seconds()
                result.logs.append(f"Completed successfully in {result.duration_seconds:.2f}s")
                
                print(f"     ✅ Completed in {result.duration_seconds:.2f}s")
                return result
                
            except Exception as e:
                result.logs.append(f"Attempt {attempts} failed: {str(e)}")
                
                if attempts < max_attempts:
                    print(f"     ⚠️ Attempt {attempts} failed, retrying...")
                    time.sleep(1)
                else:
                    result.status = StepStatus.FAILED
                    result.error = str(e)
                    result.end_time = datetime.now()
                    result.duration_seconds = (result.end_time - result.start_time).total_seconds()
                    print(f"     ❌ Failed: {e}")
        
        return result
    
    def run(self, initial_context: Dict[str, Any] = None) -> Dict[str, StepResult]:
        """Run the entire pipeline"""
        self.start_time = datetime.now()
        self.context = initial_context or {}
        self.results = {}
        
        print(f"\n{'='*60}")
        print(f"🚀 Running Pipeline: {self.name}")
        print(f"   Started: {self.start_time}")
        print(f"{'='*60}")
        
        # Get execution order
        try:
            execution_order = self._get_execution_order()
            print(f"\n   Execution order: {' → '.join(execution_order)}")
        except ValueError as e:
            print(f"   ❌ Pipeline error: {e}")
            return self.results
        
        # Execute steps in order
        for step_name in execution_order:
            step = self.steps[step_name]
            result = self._execute_step(step)
            self.results[step_name] = result
            
            # Stop pipeline on failure (unless step has retries configured)
            if result.status == StepStatus.FAILED:
                print(f"\n   🛑 Pipeline stopped due to failure in '{step_name}'")
                break
        
        self.end_time = datetime.now()
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        # Print summary
        self._print_summary(total_duration)
        
        return self.results
    
    def _print_summary(self, total_duration: float):
        """Print pipeline execution summary"""
        print(f"\n{'='*60}")
        print(f"📊 Pipeline Summary: {self.name}")
        print(f"{'='*60}")
        
        completed = sum(1 for r in self.results.values() if r.status == StepStatus.COMPLETED)
        failed = sum(1 for r in self.results.values() if r.status == StepStatus.FAILED)
        skipped = sum(1 for r in self.results.values() if r.status == StepStatus.SKIPPED)
        
        print(f"\n   Total Steps: {len(self.steps)}")
        print(f"   ✅ Completed: {completed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   ⏭️ Skipped: {skipped}")
        print(f"   ⏱️ Total Duration: {total_duration:.2f}s")
        
        print(f"\n   Step Details:")
        print(f"   {'-'*50}")
        
        for name, result in self.results.items():
            status_icon = {
                StepStatus.COMPLETED: "✅",
                StepStatus.FAILED: "❌",
                StepStatus.SKIPPED: "⏭️",
                StepStatus.RUNNING: "🔄",
                StepStatus.PENDING: "⏳"
            }.get(result.status, "❓")
            
            print(f"   {status_icon} {name}: {result.duration_seconds:.2f}s")
            if result.error:
                print(f"      Error: {result.error}")
        
        print(f"\n{'='*60}")
        
        if failed == 0 and skipped == 0:
            print("🎉 Pipeline completed successfully!")
        else:
            print("⚠️ Pipeline completed with issues")
        print(f"{'='*60}\n")


# ============================================================================
# ML PIPELINE STEPS (Simulated)
# ============================================================================

def data_ingestion_step(context: Dict) -> Dict:
    """Step 1: Ingest raw data"""
    print("     📥 Loading raw data from source...")
    time.sleep(0.5)
    
    # Simulate data loading
    num_samples = random.randint(10000, 50000)
    num_features = 128
    
    print(f"     📊 Loaded {num_samples:,} samples with {num_features} features")
    
    return {
        "raw_data_path": "/data/raw/dataset_v1.parquet",
        "num_samples": num_samples,
        "num_features": num_features,
        "data_version": "v1.0.0"
    }


def data_validation_step(context: Dict) -> Dict:
    """Step 2: Validate data quality"""
    print("     🔍 Validating data quality...")
    time.sleep(0.3)
    
    num_samples = context.get("num_samples", 0)
    
    # Simulate validation checks
    checks = {
        "no_nulls": True,
        "schema_valid": True,
        "no_duplicates": True,
        "values_in_range": True
    }
    
    failed_checks = [k for k, v in checks.items() if not v]
    
    if failed_checks:
        raise ValueError(f"Data validation failed: {failed_checks}")
    
    print(f"     ✓ All {len(checks)} validation checks passed")
    
    return {
        "validation_passed": True,
        "validation_checks": checks
    }


def feature_engineering_step(context: Dict) -> Dict:
    """Step 3: Engineer features"""
    print("     🔧 Engineering features...")
    time.sleep(0.8)
    
    num_samples = context.get("num_samples", 0)
    
    # Simulate feature engineering
    features_created = [
        "user_embedding_256d",
        "purchase_history_30d",
        "category_preferences",
        "time_features",
        "interaction_features"
    ]
    
    print(f"     📐 Created {len(features_created)} feature groups")
    
    return {
        "features_path": "/data/features/features_v1.parquet",
        "features_created": features_created,
        "total_features": 512
    }


def data_splitting_step(context: Dict) -> Dict:
    """Step 4: Split data into train/val/test"""
    print("     ✂️ Splitting data...")
    time.sleep(0.3)
    
    num_samples = context.get("num_samples", 10000)
    
    train_size = int(num_samples * 0.7)
    val_size = int(num_samples * 0.15)
    test_size = num_samples - train_size - val_size
    
    print(f"     📊 Train: {train_size:,} | Val: {val_size:,} | Test: {test_size:,}")
    
    return {
        "train_size": train_size,
        "val_size": val_size,
        "test_size": test_size,
        "split_ratio": "70/15/15"
    }


def model_training_step(context: Dict) -> Dict:
    """Step 5: Train the model"""
    print("     🧠 Training model...")
    
    train_size = context.get("train_size", 10000)
    
    # Simulate training epochs
    epochs = 5
    for epoch in range(epochs):
        time.sleep(0.3)
        loss = 0.5 / (epoch + 1) + random.uniform(0, 0.1)
        print(f"        Epoch {epoch+1}/{epochs}: loss = {loss:.4f}")
    
    # Simulate model metrics
    train_accuracy = random.uniform(0.92, 0.98)
    val_accuracy = random.uniform(0.88, 0.94)
    
    print(f"     📈 Train accuracy: {train_accuracy:.4f}")
    print(f"     📈 Val accuracy: {val_accuracy:.4f}")
    
    return {
        "model_path": "/models/model_v1.pt",
        "train_accuracy": train_accuracy,
        "val_accuracy": val_accuracy,
        "epochs_trained": epochs,
        "model_version": "v1.0.0"
    }


def model_evaluation_step(context: Dict) -> Dict:
    """Step 6: Evaluate model on test set"""
    print("     📊 Evaluating model...")
    time.sleep(0.5)
    
    val_accuracy = context.get("val_accuracy", 0.9)
    
    # Simulate test evaluation
    test_accuracy = val_accuracy - random.uniform(0.01, 0.03)
    precision = random.uniform(0.88, 0.95)
    recall = random.uniform(0.85, 0.93)
    f1_score = 2 * (precision * recall) / (precision + recall)
    
    print(f"     📈 Test Accuracy: {test_accuracy:.4f}")
    print(f"     📈 Precision: {precision:.4f}")
    print(f"     📈 Recall: {recall:.4f}")
    print(f"     📈 F1 Score: {f1_score:.4f}")
    
    # Check if model meets threshold
    min_accuracy = 0.85
    if test_accuracy < min_accuracy:
        raise ValueError(f"Model accuracy {test_accuracy:.4f} below threshold {min_accuracy}")
    
    return {
        "test_accuracy": test_accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
        "evaluation_passed": True
    }


def model_registration_step(context: Dict) -> Dict:
    """Step 7: Register model in model registry"""
    print("     📝 Registering model...")
    time.sleep(0.3)
    
    model_version = context.get("model_version", "v1.0.0")
    test_accuracy = context.get("test_accuracy", 0.9)
    
    # Simulate model registration
    model_id = f"model_{random.randint(1000, 9999)}"
    
    print(f"     📦 Registered as: {model_id}")
    print(f"     📊 Metrics logged to MLflow")
    
    return {
        "registered_model_id": model_id,
        "registry": "mlflow",
        "stage": "staging"
    }


def model_deployment_step(context: Dict) -> Dict:
    """Step 8: Deploy model to production"""
    print("     🚀 Deploying model...")
    time.sleep(0.5)
    
    model_id = context.get("registered_model_id", "model_0000")
    test_accuracy = context.get("test_accuracy", 0.9)
    
    # Simulate deployment
    endpoint = f"https://api.example.com/models/{model_id}/predict"
    
    print(f"     🌐 Deployed to: {endpoint}")
    print(f"     ✓ Health check passed")
    print(f"     ✓ Smoke tests passed")
    
    return {
        "endpoint": endpoint,
        "deployment_status": "active",
        "deployed_at": datetime.now().isoformat()
    }


def notification_step(context: Dict) -> Dict:
    """Step 9: Send notifications"""
    print("     📧 Sending notifications...")
    time.sleep(0.2)
    
    test_accuracy = context.get("test_accuracy", 0)
    endpoint = context.get("endpoint", "")
    
    # Simulate notification
    notification = {
        "channel": "slack",
        "message": f"✅ Model deployed successfully!\n"
                   f"   Accuracy: {test_accuracy:.4f}\n"
                   f"   Endpoint: {endpoint}"
    }
    
    print(f"     📨 Slack notification sent")
    
    return {
        "notification_sent": True,
        "notification_details": notification
    }


def create_ml_training_pipeline() -> MLPipeline:
    """Create a complete ML training pipeline"""
    pipeline = MLPipeline("ML Model Training Pipeline")
    
    # Add steps with dependencies
    pipeline.add_step(PipelineStep(
        name="data_ingestion",
        function=data_ingestion_step,
        description="Load raw data from source"
    ))
    
    pipeline.add_step(PipelineStep(
        name="data_validation",
        function=data_validation_step,
        dependencies=["data_ingestion"],
        description="Validate data quality"
    ))
    
    pipeline.add_step(PipelineStep(
        name="feature_engineering",
        function=feature_engineering_step,
        dependencies=["data_validation"],
        description="Create ML features"
    ))
    
    pipeline.add_step(PipelineStep(
        name="data_splitting",
        function=data_splitting_step,
        dependencies=["feature_engineering"],
        description="Split into train/val/test"
    ))
    
    pipeline.add_step(PipelineStep(
        name="model_training",
        function=model_training_step,
        dependencies=["data_splitting"],
        description="Train the model"
    ))
    
    pipeline.add_step(PipelineStep(
        name="model_evaluation",
        function=model_evaluation_step,
        dependencies=["model_training"],
        description="Evaluate on test set"
    ))
    
    pipeline.add_step(PipelineStep(
        name="model_registration",
        function=model_registration_step,
        dependencies=["model_evaluation"],
        description="Register in model registry"
    ))
    
    pipeline.add_step(PipelineStep(
        name="model_deployment",
        function=model_deployment_step,
        dependencies=["model_registration"],
        description="Deploy to production"
    ))
    
    pipeline.add_step(PipelineStep(
        name="notification",
        function=notification_step,
        dependencies=["model_deployment"],
        description="Send completion notification"
    ))
    
    return pipeline


def demo_parallel_pipeline():
    """Demo: Pipeline with parallel steps"""
    print("\n" + "=" * 60)
    print("🔀 DEMO: Pipeline with Parallel Steps")
    print("=" * 60)
    
    pipeline = MLPipeline("Parallel Processing Pipeline")
    
    # Data ingestion (no dependencies)
    pipeline.add_step(PipelineStep(
        name="ingest_user_data",
        function=lambda ctx: {"user_data": "loaded"} or time.sleep(0.3),
        description="Load user data"
    ))
    
    pipeline.add_step(PipelineStep(
        name="ingest_product_data",
        function=lambda ctx: {"product_data": "loaded"} or time.sleep(0.3),
        description="Load product data"
    ))
    
    pipeline.add_step(PipelineStep(
        name="ingest_transaction_data",
        function=lambda ctx: {"transaction_data": "loaded"} or time.sleep(0.3),
        description="Load transaction data"
    ))
    
    # Feature engineering (depends on data)
    pipeline.add_step(PipelineStep(
        name="user_features",
        function=lambda ctx: {"user_features": "computed"} or time.sleep(0.2),
        dependencies=["ingest_user_data"],
        description="Compute user features"
    ))
    
    pipeline.add_step(PipelineStep(
        name="product_features",
        function=lambda ctx: {"product_features": "computed"} or time.sleep(0.2),
        dependencies=["ingest_product_data"],
        description="Compute product features"
    ))
    
    # Join features (depends on all features)
    pipeline.add_step(PipelineStep(
        name="join_features",
        function=lambda ctx: {"joined_features": "ready"} or time.sleep(0.2),
        dependencies=["user_features", "product_features", "ingest_transaction_data"],
        description="Join all features"
    ))
    
    # Train model
    pipeline.add_step(PipelineStep(
        name="train_model",
        function=lambda ctx: {"model": "trained"} or time.sleep(0.5),
        dependencies=["join_features"],
        description="Train recommendation model"
    ))
    
    pipeline.run()


def demo_failure_handling():
    """Demo: Pipeline failure handling"""
    print("\n" + "=" * 60)
    print("💥 DEMO: Failure Handling")
    print("=" * 60)
    
    def failing_step(ctx):
        time.sleep(0.2)
        raise ValueError("Simulated failure!")
    
    pipeline = MLPipeline("Failure Demo Pipeline")
    
    pipeline.add_step(PipelineStep(
        name="step_1",
        function=lambda ctx: {"step1": "done"} or time.sleep(0.2),
        description="First step (succeeds)"
    ))
    
    pipeline.add_step(PipelineStep(
        name="step_2_fails",
        function=failing_step,
        dependencies=["step_1"],
        description="Second step (fails)"
    ))
    
    pipeline.add_step(PipelineStep(
        name="step_3_skipped",
        function=lambda ctx: {"step3": "done"},
        dependencies=["step_2_fails"],
        description="Third step (will be skipped)"
    ))
    
    pipeline.run()


def demo_retry_mechanism():
    """Demo: Step retry mechanism"""
    print("\n" + "=" * 60)
    print("🔄 DEMO: Retry Mechanism")
    print("=" * 60)
    
    attempt_count = {"count": 0}
    
    def flaky_step(ctx):
        attempt_count["count"] += 1
        time.sleep(0.2)
        if attempt_count["count"] < 3:
            raise ValueError(f"Flaky failure (attempt {attempt_count['count']})")
        return {"flaky_result": "success after retries"}
    
    pipeline = MLPipeline("Retry Demo Pipeline")
    
    pipeline.add_step(PipelineStep(
        name="flaky_step",
        function=flaky_step,
        retries=3,  # Will retry up to 3 times
        description="Step that fails twice then succeeds"
    ))
    
    pipeline.run()


def main():
    """Main demo function"""
    print("=" * 70)
    print("🔄 ML PIPELINE ORCHESTRATION DEMO")
    print("=" * 70)
    
    # Demo 1: Full ML Training Pipeline
    print("\n" + "🎯" * 35)
    print("DEMO 1: Complete ML Training Pipeline")
    print("🎯" * 35)
    
    pipeline = create_ml_training_pipeline()
    results = pipeline.run()
    
    # Demo 2: Parallel Pipeline
    demo_parallel_pipeline()
    
    # Demo 3: Failure Handling
    demo_failure_handling()
    
    # Demo 4: Retry Mechanism
    demo_retry_mechanism()
    
    print("\n" + "=" * 70)
    print("✅ ALL DEMOS COMPLETE!")
    print("=" * 70)
    
    print("\n🎯 Key Takeaways:")
    print("  1. Pipelines automate ML workflows end-to-end")
    print("  2. Dependencies ensure correct execution order")
    print("  3. Failures are handled gracefully")
    print("  4. Retries help with flaky steps")
    print("  5. Context passing shares data between steps")
    
    print("\n🏭 Popular Pipeline Orchestrators:")
    print("  - Apache Airflow")
    print("  - Kubeflow Pipelines")
    print("  - MLflow Pipelines")
    print("  - Prefect")
    print("  - Dagster")
    print("  - AWS Step Functions")


if __name__ == "__main__":
    main()