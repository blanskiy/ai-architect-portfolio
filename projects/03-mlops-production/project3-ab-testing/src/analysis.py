"""
Experiment Analysis & Reporting
Generate comprehensive A/B test reports with recommendations.

Usage:
    from analysis import ExperimentAnalyzer, generate_report
    
    analyzer = ExperimentAnalyzer(experiment, tracker)
    report = analyzer.analyze()
    print(report.summary())
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import math

from experiment import Experiment, ExperimentTracker
from stats_engine import (
    z_test_proportions,
    t_test_independent,
    calculate_sample_size,
    calculate_power,
    get_confidence_interval_proportion,
    TestResult,
)


@dataclass
class VariantResult:
    """Analysis results for a single variant."""
    name: str
    sample_size: int
    conversions: int
    conversion_rate: float
    confidence_interval: tuple[float, float]
    mean_value: Optional[float] = None
    value_confidence_interval: Optional[tuple[float, float]] = None


@dataclass
class ComparisonResult:
    """Comparison between control and treatment."""
    control: str
    treatment: str
    absolute_lift: float
    relative_lift: float
    p_value: float
    significant: bool
    confidence_interval: tuple[float, float]
    test_used: str
    power: Optional[float] = None


@dataclass
class ExperimentReport:
    """Complete experiment analysis report."""
    experiment_name: str
    analysis_timestamp: str
    status: str
    duration_days: Optional[float]
    
    # Sample sizes
    total_users: int
    variant_results: dict[str, VariantResult]
    
    # Statistical comparison
    primary_metric_comparison: ComparisonResult
    secondary_comparisons: list[ComparisonResult]
    
    # Power analysis
    achieved_power: Optional[float]
    sample_size_adequate: bool
    
    # Recommendation
    recommendation: str
    confidence_level: str  # 'high', 'medium', 'low'
    next_steps: list[str]
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            "=" * 60,
            f"EXPERIMENT REPORT: {self.experiment_name}",
            "=" * 60,
            f"Status: {self.status}",
            f"Analysis Date: {self.analysis_timestamp}",
            f"Total Users: {self.total_users:,}",
        ]
        
        if self.duration_days:
            lines.append(f"Duration: {self.duration_days:.1f} days")
        
        lines.append("\n" + "-" * 60)
        lines.append("VARIANT RESULTS")
        lines.append("-" * 60)
        
        for name, result in self.variant_results.items():
            ci_lower, ci_upper = result.confidence_interval
            lines.append(
                f"\n{name.upper()}:\n"
                f"  Sample Size: {result.sample_size:,}\n"
                f"  Conversions: {result.conversions:,}\n"
                f"  Conversion Rate: {result.conversion_rate:.2%} "
                f"(95% CI: [{ci_lower:.2%}, {ci_upper:.2%}])"
            )
            if result.mean_value is not None:
                lines.append(f"  Mean Value: ${result.mean_value:.2f}")
        
        lines.append("\n" + "-" * 60)
        lines.append("STATISTICAL COMPARISON")
        lines.append("-" * 60)
        
        comp = self.primary_metric_comparison
        sig_marker = "✓" if comp.significant else "✗"
        lines.append(
            f"\n{comp.treatment} vs {comp.control}:\n"
            f"  Relative Lift: {comp.relative_lift:+.1%}\n"
            f"  Absolute Lift: {comp.absolute_lift:+.2%}\n"
            f"  p-value: {comp.p_value:.4f} {sig_marker}\n"
            f"  95% CI: [{comp.confidence_interval[0]:+.2%}, {comp.confidence_interval[1]:+.2%}]\n"
            f"  Significant: {'Yes' if comp.significant else 'No'}"
        )
        
        if self.achieved_power:
            lines.append(f"  Statistical Power: {self.achieved_power:.1%}")
        
        lines.append("\n" + "-" * 60)
        lines.append("RECOMMENDATION")
        lines.append("-" * 60)
        lines.append(f"\n{self.recommendation}")
        lines.append(f"\nConfidence: {self.confidence_level.upper()}")
        
        lines.append("\nNext Steps:")
        for step in self.next_steps:
            lines.append(f"  • {step}")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export."""
        return {
            'experiment_name': self.experiment_name,
            'analysis_timestamp': self.analysis_timestamp,
            'status': self.status,
            'duration_days': self.duration_days,
            'total_users': self.total_users,
            'variant_results': {
                name: {
                    'sample_size': v.sample_size,
                    'conversions': v.conversions,
                    'conversion_rate': v.conversion_rate,
                    'confidence_interval': v.confidence_interval,
                }
                for name, v in self.variant_results.items()
            },
            'primary_comparison': {
                'control': self.primary_metric_comparison.control,
                'treatment': self.primary_metric_comparison.treatment,
                'relative_lift': self.primary_metric_comparison.relative_lift,
                'p_value': self.primary_metric_comparison.p_value,
                'significant': self.primary_metric_comparison.significant,
            },
            'recommendation': self.recommendation,
            'confidence_level': self.confidence_level,
            'next_steps': self.next_steps,
        }


