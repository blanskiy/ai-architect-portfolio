"""
Feature Store Implementation
Week 4 Day 18: Centralized ML Feature Management
"""

import time
import json
import hashlib
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import random
import statistics


class FeatureType(Enum):
    """Types of features"""
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    EMBEDDING = "embedding"
    TIMESTAMP = "timestamp"


@dataclass
class FeatureDefinition:
    """Defines a feature's metadata"""
    name: str
    feature_type: FeatureType
    description: str
    entity: str  # What entity this feature belongs to (user, product, etc.)
    owner: str
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    version: int = 1
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "type": self.feature_type.value,
            "description": self.description,
            "entity": self.entity,
            "owner": self.owner,
            "tags": self.tags,
            "version": self.version
        }


@dataclass
class FeatureValue:
    """A feature value with timestamp"""
    value: Any
    timestamp: datetime
    feature_name: str
    entity_id: str


class OfflineStore:
    """
    Offline feature store for batch training data.
    Stores historical feature values with timestamps.
    """
    
    def __init__(self):
        # Storage: {entity_id: {feature_name: [(timestamp, value), ...]}}
        self._store: Dict[str, Dict[str, List[Tuple[datetime, Any]]]] = {}
        self._lock = threading.Lock()
        
    def write_features(self, entity_id: str, features: Dict[str, Any], 
                       timestamp: datetime = None):
        """Write features for an entity at a specific time"""
        timestamp = timestamp or datetime.now()
        
        with self._lock:
            if entity_id not in self._store:
                self._store[entity_id] = {}
            
            for feature_name, value in features.items():
                if feature_name not in self._store[entity_id]:
                    self._store[entity_id][feature_name] = []
                
                self._store[entity_id][feature_name].append((timestamp, value))
                # Keep sorted by timestamp
                self._store[entity_id][feature_name].sort(key=lambda x: x[0])
    
    def get_features_at_time(self, entity_id: str, feature_names: List[str],
                             point_in_time: datetime) -> Dict[str, Any]:
        """
        Get feature values as they were at a specific point in time.
        This is crucial for training to avoid data leakage!
        """
        result = {}
        
        with self._lock:
            if entity_id not in self._store:
                return {name: None for name in feature_names}
            
            for feature_name in feature_names:
                if feature_name not in self._store[entity_id]:
                    result[feature_name] = None
                    continue
                
                # Find the most recent value before point_in_time
                history = self._store[entity_id][feature_name]
                value = None
                for ts, v in history:
                    if ts <= point_in_time:
                        value = v
                    else:
                        break
                
                result[feature_name] = value
        
        return result
    
    def get_training_dataset(self, entity_ids: List[str], feature_names: List[str],
                             start_time: datetime, end_time: datetime) -> List[Dict]:
        """Generate a training dataset with point-in-time correct features"""
        dataset = []
        
        for entity_id in entity_ids:
            # Get features at end_time for this entity
            features = self.get_features_at_time(entity_id, feature_names, end_time)
            features["entity_id"] = entity_id
            features["timestamp"] = end_time.isoformat()
            dataset.append(features)
        
        return dataset
    
    def get_feature_history(self, entity_id: str, feature_name: str) -> List[Tuple[datetime, Any]]:
        """Get full history of a feature for an entity"""
        with self._lock:
            if entity_id in self._store and feature_name in self._store[entity_id]:
                return self._store[entity_id][feature_name].copy()
        return []


