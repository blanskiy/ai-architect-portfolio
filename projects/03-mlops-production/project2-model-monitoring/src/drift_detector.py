"""
Drift Detection Module
Detects data drift and prediction drift using statistical tests.

Supported methods:
- PSI (Population Stability Index) - for categorical and binned continuous
- KS Test (Kolmogorov-Smirnov) - for continuous features
- Chi-Square Test - for categorical features

Usage:
    python drift_detector.py --reference data/train.csv --current data/prod.csv
"""

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class DriftResult:
    """Result of drift detection for a single feature."""
    feature_name: str
    drift_score: float
    drift_detected: bool
    test_method: str
    threshold: float
    p_value: Optional[float] = None
    details: Optional[dict] = None


@dataclass
class DriftReport:
    """Complete drift report for all features."""
    timestamp: str
    overall_drift_score: float
    overall_drift_detected: bool
    num_features_drifted: int
    total_features: int
    feature_results: list
    reference_samples: int
    current_samples: int


def calculate_psi(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """
    Calculate Population Stability Index (PSI).
    
    PSI measures how much the distribution has shifted.
    
    Interpretation:
    - PSI < 0.1: No significant drift
    - 0.1 <= PSI < 0.2: Moderate drift, monitor
    - PSI >= 0.2: Significant drift, action required
    
    Formula:
    PSI = Σ (current_% - reference_%) * ln(current_% / reference_%)
    """
    
    # Create bins based on reference distribution
    min_val = min(reference.min(), current.min())
    max_val = max(reference.max(), current.max())
    bin_edges = np.linspace(min_val, max_val, bins + 1)
    
    # Calculate proportions in each bin
    ref_counts, _ = np.histogram(reference, bins=bin_edges)
    cur_counts, _ = np.histogram(current, bins=bin_edges)
    
    # Convert to proportions (add small epsilon to avoid division by zero)
    epsilon = 1e-10
    ref_props = (ref_counts + epsilon) / (len(reference) + epsilon * bins)
    cur_props = (cur_counts + epsilon) / (len(current) + epsilon * bins)
    
    # Calculate PSI
    psi = np.sum((cur_props - ref_props) * np.log(cur_props / ref_props))
    
    return float(psi)


def calculate_ks_statistic(reference: np.ndarray, current: np.ndarray) -> tuple[float, float]:
    """
    Calculate Kolmogorov-Smirnov statistic.
    
    KS test measures the maximum distance between two cumulative distributions.
    
    Returns:
        (ks_statistic, p_value)
    
    Interpretation:
    - p_value < 0.05: Distributions are significantly different
    - ks_statistic: Maximum difference between CDFs (0 to 1)
    """
    
    statistic, p_value = stats.ks_2samp(reference, current)
    return float(statistic), float(p_value)


def calculate_chi_square(reference: pd.Series, current: pd.Series) -> tuple[float, float]:
    """
    Calculate Chi-Square statistic for categorical features.
    
    Returns:
        (chi2_statistic, p_value)
    """
    
    # Get all categories from both distributions
    all_categories = set(reference.unique()) | set(current.unique())
    
    # Count frequencies
    ref_counts = reference.value_counts()
    cur_counts = current.value_counts()
    
    # Ensure same categories in both
    ref_freq = [ref_counts.get(cat, 0) for cat in all_categories]
    cur_freq = [cur_counts.get(cat, 0) for cat in all_categories]
    
    # Scale to same total (for fair comparison)
    ref_freq = np.array(ref_freq) / sum(ref_freq) * len(current)
    
    # Chi-square test
    chi2, p_value = stats.chisquare(cur_freq, ref_freq)
    
    return float(chi2), float(p_value)


def detect_feature_drift(
    reference: pd.Series,
    current: pd.Series,
    feature_name: str,
    method: str = 'auto',
    threshold: float = 0.1,
) -> DriftResult:
    """
    Detect drift for a single feature.
    
    Args:
        reference: Feature values from reference (training) data
        current: Feature values from current (production) data
        feature_name: Name of the feature
        method: 'psi', 'ks', 'chi2', or 'auto' (auto-detect based on dtype)
        threshold: Drift threshold
    
    Returns:
        DriftResult with drift score and detection
    """
    
    # Auto-detect method based on data type
    if method == 'auto':
        if reference.dtype == 'object' or reference.nunique() < 10:
            method = 'chi2'
        else:
            method = 'psi'
    
    # Calculate drift
    if method == 'psi':
        ref_clean = reference.dropna().values
        cur_clean = current.dropna().values
        
        drift_score = calculate_psi(ref_clean, cur_clean)
        
        return DriftResult(
            feature_name=feature_name,
            drift_score=drift_score,
            drift_detected=drift_score >= threshold,
            test_method='PSI',
            threshold=threshold,
            details={
                'interpretation': 'No drift' if drift_score < 0.1 
                    else 'Moderate drift' if drift_score < 0.2 
                    else 'Significant drift'
            }
        )
    
    elif method == 'ks':
        ref_clean = reference.dropna().values
        cur_clean = current.dropna().values
        
        ks_stat, p_value = calculate_ks_statistic(ref_clean, cur_clean)
        
        return DriftResult(
            feature_name=feature_name,
            drift_score=ks_stat,
            drift_detected=p_value < 0.05,
            test_method='KS Test',
            threshold=0.05,
            p_value=p_value,
            details={'ks_statistic': ks_stat}
        )
    
    elif method == 'chi2':
        ref_clean = reference.dropna()
        cur_clean = current.dropna()
        
        chi2_stat, p_value = calculate_chi_square(ref_clean, cur_clean)
        
        return DriftResult(
            feature_name=feature_name,
            drift_score=chi2_stat,
            drift_detected=p_value < 0.05,
            test_method='Chi-Square',
            threshold=0.05,
            p_value=p_value,
        )
    
    else:
        raise ValueError(f"Unknown method: {method}")


def detect_dataset_drift(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    features: list[str] = None,
    method: str = 'auto',
    threshold: float = 0.1,
) -> DriftReport:
    """
    Detect drift across all features in a dataset.
    
    Args:
        reference_df: Reference (training) dataset
        current_df: Current (production) dataset
        features: List of features to check (None = all common columns)
        method: Detection method
        threshold: Drift threshold
    
    Returns:
        DriftReport with overall and per-feature results
    """
    
    # Determine features to check
    if features is None:
        features = list(set(reference_df.columns) & set(current_df.columns))
    
    # Check each feature
    feature_results = []
    for feature in features:
        if feature not in reference_df.columns or feature not in current_df.columns:
            continue
        
        result = detect_feature_drift(
            reference=reference_df[feature],
            current=current_df[feature],
            feature_name=feature,
            method=method,
            threshold=threshold,
        )
        feature_results.append(result)
    
    # Calculate overall drift
    drift_scores = [r.drift_score for r in feature_results]
    num_drifted = sum(1 for r in feature_results if r.drift_detected)
    
    # Overall drift score: mean of feature drift scores
    overall_drift_score = np.mean(drift_scores) if drift_scores else 0.0
    
    # Overall drift detected if >20% of features drifted
    drift_ratio = num_drifted / len(feature_results) if feature_results else 0
    overall_drift_detected = drift_ratio > 0.2 or overall_drift_score > threshold
    
    return DriftReport(
        timestamp=datetime.now().isoformat(),
        overall_drift_score=float(overall_drift_score),
        overall_drift_detected=overall_drift_detected,
        num_features_drifted=num_drifted,
        total_features=len(feature_results),
        feature_results=[asdict(r) for r in feature_results],
        reference_samples=len(reference_df),
        current_samples=len(current_df),
    )


def detect_prediction_drift(
    reference_predictions: np.ndarray,
    current_predictions: np.ndarray,
    threshold: float = 0.15,
) -> DriftResult:
    """
    Detect drift in model predictions.
    
    For classification: Compare predicted class distributions
    For regression: Compare prediction value distributions
    """
    
    # Determine if classification or regression
    unique_values = len(np.unique(np.concatenate([reference_predictions, current_predictions])))
    
    if unique_values <= 10:  # Classification
        # Compare class distributions using PSI
        ref_series = pd.Series(reference_predictions)
        cur_series = pd.Series(current_predictions)
        
        all_classes = set(ref_series.unique()) | set(cur_series.unique())
        
        ref_dist = ref_series.value_counts(normalize=True)
        cur_dist = cur_series.value_counts(normalize=True)
        
        # Calculate Jensen-Shannon divergence (symmetric version of KL)
        epsilon = 1e-10
        ref_probs = np.array([ref_dist.get(c, epsilon) for c in all_classes])
        cur_probs = np.array([cur_dist.get(c, epsilon) for c in all_classes])
        
        # Normalize
        ref_probs = ref_probs / ref_probs.sum()
        cur_probs = cur_probs / cur_probs.sum()
        
        # JS divergence
        m = 0.5 * (ref_probs + cur_probs)
        js_div = 0.5 * stats.entropy(ref_probs, m) + 0.5 * stats.entropy(cur_probs, m)
        
        return DriftResult(
            feature_name='predictions',
            drift_score=float(js_div),
            drift_detected=js_div > threshold,
            test_method='Jensen-Shannon Divergence',
            threshold=threshold,
            details={
                'reference_distribution': ref_dist.to_dict(),
                'current_distribution': cur_dist.to_dict(),
            }
        )
    
    else:  # Regression
        drift_score = calculate_psi(reference_predictions, current_predictions)
        
        return DriftResult(
            feature_name='predictions',
            drift_score=drift_score,
            drift_detected=drift_score > threshold,
            test_method='PSI',
            threshold=threshold,
        )


def print_drift_report(report: DriftReport):
    """Print formatted drift report."""
    
    print("\n" + "=" * 60)
    print("📊 DRIFT DETECTION REPORT")
    print("=" * 60)
    print(f"\nTimestamp: {report.timestamp}")
    print(f"Reference samples: {report.reference_samples:,}")
    print(f"Current samples: {report.current_samples:,}")
    
    print(f"\n{'─' * 60}")
    print("OVERALL RESULTS")
    print(f"{'─' * 60}")
    
    status = "🚨 DRIFT DETECTED" if report.overall_drift_detected else "✅ NO SIGNIFICANT DRIFT"
    print(f"\nStatus: {status}")
    print(f"Overall Drift Score: {report.overall_drift_score:.4f}")
    print(f"Features with Drift: {report.num_features_drifted}/{report.total_features}")
    
    print(f"\n{'─' * 60}")
    print("PER-FEATURE RESULTS")
    print(f"{'─' * 60}")
    
    print(f"\n{'Feature':<20} {'Score':<10} {'Method':<12} {'Status':<10}")
    print("-" * 52)
    
    for result in report.feature_results:
        status = "⚠️ DRIFT" if result['drift_detected'] else "✅ OK"
        print(f"{result['feature_name']:<20} {result['drift_score']:<10.4f} "
              f"{result['test_method']:<12} {status:<10}")
    
    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Detect data drift')
    parser.add_argument('--reference-data', type=str, required=True,
                        help='Path to reference (training) data CSV')
    parser.add_argument('--current-data', type=str, required=True,
                        help='Path to current (production) data CSV')
    parser.add_argument('--features', type=str, nargs='+', default=None,
                        help='Features to check (default: all)')
    parser.add_argument('--method', type=str, default='auto',
                        choices=['auto', 'psi', 'ks', 'chi2'],
                        help='Detection method')
    parser.add_argument('--threshold', type=float, default=0.1,
                        help='Drift threshold')
    parser.add_argument('--output-file', type=str, default='drift_report.json',
                        help='Output file for report')
    
    args = parser.parse_args()
    
    # Load data
    print(f"Loading reference data: {args.reference_data}")
    reference_df = pd.read_csv(args.reference_data)
    
    print(f"Loading current data: {args.current_data}")
    current_df = pd.read_csv(args.current_data)
    
    # Detect drift
    report = detect_dataset_drift(
        reference_df=reference_df,
        current_df=current_df,
        features=args.features,
        method=args.method,
        threshold=args.threshold,
    )
    
    # Print report
    print_drift_report(report)
    
    # Save report
    with open(args.output_file, 'w') as f:
        json.dump(asdict(report), f, indent=2)
    
    print(f"\n📁 Report saved to: {args.output_file}")
    
    # Exit with error code if drift detected
    if report.overall_drift_detected:
        exit(1)


if __name__ == '__main__':
    main()