class ExperimentAnalyzer:
    """
    Analyzes experiment results and generates reports.
    
    Usage:
        analyzer = ExperimentAnalyzer(experiment, tracker)
        report = analyzer.analyze()
    """
    
    def __init__(
        self,
        experiment: Experiment,
        tracker: ExperimentTracker,
        control_variant: str = "control",
        confidence_level: float = 0.95,
    ):
        self.experiment = experiment
        self.tracker = tracker
        self.control_variant = control_variant
        self.confidence_level = confidence_level
    
    def analyze(self) -> ExperimentReport:
        """Perform full analysis and generate report."""
        
        summary = self.tracker.get_summary()
        
        # Calculate duration
        duration_days = None
        if self.experiment.started_at:
            start = datetime.fromisoformat(self.experiment.started_at)
            end = datetime.now()
            if self.experiment.ended_at:
                end = datetime.fromisoformat(self.experiment.ended_at)
            duration_days = (end - start).total_seconds() / 86400
        
        # Analyze each variant
        variant_results = {}
        for variant_name in self.experiment.get_variant_names():
            stats = self.tracker.get_variant_stats(variant_name)
            
            ci = get_confidence_interval_proportion(
                stats['conversions'],
                stats['exposures'],
                self.confidence_level,
            )
            
            variant_results[variant_name] = VariantResult(
                name=variant_name,
                sample_size=stats['exposures'],
                conversions=stats['conversions'],
                conversion_rate=stats['conversion_rate'],
                confidence_interval=ci,
                mean_value=stats['mean_value'] if stats['mean_value'] > 0 else None,
            )
        
        # Statistical comparison
        control_stats = self.tracker.get_variant_stats(self.control_variant)
        treatment_variants = [v for v in self.experiment.get_variant_names() if v != self.control_variant]
        
        # Primary comparison (first treatment vs control)
        if treatment_variants:
            treatment_name = treatment_variants[0]
            treatment_stats = self.tracker.get_variant_stats(treatment_name)
            
            test_result = z_test_proportions(
                control_stats['conversions'],
                control_stats['exposures'],
                treatment_stats['conversions'],
                treatment_stats['exposures'],
                self.confidence_level,
            )
            
            control_rate = control_stats['conversion_rate']
            treatment_rate = treatment_stats['conversion_rate']
            
            primary_comparison = ComparisonResult(
                control=self.control_variant,
                treatment=treatment_name,
                absolute_lift=treatment_rate - control_rate,
                relative_lift=(treatment_rate - control_rate) / control_rate if control_rate > 0 else 0,
                p_value=test_result.p_value,
                significant=test_result.significant,
                confidence_interval=test_result.confidence_interval,
                test_used=test_result.test_name,
            )
            
            # Calculate achieved power
            achieved_power = calculate_power(
                baseline_rate=control_rate,
                treatment_rate=treatment_rate,
                n_per_variant=min(control_stats['exposures'], treatment_stats['exposures']),
            )
            primary_comparison.power = achieved_power
        else:
            primary_comparison = None
            achieved_power = None
        
        # Check sample size adequacy
        min_sample = self.experiment.min_sample_size
        sample_adequate = all(
            v.sample_size >= min_sample 
            for v in variant_results.values()
        )
        
        # Generate recommendation
        recommendation, confidence, next_steps = self._generate_recommendation(
            primary_comparison,
            sample_adequate,
            variant_results,
        )
        
        return ExperimentReport(
            experiment_name=self.experiment.name,
            analysis_timestamp=datetime.now().isoformat(),
            status=self.experiment.status.value,
            duration_days=duration_days,
            total_users=summary['total_users'],
            variant_results=variant_results,
            primary_metric_comparison=primary_comparison,
            secondary_comparisons=[],
            achieved_power=achieved_power,
            sample_size_adequate=sample_adequate,
            recommendation=recommendation,
            confidence_level=confidence,
            next_steps=next_steps,
        )
    
    def _generate_recommendation(
        self,
        comparison: Optional[ComparisonResult],
        sample_adequate: bool,
        variant_results: dict[str, VariantResult],
    ) -> tuple[str, str, list[str]]:
        """Generate recommendation based on analysis."""
        
        if comparison is None:
            return (
                "Unable to generate recommendation - no comparison available.",
                "low",
                ["Ensure experiment has both control and treatment variants."]
            )
        
        if not sample_adequate:
            return (
                f"WAIT: Insufficient sample size. Continue running experiment until "
                f"each variant has at least {self.experiment.min_sample_size:,} users.",
                "low",
                [
                    "Continue running the experiment",
                    f"Target: {self.experiment.min_sample_size:,} users per variant",
                    "Do not make decisions based on current data",
                ]
            )
        
        if comparison.significant:
            if comparison.relative_lift > 0:
                return (
                    f"DEPLOY TREATMENT: {comparison.treatment} shows a statistically "
                    f"significant improvement of {comparison.relative_lift:+.1%} over "
                    f"{comparison.control} (p={comparison.p_value:.4f}).",
                    "high",
                    [
                        f"Roll out {comparison.treatment} to 100% of traffic",
                        "Monitor key metrics post-deployment",
                        "Set up alerting for any degradation",
                        "Document learnings for future experiments",
                    ]
                )
            else:
                return (
                    f"KEEP CONTROL: {comparison.treatment} performs significantly worse "
                    f"than {comparison.control} ({comparison.relative_lift:+.1%}, "
                    f"p={comparison.p_value:.4f}). Do not deploy.",
                    "high",
                    [
                        f"Do not deploy {comparison.treatment}",
                        "Investigate why treatment underperformed",
                        "Consider alternative hypotheses",
                        "Design new experiment with different approach",
                    ]
                )
        else:
            # Not significant
            if comparison.power and comparison.power < 0.8:
                return (
                    f"UNDERPOWERED: No significant difference detected, but statistical "
                    f"power is only {comparison.power:.0%}. The experiment may be too "
                    f"small to detect the expected effect.",
                    "medium",
                    [
                        "Continue running to increase sample size",
                        "Consider if minimum detectable effect is realistic",
                        "Calculate required sample size for adequate power",
                    ]
                )
            else:
                return (
                    f"NO DIFFERENCE: No statistically significant difference between "
                    f"{comparison.treatment} and {comparison.control} "
                    f"(p={comparison.p_value:.4f}). The treatment does not appear to "
                    f"improve the primary metric.",
                    "medium",
                    [
                        "Consider keeping control (simpler is better)",
                        "Investigate if treatment has non-primary benefits",
                        "Design experiment with larger effect hypothesis",
                        "Explore different treatment variations",
                    ]
                )


