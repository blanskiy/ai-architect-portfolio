"""
Distributed Inference System
Week 4 Day 17: Scale ML inference across multiple workers
"""

import threading
import queue
import time
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future
import statistics


class LoadBalancerStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    RANDOM = "random"


class WorkerStatus(Enum):
    """Worker health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class InferenceRequest:
    """Represents an inference request"""
    request_id: str
    payload: Any
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 0  # Higher = more priority
    timeout_ms: int = 5000


@dataclass
class InferenceResult:
    """Represents an inference result"""
    request_id: str
    result: Any
    worker_id: str
    latency_ms: float
    success: bool
    error: Optional[str] = None


@dataclass
class WorkerStats:
    """Statistics for a worker"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    active_connections: int = 0
    last_health_check: Optional[datetime] = None
    
    @property
    def avg_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100


class InferenceWorker:
    """
    Simulates a model inference worker.
    In production, this would be a separate process/container.
    """
    
    def __init__(self, worker_id: str, model_name: str = "ResNet-50",
                 capacity: int = 10, base_latency_ms: float = 100.0):
        self.worker_id = worker_id
        self.model_name = model_name
        self.capacity = capacity  # Max concurrent requests
        self.base_latency_ms = base_latency_ms
        self.stats = WorkerStats()
        self.status = WorkerStatus.HEALTHY
        self._lock = threading.Lock()
        
        print(f"  ✅ Worker {worker_id} initialized (capacity: {capacity})")
    
    def process_request(self, request: InferenceRequest) -> InferenceResult:
        """Process an inference request"""
        start_time = time.perf_counter()
        
        with self._lock:
            self.stats.active_connections += 1
        
        try:
            # Simulate inference with variable latency
            latency_variation = random.uniform(-20, 30)
            load_factor = 1 + (self.stats.active_connections / self.capacity) * 0.5
            actual_latency = (self.base_latency_ms + latency_variation) * load_factor
            
            time.sleep(actual_latency / 1000)
            
            # Simulate occasional failures (1% rate)
            if random.random() < 0.01:
                raise Exception("Simulated inference error")
            
            # Simulate prediction result
            result = {
                "predictions": [
                    {"class": "Samoyed", "confidence": random.uniform(0.85, 0.95)},
                    {"class": "Pomeranian", "confidence": random.uniform(0.02, 0.08)}
                ],
                "model": self.model_name,
                "worker": self.worker_id
            }
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            with self._lock:
                self.stats.total_requests += 1
                self.stats.successful_requests += 1
                self.stats.total_latency_ms += elapsed_ms
            
            return InferenceResult(
                request_id=request.request_id,
                result=result,
                worker_id=self.worker_id,
                latency_ms=elapsed_ms,
                success=True
            )
            
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            with self._lock:
                self.stats.total_requests += 1
                self.stats.failed_requests += 1
                self.stats.total_latency_ms += elapsed_ms
            
            return InferenceResult(
                request_id=request.request_id,
                result=None,
                worker_id=self.worker_id,
                latency_ms=elapsed_ms,
                success=False,
                error=str(e)
            )
        
        finally:
            with self._lock:
                self.stats.active_connections -= 1
    
    def health_check(self) -> WorkerStatus:
        """Check worker health"""
        self.stats.last_health_check = datetime.now()
        
        # Degraded if high error rate
        if self.stats.success_rate < 95:
            self.status = WorkerStatus.DEGRADED
        # Unhealthy if very high error rate
        elif self.stats.success_rate < 80:
            self.status = WorkerStatus.UNHEALTHY
        else:
            self.status = WorkerStatus.HEALTHY
        
        return self.status


