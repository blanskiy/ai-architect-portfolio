"""
Experiment Management
Defines and tracks A/B test experiments.

Usage:
    from experiment import Experiment, ExperimentTracker
    
    exp = Experiment(
        name="model-v4-test",
        variants={"control": 0.9, "treatment": 0.1},
        primary_metric="conversion_rate"
    )
    
    tracker = ExperimentTracker(exp)
    tracker.log_event(user_id="123", variant="treatment", converted=True)
"""

import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional, Any
from enum import Enum
from collections import defaultdict
import threading


class ExperimentStatus(Enum):
    """Experiment lifecycle states."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Variant:
    """A single variant in an experiment."""
    name: str
    weight: float  # Traffic weight (0.0 to 1.0)
    config: dict = field(default_factory=dict)  # Model config, parameters, etc.
    
    def __post_init__(self):
        if not 0 <= self.weight <= 1:
            raise ValueError(f"Weight must be between 0 and 1, got {self.weight}")


@dataclass
class Metric:
    """Metric to track in experiment."""
    name: str
    metric_type: str  # 'conversion', 'continuous', 'count'
    is_primary: bool = False
    min_detectable_effect: Optional[float] = None  # For sample size calculation
    
    def __post_init__(self):
        valid_types = ['conversion', 'continuous', 'count']
        if self.metric_type not in valid_types:
            raise ValueError(f"metric_type must be one of {valid_types}")


@dataclass
class Experiment:
    """
    A/B Test Experiment definition.
    
    Attributes:
        name: Unique experiment identifier
        description: Human-readable description
        variants: Dict of variant_name -> Variant or weight
        primary_metric: Name of the primary metric
        secondary_metrics: List of secondary metric names
        min_sample_size: Minimum samples per variant
        max_duration_days: Maximum experiment duration
        status: Current experiment status
    """
    name: str
    variants: dict
    primary_metric: str
    description: str = ""
    secondary_metrics: list = field(default_factory=list)
    min_sample_size: int = 1000
    max_duration_days: int = 14
    status: ExperimentStatus = ExperimentStatus.DRAFT
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    
    def __post_init__(self):
        # Convert simple weights to Variant objects
        processed_variants = {}
        for name, value in self.variants.items():
            if isinstance(value, Variant):
                processed_variants[name] = value
            elif isinstance(value, (int, float)):
                processed_variants[name] = Variant(name=name, weight=float(value))
            elif isinstance(value, dict):
                weight = value.get('weight', 0.5)
                config = {k: v for k, v in value.items() if k != 'weight'}
                processed_variants[name] = Variant(name=name, weight=weight, config=config)
            else:
                raise ValueError(f"Invalid variant definition: {value}")
        
        self.variants = processed_variants
        
        # Validate weights sum to ~1
        total_weight = sum(v.weight for v in self.variants.values())
        if not 0.99 <= total_weight <= 1.01:
            raise ValueError(f"Variant weights must sum to 1, got {total_weight}")
    
    def start(self):
        """Start the experiment."""
        self.status = ExperimentStatus.RUNNING
        self.started_at = datetime.now().isoformat()
    
    def pause(self):
        """Pause the experiment."""
        self.status = ExperimentStatus.PAUSED
    
    def complete(self):
        """Mark experiment as completed."""
        self.status = ExperimentStatus.COMPLETED
        self.ended_at = datetime.now().isoformat()
    
    def cancel(self):
        """Cancel the experiment."""
        self.status = ExperimentStatus.CANCELLED
        self.ended_at = datetime.now().isoformat()
    
    def get_variant_names(self) -> list[str]:
        """Get list of variant names."""
        return list(self.variants.keys())
    
    def get_variant_weight(self, variant_name: str) -> float:
        """Get weight for a variant."""
        return self.variants[variant_name].weight
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'variants': {
                name: {'weight': v.weight, 'config': v.config}
                for name, v in self.variants.items()
            },
            'primary_metric': self.primary_metric,
            'secondary_metrics': self.secondary_metrics,
            'min_sample_size': self.min_sample_size,
            'max_duration_days': self.max_duration_days,
            'status': self.status.value,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'ended_at': self.ended_at,
        }


@dataclass
class ExperimentEvent:
    """A single event/observation in an experiment."""
    user_id: str
    variant: str
    timestamp: str
    converted: Optional[bool] = None
    value: Optional[float] = None  # For continuous metrics (revenue, etc.)
    metadata: dict = field(default_factory=dict)


class ExperimentTracker:
    """
    Tracks events and outcomes for an experiment.
    
    Thread-safe for concurrent logging.
    
    Usage:
        tracker = ExperimentTracker(experiment)
        tracker.log_event(user_id="123", variant="control", converted=True)
        tracker.log_event(user_id="456", variant="treatment", converted=False, value=0)
        
        summary = tracker.get_summary()
    """
    
    def __init__(self, experiment: Experiment):
        self.experiment = experiment
        self.events: list[ExperimentEvent] = []
        self.user_variants: dict[str, str] = {}  # user_id -> variant (sticky)
        self._lock = threading.Lock()
        
        # Aggregated stats per variant
        self._stats = {
            variant: {
                'exposures': 0,
                'conversions': 0,
                'total_value': 0.0,
                'values': [],
            }
            for variant in experiment.get_variant_names()
        }
    
    def log_exposure(self, user_id: str, variant: str):
        """Log that a user was exposed to a variant."""
        with self._lock:
            if user_id not in self.user_variants:
                self.user_variants[user_id] = variant
                self._stats[variant]['exposures'] += 1
    
    def log_event(
        self,
        user_id: str,
        variant: str,
        converted: Optional[bool] = None,
        value: Optional[float] = None,
        metadata: dict = None,
    ):
        """
        Log an event/outcome for a user.
        
        Args:
            user_id: Unique user identifier
            variant: Variant the user was assigned to
            converted: Whether user converted (for conversion metrics)
            value: Numeric value (for continuous metrics like revenue)
            metadata: Additional event data
        """
        
        event = ExperimentEvent(
            user_id=user_id,
            variant=variant,
            timestamp=datetime.now().isoformat(),
            converted=converted,
            value=value,
            metadata=metadata or {},
        )
        
        with self._lock:
            self.events.append(event)
            
            # Update aggregated stats
            stats = self._stats[variant]
            
            if user_id not in self.user_variants:
                self.user_variants[user_id] = variant
                stats['exposures'] += 1
            
            if converted is not None and converted:
                stats['conversions'] += 1
            
            if value is not None:
                stats['total_value'] += value
                stats['values'].append(value)
    
    def get_variant_stats(self, variant: str) -> dict:
        """Get aggregated stats for a variant."""
        with self._lock:
            stats = self._stats[variant].copy()
            
            # Calculate rates
            n = stats['exposures']
            if n > 0:
                stats['conversion_rate'] = stats['conversions'] / n
                stats['mean_value'] = stats['total_value'] / n
            else:
                stats['conversion_rate'] = 0.0
                stats['mean_value'] = 0.0
            
            return stats
    
    def get_summary(self) -> dict:
        """Get summary of experiment results."""
        summary = {
            'experiment': self.experiment.name,
            'status': self.experiment.status.value,
            'total_users': len(self.user_variants),
            'total_events': len(self.events),
            'variants': {},
        }
        
        for variant in self.experiment.get_variant_names():
            summary['variants'][variant] = self.get_variant_stats(variant)
        
        return summary
    
    def get_events_dataframe(self):
        """Get events as a pandas DataFrame."""
        import pandas as pd
        
        records = []
        for event in self.events:
            record = {
                'user_id': event.user_id,
                'variant': event.variant,
                'timestamp': event.timestamp,
                'converted': event.converted,
                'value': event.value,
            }
            record.update(event.metadata)
            records.append(record)
        
        return pd.DataFrame(records)
    
    def export_events(self, filepath: str):
        """Export events to JSON file."""
        with open(filepath, 'w') as f:
            events_data = [asdict(e) for e in self.events]
            json.dump({
                'experiment': self.experiment.to_dict(),
                'events': events_data,
                'summary': self.get_summary(),
            }, f, indent=2)


class ExperimentRegistry:
    """
    Registry for managing multiple experiments.
    
    Usage:
        registry = ExperimentRegistry()
        registry.register(experiment)
        exp = registry.get("my-experiment")
    """
    
    def __init__(self):
        self.experiments: dict[str, Experiment] = {}
        self._lock = threading.Lock()
    
    def register(self, experiment: Experiment):
        """Register an experiment."""
        with self._lock:
            if experiment.name in self.experiments:
                raise ValueError(f"Experiment '{experiment.name}' already exists")
            self.experiments[experiment.name] = experiment
    
    def get(self, name: str) -> Optional[Experiment]:
        """Get experiment by name."""
        return self.experiments.get(name)
    
    def list_active(self) -> list[Experiment]:
        """Get all running experiments."""
        return [
            exp for exp in self.experiments.values()
            if exp.status == ExperimentStatus.RUNNING
        ]
    
    def list_all(self) -> list[Experiment]:
        """Get all experiments."""
        return list(self.experiments.values())


# Example usage
if __name__ == '__main__':
    # Create experiment
    exp = Experiment(
        name="model-v4-rollout",
        description="Testing new sales prediction model",
        variants={
            "control": {"weight": 0.9, "model": "v3"},
            "treatment": {"weight": 0.1, "model": "v4"},
        },
        primary_metric="conversion_rate",
        secondary_metrics=["revenue", "latency"],
        min_sample_size=1000,
    )
    
    print("Experiment created:")
    print(json.dumps(exp.to_dict(), indent=2))
    
    # Create tracker
    tracker = ExperimentTracker(exp)
    
    # Simulate some events
    import random
    random.seed(42)
    
    for i in range(100):
        user_id = f"user_{i}"
        variant = "control" if random.random() < 0.9 else "treatment"
        converted = random.random() < (0.10 if variant == "control" else 0.12)
        revenue = random.uniform(20, 100) if converted else 0
        
        tracker.log_event(
            user_id=user_id,
            variant=variant,
            converted=converted,
            value=revenue,
        )
    
    # Print summary
    print("\nExperiment Summary:")
    print(json.dumps(tracker.get_summary(), indent=2))