class OnlineStore:
    """
    Online feature store for real-time inference.
    Optimized for low-latency reads of latest feature values.
    """
    
    def __init__(self):
        # Storage: {entity_id: {feature_name: value}}
        self._store: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, Dict[str, datetime]] = {}
        self._lock = threading.Lock()
        self._stats = {
            "reads": 0,
            "writes": 0,
            "cache_hits": 0,
            "total_read_time_ms": 0.0
        }
    
    def write_features(self, entity_id: str, features: Dict[str, Any]):
        """Write latest features for an entity (overwrites previous values)"""
        with self._lock:
            if entity_id not in self._store:
                self._store[entity_id] = {}
                self._timestamps[entity_id] = {}
            
            now = datetime.now()
            for feature_name, value in features.items():
                self._store[entity_id][feature_name] = value
                self._timestamps[entity_id][feature_name] = now
            
            self._stats["writes"] += 1
    
    def get_features(self, entity_id: str, feature_names: List[str]) -> Dict[str, Any]:
        """Get latest feature values for real-time inference"""
        start_time = time.perf_counter()
        
        with self._lock:
            self._stats["reads"] += 1
            
            if entity_id not in self._store:
                return {name: None for name in feature_names}
            
            result = {}
            for feature_name in feature_names:
                result[feature_name] = self._store[entity_id].get(feature_name)
            
            self._stats["total_read_time_ms"] += (time.perf_counter() - start_time) * 1000
            
            return result
    
    def get_stats(self) -> Dict:
        """Get online store statistics"""
        with self._lock:
            avg_read_time = 0
            if self._stats["reads"] > 0:
                avg_read_time = self._stats["total_read_time_ms"] / self._stats["reads"]
            
            return {
                "total_entities": len(self._store),
                "reads": self._stats["reads"],
                "writes": self._stats["writes"],
                "avg_read_time_ms": round(avg_read_time, 4)
            }


class FeatureStore:
    """
    Main Feature Store that manages both online and offline stores.
    """
    
    def __init__(self):
        self.offline_store = OfflineStore()
        self.online_store = OnlineStore()
        self.feature_definitions: Dict[str, FeatureDefinition] = {}
        self._lock = threading.Lock()
        
        print("🏪 Feature Store initialized!")
        print("   - Offline store: Historical features for training")
        print("   - Online store: Latest features for inference")
    
    def register_feature(self, definition: FeatureDefinition):
        """Register a new feature definition"""
        with self._lock:
            self.feature_definitions[definition.name] = definition
        print(f"   ✅ Registered feature: {definition.name} ({definition.feature_type.value})")
    
    def get_feature_definition(self, name: str) -> Optional[FeatureDefinition]:
        """Get a feature's definition"""
        return self.feature_definitions.get(name)
    
    def list_features(self, entity: str = None, tag: str = None) -> List[FeatureDefinition]:
        """List features, optionally filtered by entity or tag"""
        features = list(self.feature_definitions.values())
        
        if entity:
            features = [f for f in features if f.entity == entity]
        if tag:
            features = [f for f in features if tag in f.tags]
        
        return features
    
    def ingest_features(self, entity_id: str, features: Dict[str, Any],
                        timestamp: datetime = None):
        """
        Ingest features into both offline and online stores.
        This ensures consistency between training and serving.
        """
        timestamp = timestamp or datetime.now()
        
        # Write to offline store (with timestamp for history)
        self.offline_store.write_features(entity_id, features, timestamp)
        
        # Write to online store (latest values only)
        self.online_store.write_features(entity_id, features)
    
    def get_online_features(self, entity_id: str, feature_names: List[str]) -> Dict[str, Any]:
        """Get features for real-time inference (low latency)"""
        return self.online_store.get_features(entity_id, feature_names)
    
    def get_historical_features(self, entity_id: str, feature_names: List[str],
                                point_in_time: datetime) -> Dict[str, Any]:
        """Get features as they were at a specific point in time (for training)"""
        return self.offline_store.get_features_at_time(entity_id, feature_names, point_in_time)
    
    def get_training_data(self, entity_ids: List[str], feature_names: List[str],
                          start_time: datetime, end_time: datetime) -> List[Dict]:
        """Generate training dataset with point-in-time correctness"""
        return self.offline_store.get_training_dataset(
            entity_ids, feature_names, start_time, end_time
        )