class LoadBalancer:
    """
    Distributes requests across workers using configurable strategies.
    """
    
    def __init__(self, strategy: LoadBalancerStrategy = LoadBalancerStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self.workers: List[InferenceWorker] = []
        self.worker_weights: Dict[str, float] = {}
        self._round_robin_index = 0
        self._lock = threading.Lock()
        
    def register_worker(self, worker: InferenceWorker, weight: float = 1.0):
        """Register a worker with the load balancer"""
        self.workers.append(worker)
        self.worker_weights[worker.worker_id] = weight
        
    def remove_worker(self, worker_id: str):
        """Remove a worker from the pool"""
        self.workers = [w for w in self.workers if w.worker_id != worker_id]
        if worker_id in self.worker_weights:
            del self.worker_weights[worker_id]
    
    def get_healthy_workers(self) -> List[InferenceWorker]:
        """Get list of healthy workers"""
        return [w for w in self.workers if w.status != WorkerStatus.UNHEALTHY]
    
    def select_worker(self) -> Optional[InferenceWorker]:
        """Select a worker based on the configured strategy"""
        healthy_workers = self.get_healthy_workers()
        
        if not healthy_workers:
            return None
        
        if self.strategy == LoadBalancerStrategy.ROUND_ROBIN:
            return self._round_robin_select(healthy_workers)
        elif self.strategy == LoadBalancerStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(healthy_workers)
        elif self.strategy == LoadBalancerStrategy.WEIGHTED:
            return self._weighted_select(healthy_workers)
        elif self.strategy == LoadBalancerStrategy.RANDOM:
            return self._random_select(healthy_workers)
        
        return healthy_workers[0]
    
    def _round_robin_select(self, workers: List[InferenceWorker]) -> InferenceWorker:
        """Round-robin selection"""
        with self._lock:
            worker = workers[self._round_robin_index % len(workers)]
            self._round_robin_index += 1
        return worker
    
    def _least_connections_select(self, workers: List[InferenceWorker]) -> InferenceWorker:
        """Select worker with least active connections"""
        return min(workers, key=lambda w: w.stats.active_connections)
    
    def _weighted_select(self, workers: List[InferenceWorker]) -> InferenceWorker:
        """Weighted random selection based on worker weights"""
        weights = [self.worker_weights.get(w.worker_id, 1.0) for w in workers]
        total_weight = sum(weights)
        rand = random.uniform(0, total_weight)
        
        cumulative = 0
        for i, weight in enumerate(weights):
            cumulative += weight
            if rand <= cumulative:
                return workers[i]
        
        return workers[-1]
    
    def _random_select(self, workers: List[InferenceWorker]) -> InferenceWorker:
        """Random selection"""
        return random.choice(workers)


class DistributedInferenceSystem:
    """
    Main distributed inference system that manages workers and request processing.
    """
    
    def __init__(self, num_workers: int = 4,
                 strategy: LoadBalancerStrategy = LoadBalancerStrategy.ROUND_ROBIN,
                 max_queue_size: int = 1000):
        
        print(f"\n{'='*60}")
        print("🚀 Initializing Distributed Inference System")
        print(f"{'='*60}")
        print(f"  Workers: {num_workers}")
        print(f"  Strategy: {strategy.value}")
        print(f"  Queue Size: {max_queue_size}")
        
        self.load_balancer = LoadBalancer(strategy)
        self.request_queue = queue.PriorityQueue(maxsize=max_queue_size)
        self.results: Dict[str, InferenceResult] = {}
        self.executor = ThreadPoolExecutor(max_workers=num_workers * 2)
        self._lock = threading.Lock()
        self._shutdown = False
        
        # Initialize workers
        print("\n  Initializing workers...")
        for i in range(num_workers):
            worker = InferenceWorker(
                worker_id=f"worker-{i+1}",
                capacity=10,
                base_latency_ms=80 + random.uniform(-10, 10)
            )
            self.load_balancer.register_worker(worker)
        
        print(f"\n{'='*60}")
        print("✅ System initialized!")
        print(f"{'='*60}\n")
    
    def submit_request(self, request: InferenceRequest) -> Future:
        """Submit a request for processing"""
        # Priority queue uses (priority, item) - lower number = higher priority
        # We negate priority so higher priority requests are processed first
        future = self.executor.submit(self._process_request, request)
        return future
    
    def _process_request(self, request: InferenceRequest) -> InferenceResult:
        """Process a single request"""
        worker = self.load_balancer.select_worker()
        
        if worker is None:
            return InferenceResult(
                request_id=request.request_id,
                result=None,
                worker_id="none",
                latency_ms=0,
                success=False,
                error="No healthy workers available"
            )
        
        result = worker.process_request(request)
        
        with self._lock:
            self.results[request.request_id] = result
        
        return result
    
    def submit_batch(self, requests: List[InferenceRequest]) -> List[Future]:
        """Submit a batch of requests"""
        futures = []
        for request in requests:
            future = self.submit_request(request)
            futures.append(future)
        return futures
    
    def get_system_stats(self) -> Dict:
        """Get aggregated system statistics"""
        total_requests = 0
        total_successes = 0
        total_failures = 0
        total_latency = 0.0
        active_connections = 0
        
        worker_stats = []
        
        for worker in self.load_balancer.workers:
            stats = worker.stats
            total_requests += stats.total_requests
            total_successes += stats.successful_requests
            total_failures += stats.failed_requests
            total_latency += stats.total_latency_ms
            active_connections += stats.active_connections
            
            worker_stats.append({
                "worker_id": worker.worker_id,
                "status": worker.status.value,
                "requests": stats.total_requests,
                "success_rate": f"{stats.success_rate:.1f}%",
                "avg_latency_ms": f"{stats.avg_latency_ms:.2f}",
                "active_connections": stats.active_connections
            })
        
        return {
            "total_workers": len(self.load_balancer.workers),
            "healthy_workers": len(self.load_balancer.get_healthy_workers()),
            "total_requests": total_requests,
            "successful_requests": total_successes,
            "failed_requests": total_failures,
            "overall_success_rate": f"{(total_successes/total_requests*100) if total_requests > 0 else 0:.1f}%",
            "avg_latency_ms": f"{(total_latency/total_requests) if total_requests > 0 else 0:.2f}",
            "active_connections": active_connections,
            "workers": worker_stats
        }
    
    def print_stats(self):
        """Print formatted statistics"""
        stats = self.get_system_stats()
        
        print(f"\n{'='*70}")
        print("📊 DISTRIBUTED INFERENCE SYSTEM STATS")
        print(f"{'='*70}")
        
        print(f"\nSystem Overview:")
        print(f"  Workers: {stats['healthy_workers']}/{stats['total_workers']} healthy")
        print(f"  Total Requests: {stats['total_requests']}")
        print(f"  Success Rate: {stats['overall_success_rate']}")
        print(f"  Avg Latency: {stats['avg_latency_ms']} ms")
        print(f"  Active Connections: {stats['active_connections']}")
        
        print(f"\n{'Worker':<15} {'Status':<12} {'Requests':<10} {'Success':<10} {'Latency':<12}")
        print("-" * 70)
        
        for worker in stats['workers']:
            status_icon = "✅" if worker['status'] == 'healthy' else "⚠️" if worker['status'] == 'degraded' else "❌"
            print(f"{status_icon} {worker['worker_id']:<12} {worker['status']:<12} "
                  f"{worker['requests']:<10} {worker['success_rate']:<10} {worker['avg_latency_ms']:<12}")
        
        print(f"{'='*70}\n")
    
    def shutdown(self):
        """Shutdown the system"""
        self._shutdown = True
        self.executor.shutdown(wait=True)
        print("🛑 System shutdown complete")


def benchmark_single_vs_distributed():
    """Compare single worker vs distributed inference"""
    print("\n" + "=" * 70)
    print("📊 BENCHMARK: Single Worker vs Distributed")
    print("=" * 70)
    
    num_requests = 100
    
    # Single worker benchmark
    print("\n▶ Single Worker Test...")
    single_worker = InferenceWorker("single", capacity=10, base_latency_ms=100)
    
    single_start = time.perf_counter()
    single_latencies = []
    
    for i in range(num_requests):
        request = InferenceRequest(request_id=f"single-{i}", payload={"image": "test.jpg"})
        result = single_worker.process_request(request)
        single_latencies.append(result.latency_ms)
        if (i + 1) % 25 == 0:
            print(f"    Processed {i + 1}/{num_requests}")
    
    single_total_time = (time.perf_counter() - single_start) * 1000
    
    # Distributed benchmark
    print("\n▶ Distributed (4 Workers) Test...")
    system = DistributedInferenceSystem(
        num_workers=4,
        strategy=LoadBalancerStrategy.LEAST_CONNECTIONS
    )
    
    distributed_start = time.perf_counter()
    
    requests = [
        InferenceRequest(request_id=f"dist-{i}", payload={"image": "test.jpg"})
        for i in range(num_requests)
    ]
    
    futures = system.submit_batch(requests)
    
    distributed_latencies = []
    for i, future in enumerate(futures):
        result = future.result()
        distributed_latencies.append(result.latency_ms)
        if (i + 1) % 25 == 0:
            print(f"    Processed {i + 1}/{num_requests}")
    
    distributed_total_time = (time.perf_counter() - distributed_start) * 1000
    
    # Print results
    print("\n" + "=" * 70)
    print("📈 BENCHMARK RESULTS")
    print("=" * 70)
    
    print(f"\n{'Metric':<25} {'Single Worker':<20} {'Distributed (4)':<20}")
    print("-" * 70)
    
    single_avg = statistics.mean(single_latencies)
    single_p99 = sorted(single_latencies)[int(len(single_latencies) * 0.99)]
    single_throughput = num_requests / (single_total_time / 1000)
    
    dist_avg = statistics.mean(distributed_latencies)
    dist_p99 = sorted(distributed_latencies)[int(len(distributed_latencies) * 0.99)]
    dist_throughput = num_requests / (distributed_total_time / 1000)
    
    speedup = single_total_time / distributed_total_time
    throughput_gain = dist_throughput / single_throughput
    
    print(f"{'Total Time (ms)':<25} {single_total_time:>15.2f}     {distributed_total_time:>15.2f}")
    print(f"{'Avg Latency (ms)':<25} {single_avg:>15.2f}     {dist_avg:>15.2f}")
    print(f"{'P99 Latency (ms)':<25} {single_p99:>15.2f}     {dist_p99:>15.2f}")
    print(f"{'Throughput (RPS)':<25} {single_throughput:>15.2f}     {dist_throughput:>15.2f}")
    
    print("-" * 70)
    print(f"\n🏆 Distributed is {speedup:.2f}x faster overall")
    print(f"🏆 Throughput improved by {throughput_gain:.2f}x")
    
    system.print_stats()
    system.shutdown()


def demo_load_balancing_strategies():
    """Demonstrate different load balancing strategies"""
    print("\n" + "=" * 70)
    print("🔄 LOAD BALANCING STRATEGIES DEMO")
    print("=" * 70)
    
    strategies = [
        LoadBalancerStrategy.ROUND_ROBIN,
        LoadBalancerStrategy.LEAST_CONNECTIONS,
        LoadBalancerStrategy.RANDOM
    ]
    
    num_requests = 50
    
    for strategy in strategies:
        print(f"\n▶ Testing {strategy.value.upper()}...")
        
        system = DistributedInferenceSystem(
            num_workers=3,
            strategy=strategy
        )
        
        requests = [
            InferenceRequest(request_id=f"{strategy.value}-{i}", payload={})
            for i in range(num_requests)
        ]
        
        futures = system.submit_batch(requests)
        for future in futures:
            _ = future.result()
        
        # Show distribution
        stats = system.get_system_stats()
        print(f"  Request Distribution:")
        for worker in stats['workers']:
            bar = "█" * (worker['requests'] // 2)
            print(f"    {worker['worker_id']}: {worker['requests']:>3} requests {bar}")
        
        system.shutdown()


def demo_fault_tolerance():
    """Demonstrate fault tolerance with worker failures"""
    print("\n" + "=" * 70)
    print("🛡️ FAULT TOLERANCE DEMO")
    print("=" * 70)
    
    system = DistributedInferenceSystem(
        num_workers=4,
        strategy=LoadBalancerStrategy.LEAST_CONNECTIONS
    )
    
    print("\n▶ Phase 1: All workers healthy")
    requests = [InferenceRequest(request_id=f"ft-1-{i}", payload={}) for i in range(20)]
    futures = system.submit_batch(requests)
    for f in futures:
        f.result()
    system.print_stats()
    
    # Simulate worker failure
    print("\n⚠️ Simulating Worker-2 failure...")
    system.load_balancer.workers[1].status = WorkerStatus.UNHEALTHY
    
    print("\n▶ Phase 2: One worker unhealthy (system continues)")
    requests = [InferenceRequest(request_id=f"ft-2-{i}", payload={}) for i in range(20)]
    futures = system.submit_batch(requests)
    for f in futures:
        f.result()
    system.print_stats()
    
    # Recover worker
    print("\n✅ Worker-2 recovered!")
    system.load_balancer.workers[1].status = WorkerStatus.HEALTHY
    
    print("\n▶ Phase 3: All workers healthy again")
    requests = [InferenceRequest(request_id=f"ft-3-{i}", payload={}) for i in range(20)]
    futures = system.submit_batch(requests)
    for f in futures:
        f.result()
    system.print_stats()
    
    system.shutdown()


def main():
    """Main demo function"""
    print("=" * 70)
    print("🌐 DISTRIBUTED INFERENCE SYSTEM DEMO")
    print("=" * 70)
    
    # Run benchmarks
    benchmark_single_vs_distributed()
    
    # Demo load balancing
    demo_load_balancing_strategies()
    
    # Demo fault tolerance
    demo_fault_tolerance()
    
    print("\n" + "=" * 70)
    print("✅ ALL DEMOS COMPLETE!")
    print("=" * 70)
    
    print("\n🎯 Key Takeaways:")
    print("  1. Distributed inference scales horizontally")
    print("  2. Load balancing ensures even distribution")
    print("  3. Least-connections adapts to variable latencies")
    print("  4. Fault tolerance keeps system running during failures")
    print("  5. 4 workers can provide ~4x throughput improvement")


if __name__ == "__main__":
    main()