def analyze_experiment(
    experiment: Experiment,
    tracker: ExperimentTracker,
) -> ExperimentReport:
    """Convenience function to analyze an experiment."""
    analyzer = ExperimentAnalyzer(experiment, tracker)
    return analyzer.analyze()


def export_report(report: ExperimentReport, filepath: str):
    """Export report to JSON file."""
    with open(filepath, 'w') as f:
        json.dump(report.to_dict(), f, indent=2)


# Example usage
if __name__ == '__main__':
    import random
    from experiment import Experiment, ExperimentTracker
    
    # Create experiment
    exp = Experiment(
        name="new-recommendation-model",
        variants={
            "control": 0.5,
            "treatment": 0.5,
        },
        primary_metric="conversion_rate",
        min_sample_size=1000,
    )
    exp.start()
    
    # Create tracker and simulate data
    tracker = ExperimentTracker(exp)
    
    random.seed(42)
    
    # Simulate 2000 users
    for i in range(2000):
        user_id = f"user_{i}"
        variant = "control" if i % 2 == 0 else "treatment"
        
        # Control: 10% conversion, Treatment: 12% conversion
        conversion_rate = 0.10 if variant == "control" else 0.12
        converted = random.random() < conversion_rate
        revenue = random.uniform(20, 100) if converted else 0
        
        tracker.log_event(
            user_id=user_id,
            variant=variant,
            converted=converted,
            value=revenue,
        )
    
    # Analyze
    report = analyze_experiment(exp, tracker)
    
    # Print report
    print(report.summary())
