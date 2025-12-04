"""
A/B Testing and Canary Deployment Module
Week 3 Day 14: Traffic Splitting
"""

import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import json


@dataclass
class ModelVersion:
    """Represents a model version in the deployment"""
    name: str
    version: str
    weight: float  # Traffic percentage (0.0 to 1.0)
    endpoint: str
    is_canary: bool = False
    metrics: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        self.metrics = {
            "requests": 0,
            "successes": 0,
            "failures": 0,
            "total_latency_ms": 0.0,
            "predictions": []
        }


class ABTestManager:
    """
    Manages A/B testing and canary deployments for ML models.
    Routes traffic based on configured weights.
    """
    
    def __init__(self):
        self.versions: Dict[str, ModelVersion] = {}
        self.experiment_name: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.request_log: List[Dict] = []
        
    def setup_experiment(self, name: str, versions: List[ModelVersion]):
        """
        Setup an A/B test or canary deployment.
        
        Args:
            name: Experiment name
            versions: List of ModelVersion objects with weights
        """
        # Validate weights sum to 1.0
        total_weight = sum(v.weight for v in versions)
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")
        
        self.experiment_name = name
        self.start_time = datetime.now()
        self.versions = {v.name: v for v in versions}
        
        print(f"\n{'='*60}")
        print(f"Experiment: {name}")
        print(f"Started: {self.start_time}")
        print(f"{'='*60}")
        for v in versions:
            canary_tag = " [CANARY]" if v.is_canary else ""
            print(f"  {v.name} (v{v.version}): {v.weight*100:.1f}% traffic{canary_tag}")
        print(f"{'='*60}\n")
        
    def route_request(self) -> ModelVersion:
        """
        Route a request to a model version based on weights.
        Returns the selected ModelVersion.
        """
        if not self.versions:
            raise RuntimeError("No experiment configured. Call setup_experiment first.")
        
        # Weighted random selection
        rand = random.random()
        cumulative = 0.0
        
        for version in self.versions.values():
            cumulative += version.weight
            if rand <= cumulative:
                return version
        
        # Fallback to last version
        return list(self.versions.values())[-1]
    
    def record_result(self, version: ModelVersion, latency_ms: float, 
                      success: bool, prediction: Optional[Dict] = None):
        """Record the result of a request for analysis."""
        version.metrics["requests"] += 1
        version.metrics["total_latency_ms"] += latency_ms
        
        if success:
            version.metrics["successes"] += 1
        else:
            version.metrics["failures"] += 1
            
        if prediction:
            version.metrics["predictions"].append(prediction)
        
        # Log request
        self.request_log.append({
            "timestamp": datetime.now().isoformat(),
            "version": version.name,
            "latency_ms": latency_ms,
            "success": success
        })
    
    def get_metrics(self) -> Dict:
        """Get current metrics for all versions."""
        results = {}
        
        for name, version in self.versions.items():
            requests = version.metrics["requests"]
            if requests > 0:
                avg_latency = version.metrics["total_latency_ms"] / requests
                success_rate = version.metrics["successes"] / requests * 100
            else:
                avg_latency = 0
                success_rate = 0
                
            results[name] = {
                "version": version.version,
                "is_canary": version.is_canary,
                "weight": version.weight * 100,
                "requests": requests,
                "successes": version.metrics["successes"],
                "failures": version.metrics["failures"],
                "avg_latency_ms": round(avg_latency, 2),
                "success_rate": round(success_rate, 2)
            }
        
        return results
    
    def print_report(self):
        """Print a formatted report of the experiment."""
        metrics = self.get_metrics()
        
        print(f"\n{'='*70}")
        print(f"A/B TEST REPORT: {self.experiment_name}")
        print(f"Duration: {datetime.now() - self.start_time}")
        print(f"{'='*70}")
        
        print(f"\n{'Version':<20} {'Traffic':<10} {'Requests':<10} {'Success':<10} {'Latency':<15}")
        print(f"{'-'*70}")
        
        for name, m in metrics.items():
            canary = "🐤" if m["is_canary"] else "  "
            print(f"{canary}{name:<18} {m['weight']:.1f}%      {m['requests']:<10} {m['success_rate']:.1f}%     {m['avg_latency_ms']:.2f}ms")
        
        print(f"\n{'='*70}")
        
        # Determine winner
        if len(metrics) == 2:
            versions = list(metrics.items())
            v1_name, v1_metrics = versions[0]
            v2_name, v2_metrics = versions[1]
            
            if v1_metrics["requests"] > 0 and v2_metrics["requests"] > 0:
                # Compare latency
                if v2_metrics["avg_latency_ms"] < v1_metrics["avg_latency_ms"]:
                    improvement = (1 - v2_metrics["avg_latency_ms"] / v1_metrics["avg_latency_ms"]) * 100
                    print(f"📊 {v2_name} is {improvement:.1f}% faster than {v1_name}")
                else:
                    slower = (v2_metrics["avg_latency_ms"] / v1_metrics["avg_latency_ms"] - 1) * 100
                    print(f"📊 {v2_name} is {slower:.1f}% slower than {v1_name}")
                
                # Compare success rate
                if v2_metrics["success_rate"] >= v1_metrics["success_rate"]:
                    print(f"✅ {v2_name} success rate: {v2_metrics['success_rate']:.1f}% (same or better)")
                else:
                    print(f"⚠️  {v2_name} success rate: {v2_metrics['success_rate']:.1f}% (worse)")
        
        print(f"{'='*70}\n")
    
    def update_weights(self, new_weights: Dict[str, float]):
        """
        Update traffic weights dynamically.
        Used for gradual canary rollout.
        """
        total = sum(new_weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        
        for name, weight in new_weights.items():
            if name in self.versions:
                old_weight = self.versions[name].weight
                self.versions[name].weight = weight
                print(f"Updated {name}: {old_weight*100:.1f}% → {weight*100:.1f}%")
    
    def promote_canary(self):
        """Promote canary to 100% traffic (full rollout)."""
        canary = None
        for v in self.versions.values():
            if v.is_canary:
                canary = v
                break
        
        if canary:
            print(f"\n🚀 Promoting canary {canary.name} to 100% traffic!")
            for v in self.versions.values():
                if v.is_canary:
                    v.weight = 1.0
                else:
                    v.weight = 0.0
            print("✅ Canary promoted successfully!")
        else:
            print("No canary version found.")
    
    def rollback(self):
        """Rollback: Send 100% traffic to non-canary version."""
        print("\n⚠️  ROLLBACK INITIATED!")
        for v in self.versions.values():
            if v.is_canary:
                v.weight = 0.0
            else:
                v.weight = 1.0
        print("✅ Rolled back to stable version.")


def simulate_request(version: ModelVersion) -> tuple:
    """Simulate a model inference request."""
    # Simulate different latencies for different versions
    base_latency = 100  # ms
    
    if "v2" in version.version or "onnx" in version.name.lower():
        # v2/ONNX is faster
        latency = base_latency * 0.7 + random.uniform(-10, 10)
    else:
        # v1 baseline
        latency = base_latency + random.uniform(-15, 15)
    
    # Simulate occasional failures (2% for v1, 1% for v2)
    failure_rate = 0.01 if "v2" in version.version else 0.02
    success = random.random() > failure_rate
    
    # Simulate prediction
    prediction = {
        "class": "Samoyed",
        "confidence": round(random.uniform(0.85, 0.95), 4)
    }
    
    time.sleep(latency / 1000)  # Simulate actual latency
    
    return latency, success, prediction


def demo_canary_deployment():
    """Demo: Canary Deployment (10% new version)"""
    print("\n" + "🐤"*30)
    print("DEMO: Canary Deployment")
    print("🐤"*30)
    
    manager = ABTestManager()
    
    # Setup canary: 90% v1, 10% v2 (canary)
    manager.setup_experiment(
        name="ResNet50 Canary Rollout",
        versions=[
            ModelVersion(
                name="resnet-stable",
                version="v1.0",
                weight=0.9,
                endpoint="http://localhost:8000/predict",
                is_canary=False
            ),
            ModelVersion(
                name="resnet-canary",
                version="v2.0",
                weight=0.1,
                endpoint="http://localhost:8001/predict",
                is_canary=True
            )
        ]
    )
    
    # Simulate 100 requests
    print("Simulating 100 requests...")
    for i in range(100):
        version = manager.route_request()
        latency, success, prediction = simulate_request(version)
        manager.record_result(version, latency, success, prediction)
        
        if (i + 1) % 25 == 0:
            print(f"  Processed {i + 1} requests...")
    
    manager.print_report()
    
    return manager


def demo_ab_test():
    """Demo: A/B Test (50/50 split)"""
    print("\n" + "🔬"*30)
    print("DEMO: A/B Test (50/50)")
    print("🔬"*30)
    
    manager = ABTestManager()
    
    # Setup A/B test: 50% each
    manager.setup_experiment(
        name="PyTorch vs ONNX Comparison",
        versions=[
            ModelVersion(
                name="pytorch-baseline",
                version="v1.0",
                weight=0.5,
                endpoint="http://localhost:8000/predict"
            ),
            ModelVersion(
                name="onnx-optimized",
                version="v2.0",
                weight=0.5,
                endpoint="http://localhost:8001/predict"
            )
        ]
    )
    
    # Simulate 100 requests
    print("Simulating 100 requests...")
    for i in range(100):
        version = manager.route_request()
        latency, success, prediction = simulate_request(version)
        manager.record_result(version, latency, success, prediction)
        
        if (i + 1) % 25 == 0:
            print(f"  Processed {i + 1} requests...")
    
    manager.print_report()
    
    return manager


def demo_gradual_rollout():
    """Demo: Gradual Canary Rollout (10% → 50% → 100%)"""
    print("\n" + "📈"*30)
    print("DEMO: Gradual Canary Rollout")
    print("📈"*30)
    
    manager = ABTestManager()
    
    # Start with 10% canary
    manager.setup_experiment(
        name="Gradual Rollout Demo",
        versions=[
            ModelVersion(
                name="stable",
                version="v1.0",
                weight=0.9,
                endpoint="http://localhost:8000/predict"
            ),
            ModelVersion(
                name="canary",
                version="v2.0",
                weight=0.1,
                endpoint="http://localhost:8001/predict",
                is_canary=True
            )
        ]
    )
    
    # Phase 1: 10% canary
    print("\n📍 Phase 1: 10% canary traffic")
    for _ in range(50):
        version = manager.route_request()
        latency, success, prediction = simulate_request(version)
        manager.record_result(version, latency, success, prediction)
    manager.print_report()
    
    # Phase 2: Increase to 50%
    print("\n📍 Phase 2: Increasing to 50% canary traffic")
    manager.update_weights({"stable": 0.5, "canary": 0.5})
    for _ in range(50):
        version = manager.route_request()
        latency, success, prediction = simulate_request(version)
        manager.record_result(version, latency, success, prediction)
    manager.print_report()
    
    # Phase 3: Full rollout
    print("\n📍 Phase 3: Full rollout (100% canary)")
    manager.promote_canary()
    for _ in range(50):
        version = manager.route_request()
        latency, success, prediction = simulate_request(version)
        manager.record_result(version, latency, success, prediction)
    manager.print_report()
    
    return manager


if __name__ == "__main__":
    print("="*70)
    print("A/B TESTING & CANARY DEPLOYMENT DEMO")
    print("="*70)
    
    # Run demos
    demo_canary_deployment()
    demo_ab_test()
    demo_gradual_rollout()
    
    print("\n✅ All demos completed!")
    print("\nKey Takeaways:")
    print("  1. Canary: Start with small % of traffic to new version")
    print("  2. A/B Test: Split traffic 50/50 to compare versions")
    print("  3. Gradual Rollout: Increase canary traffic over time")
    print("  4. Rollback: Instantly revert if issues detected")