class FeatureEngineeringPipeline:
    """
    Computes derived features from raw data.
    """
    
    def __init__(self, feature_store: FeatureStore):
        self.feature_store = feature_store
        self.transformations: Dict[str, callable] = {}
    
    def register_transformation(self, feature_name: str, transform_fn: callable):
        """Register a feature transformation function"""
        self.transformations[feature_name] = transform_fn
        print(f"   📐 Registered transformation: {feature_name}")
    
    def compute_features(self, entity_id: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compute all registered features from raw data"""
        computed = {}
        
        for feature_name, transform_fn in self.transformations.items():
            try:
                computed[feature_name] = transform_fn(raw_data)
            except Exception as e:
                print(f"   ⚠️ Error computing {feature_name}: {e}")
                computed[feature_name] = None
        
        return computed
    
    def run_pipeline(self, entity_id: str, raw_data: Dict[str, Any]):
        """Compute features and ingest into feature store"""
        features = self.compute_features(entity_id, raw_data)
        self.feature_store.ingest_features(entity_id, features)
        return features


def demo_image_classification_features():
    """Demo: Feature store for image classification"""
    print("\n" + "=" * 70)
    print("📸 DEMO: Image Classification Feature Store")
    print("=" * 70)
    
    # Initialize feature store
    fs = FeatureStore()
    
    # Register feature definitions
    print("\n📋 Registering feature definitions...")
    
    fs.register_feature(FeatureDefinition(
        name="image_brightness",
        feature_type=FeatureType.NUMERIC,
        description="Average brightness of the image (0-255)",
        entity="image",
        owner="vision-team",
        tags=["image", "preprocessing"]
    ))
    
    fs.register_feature(FeatureDefinition(
        name="image_contrast",
        feature_type=FeatureType.NUMERIC,
        description="Contrast ratio of the image",
        entity="image",
        owner="vision-team",
        tags=["image", "preprocessing"]
    ))
    
    fs.register_feature(FeatureDefinition(
        name="dominant_color",
        feature_type=FeatureType.CATEGORICAL,
        description="Dominant color in the image",
        entity="image",
        owner="vision-team",
        tags=["image", "color"]
    ))
    
    fs.register_feature(FeatureDefinition(
        name="image_embedding",
        feature_type=FeatureType.EMBEDDING,
        description="512-dim embedding from ResNet",
        entity="image",
        owner="ml-team",
        tags=["embedding", "deep-learning"]
    ))
    
    # Setup feature engineering pipeline
    print("\n🔧 Setting up feature engineering pipeline...")
    pipeline = FeatureEngineeringPipeline(fs)
    
    # Register transformations
    pipeline.register_transformation(
        "image_brightness",
        lambda data: data.get("pixel_mean", 0) * 255
    )
    
    pipeline.register_transformation(
        "image_contrast",
        lambda data: data.get("pixel_std", 0) / (data.get("pixel_mean", 1) + 0.001)
    )
    
    pipeline.register_transformation(
        "dominant_color",
        lambda data: data.get("top_color", "unknown")
    )
    
    pipeline.register_transformation(
        "image_embedding",
        lambda data: data.get("embedding", [0.0] * 512)
    )
    
    # Simulate ingesting features for multiple images
    print("\n📥 Ingesting features for images...")
    
    image_ids = [f"img_{i:04d}" for i in range(1, 11)]
    
    for img_id in image_ids:
        # Simulate raw image data
        raw_data = {
            "pixel_mean": random.uniform(0.3, 0.7),
            "pixel_std": random.uniform(0.1, 0.3),
            "top_color": random.choice(["red", "blue", "green", "white", "brown"]),
            "embedding": [random.uniform(-1, 1) for _ in range(512)]
        }
        
        # Run pipeline to compute and store features
        pipeline.run_pipeline(img_id, raw_data)
    
    print(f"   ✅ Ingested features for {len(image_ids)} images")
    
    # Demonstrate online feature retrieval (for inference)
    print("\n⚡ Online Feature Retrieval (Inference)...")
    
    test_image = "img_0005"
    feature_names = ["image_brightness", "image_contrast", "dominant_color"]
    
    start = time.perf_counter()
    features = fs.get_online_features(test_image, feature_names)
    latency = (time.perf_counter() - start) * 1000
    
    print(f"   Image: {test_image}")
    print(f"   Features retrieved in {latency:.4f} ms")
    for name, value in features.items():
        if name != "image_embedding":
            print(f"     - {name}: {value:.4f}" if isinstance(value, float) else f"     - {name}: {value}")
    
    # Show online store stats
    print("\n📊 Online Store Statistics:")
    stats = fs.online_store.get_stats()
    print(f"   Total entities: {stats['total_entities']}")
    print(f"   Total reads: {stats['reads']}")
    print(f"   Avg read time: {stats['avg_read_time_ms']:.4f} ms")
    
    return fs


def demo_user_recommendation_features():
    """Demo: Feature store for user recommendations"""
    print("\n" + "=" * 70)
    print("👤 DEMO: User Recommendation Feature Store")
    print("=" * 70)
    
    fs = FeatureStore()
    
    # Register user features
    print("\n📋 Registering user feature definitions...")
    
    features_to_register = [
        ("user_purchase_count_7d", FeatureType.NUMERIC, "Number of purchases in last 7 days"),
        ("user_avg_order_value", FeatureType.NUMERIC, "Average order value in USD"),
        ("user_favorite_category", FeatureType.CATEGORICAL, "Most purchased category"),
        ("user_account_age_days", FeatureType.NUMERIC, "Days since account creation"),
        ("user_is_premium", FeatureType.CATEGORICAL, "Whether user has premium subscription"),
    ]
    
    for name, ftype, desc in features_to_register:
        fs.register_feature(FeatureDefinition(
            name=name,
            feature_type=ftype,
            description=desc,
            entity="user",
            owner="recommendation-team",
            tags=["user", "recommendation"]
        ))
    
    # Simulate historical feature data
    print("\n📥 Ingesting historical user features...")
    
    user_ids = [f"user_{i:04d}" for i in range(1, 101)]
    base_time = datetime.now() - timedelta(days=30)
    
    for user_id in user_ids:
        # Simulate features at different points in time
        for day_offset in range(0, 30, 7):
            timestamp = base_time + timedelta(days=day_offset)
            
            features = {
                "user_purchase_count_7d": random.randint(0, 20),
                "user_avg_order_value": random.uniform(20, 200),
                "user_favorite_category": random.choice(["electronics", "clothing", "books", "home"]),
                "user_account_age_days": day_offset + random.randint(30, 365),
                "user_is_premium": random.choice(["yes", "no"])
            }
            
            fs.ingest_features(user_id, features, timestamp)
    
    print(f"   ✅ Ingested features for {len(user_ids)} users over 30 days")
    
    # Demonstrate point-in-time correctness
    print("\n🕐 Point-in-Time Feature Retrieval (Training)...")
    
    test_user = "user_0042"
    feature_names = ["user_purchase_count_7d", "user_avg_order_value", "user_favorite_category"]
    
    # Get features as they were 14 days ago
    past_time = datetime.now() - timedelta(days=14)
    historical_features = fs.get_historical_features(test_user, feature_names, past_time)
    
    print(f"   User: {test_user}")
    print(f"   Point in time: {past_time.strftime('%Y-%m-%d')}")
    for name, value in historical_features.items():
        print(f"     - {name}: {value}")
    
    # Get current features (for inference)
    print("\n⚡ Current Features (Inference)...")
    current_features = fs.get_online_features(test_user, feature_names)
    
    print(f"   User: {test_user}")
    print(f"   Point in time: NOW")
    for name, value in current_features.items():
        print(f"     - {name}: {value}")
    
    # Generate training dataset
    print("\n📊 Generating Training Dataset...")
    
    training_users = user_ids[:20]
    start_time = datetime.now() - timedelta(days=30)
    end_time = datetime.now() - timedelta(days=7)  # Leave 7 days for validation
    
    training_data = fs.get_training_data(training_users, feature_names, start_time, end_time)
    
    print(f"   Training samples: {len(training_data)}")
    print(f"   Features per sample: {len(feature_names)}")
    print(f"   Sample record: {training_data[0]}")
    
    return fs


def demo_training_serving_consistency():
    """Demo: Ensuring consistency between training and serving"""
    print("\n" + "=" * 70)
    print("🔄 DEMO: Training/Serving Consistency")
    print("=" * 70)
    
    fs = FeatureStore()
    
    # Register a feature
    fs.register_feature(FeatureDefinition(
        name="user_score",
        feature_type=FeatureType.NUMERIC,
        description="Calculated user engagement score",
        entity="user",
        owner="ml-team",
        tags=["user", "engagement"]
    ))
    
    user_id = "user_001"
    
    # Simulate feature values changing over time
    print("\n📈 Simulating feature changes over time...")
    
    timestamps = [
        datetime.now() - timedelta(days=10),
        datetime.now() - timedelta(days=5),
        datetime.now() - timedelta(days=1),
        datetime.now()
    ]
    
    scores = [50, 65, 80, 95]
    
    for ts, score in zip(timestamps, scores):
        fs.ingest_features(user_id, {"user_score": score}, ts)
        print(f"   {ts.strftime('%Y-%m-%d')}: user_score = {score}")
    
    # Show how training gets point-in-time correct data
    print("\n🎯 Training Data (Point-in-Time Correct):")
    
    for days_ago in [8, 3, 0]:
        pit = datetime.now() - timedelta(days=days_ago)
        features = fs.get_historical_features(user_id, ["user_score"], pit)
        print(f"   {days_ago} days ago: user_score = {features['user_score']}")
    
    # Show how inference gets latest data
    print("\n⚡ Inference Data (Latest):")
    features = fs.get_online_features(user_id, ["user_score"])
    print(f"   Current: user_score = {features['user_score']}")
    
    print("\n✅ Key Insight:")
    print("   - Training uses historical values to prevent data leakage")
    print("   - Inference uses latest values for real-time predictions")
    print("   - Both use the SAME feature definitions for consistency")


def benchmark_feature_retrieval():
    """Benchmark online feature retrieval performance"""
    print("\n" + "=" * 70)
    print("⏱️ BENCHMARK: Feature Retrieval Performance")
    print("=" * 70)
    
    fs = FeatureStore()
    
    # Register features
    for i in range(10):
        fs.register_feature(FeatureDefinition(
            name=f"feature_{i}",
            feature_type=FeatureType.NUMERIC,
            description=f"Test feature {i}",
            entity="entity",
            owner="test"
        ))
    
    # Ingest features for many entities
    print("\n📥 Ingesting features for 10,000 entities...")
    num_entities = 10000
    
    for i in range(num_entities):
        features = {f"feature_{j}": random.random() for j in range(10)}
        fs.ingest_features(f"entity_{i}", features)
    
    print(f"   ✅ Ingested {num_entities} entities")
    
    # Benchmark reads
    print("\n⚡ Benchmarking feature retrieval...")
    
    feature_names = [f"feature_{i}" for i in range(10)]
    num_reads = 1000
    latencies = []
    
    for i in range(num_reads):
        entity_id = f"entity_{random.randint(0, num_entities-1)}"
        
        start = time.perf_counter()
        _ = fs.get_online_features(entity_id, feature_names)
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)
    
    print(f"\n📊 Results ({num_reads} reads):")
    print(f"   Avg latency: {statistics.mean(latencies):.4f} ms")
    print(f"   P50 latency: {sorted(latencies)[len(latencies)//2]:.4f} ms")
    print(f"   P99 latency: {sorted(latencies)[int(len(latencies)*0.99)]:.4f} ms")
    print(f"   Throughput: {1000/statistics.mean(latencies):.0f} reads/sec")


def main():
    """Main demo function"""
    print("=" * 70)
    print("🏪 FEATURE STORE DEMO")
    print("=" * 70)
    
    # Run demos
    demo_image_classification_features()
    demo_user_recommendation_features()
    demo_training_serving_consistency()
    benchmark_feature_retrieval()
    
    print("\n" + "=" * 70)
    print("✅ ALL DEMOS COMPLETE!")
    print("=" * 70)
    
    print("\n🎯 Key Takeaways:")
    print("  1. Feature stores centralize feature management")
    print("  2. Online store: Low-latency reads for inference")
    print("  3. Offline store: Historical data for training")
    print("  4. Point-in-time correctness prevents data leakage")
    print("  5. Same feature definitions ensure consistency")
    
    print("\n🏭 Popular Feature Stores:")
    print("  - Feast (open source)")
    print("  - Tecton")
    print("  - AWS SageMaker Feature Store")
    print("  - Databricks Feature Store")
    print("  - Google Vertex AI Feature Store")


if __name__ == "__main__":
    main()