"""
Statistical Engine for A/B Testing
Hypothesis testing and sample size calculations.

Methods:
- Z-test for proportions (conversion rates)
- T-test for continuous metrics (revenue, etc.)
- Chi-square test for categorical outcomes
- Sample size calculation
- Confidence intervals

Usage:
    from stats_engine import (
        z_test_proportions,
        calculate_sample_size,
        get_confidence_interval
    )
    
    result = z_test_proportions(
        conversions_a=100, total_a=1000,
        conversions_b=120, total_b=1000
    )
    print(f"p-value: {result.p_value}")
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple
from scipy import stats
import numpy as np


@dataclass
class TestResult:
    """Result of a statistical test."""
    test_name: str
    statistic: float
    p_value: float
    significant: bool
    confidence_level: float
    effect_size: Optional[float] = None
    confidence_interval: Optional[Tuple[float, float]] = None
    power: Optional[float] = None
    interpretation: str = ""


# ============================================================================
# PROPORTION TESTS (for conversion rates)
# ============================================================================

def z_test_proportions(
    conversions_a: int,
    total_a: int,
    conversions_b: int,
    total_b: int,
    confidence_level: float = 0.95,
    alternative: str = 'two-sided',
) -> TestResult:
    """
    Two-proportion Z-test.
    
    Tests if two conversion rates are significantly different.
    
    Args:
        conversions_a: Number of conversions in group A (control)
        total_a: Total samples in group A
        conversions_b: Number of conversions in group B (treatment)
        total_b: Total samples in group B
        confidence_level: Confidence level (default 0.95 = 95%)
        alternative: 'two-sided', 'greater', or 'less'
    
    Returns:
        TestResult with z-statistic, p-value, and interpretation
    
    Example:
        # Control: 100/1000 = 10% conversion
        # Treatment: 120/1000 = 12% conversion
        result = z_test_proportions(100, 1000, 120, 1000)
        # Is the 2% lift statistically significant?
    """
    
    # Calculate proportions
    p_a = conversions_a / total_a
    p_b = conversions_b / total_b
    
    # Pooled proportion (under null hypothesis)
    p_pooled = (conversions_a + conversions_b) / (total_a + total_b)
    
    # Standard error
    se = math.sqrt(p_pooled * (1 - p_pooled) * (1/total_a + 1/total_b))
    
    # Z-statistic
    if se == 0:
        z_stat = 0.0
    else:
        z_stat = (p_b - p_a) / se
    
    # P-value
    if alternative == 'two-sided':
        p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
    elif alternative == 'greater':
        p_value = 1 - stats.norm.cdf(z_stat)
    else:  # less
        p_value = stats.norm.cdf(z_stat)
    
    # Significance
    alpha = 1 - confidence_level
    significant = p_value < alpha
    
    # Effect size (relative lift)
    if p_a > 0:
        relative_lift = (p_b - p_a) / p_a
    else:
        relative_lift = float('inf') if p_b > 0 else 0.0
    
    # Confidence interval for difference
    z_critical = stats.norm.ppf(1 - alpha/2)
    se_diff = math.sqrt(p_a * (1-p_a) / total_a + p_b * (1-p_b) / total_b)
    diff = p_b - p_a
    ci_lower = diff - z_critical * se_diff
    ci_upper = diff + z_critical * se_diff
    
    # Interpretation
    if significant:
        direction = "higher" if p_b > p_a else "lower"
        interpretation = (
            f"Treatment ({p_b:.2%}) is significantly {direction} than "
            f"Control ({p_a:.2%}). Relative lift: {relative_lift:+.1%}. "
            f"95% CI for difference: [{ci_lower:+.2%}, {ci_upper:+.2%}]"
        )
    else:
        interpretation = (
            f"No significant difference between Treatment ({p_b:.2%}) and "
            f"Control ({p_a:.2%}). p-value: {p_value:.3f}"
        )
    
    return TestResult(
        test_name="Two-Proportion Z-Test",
        statistic=z_stat,
        p_value=p_value,
        significant=significant,
        confidence_level=confidence_level,
        effect_size=relative_lift,
        confidence_interval=(ci_lower, ci_upper),
        interpretation=interpretation,
    )


def chi_square_test(
    contingency_table: list[list[int]],
    confidence_level: float = 0.95,
) -> TestResult:
    """
    Chi-square test for independence.
    
    Tests if there's an association between variant and outcome.
    
    Args:
        contingency_table: 2x2 table [[a, b], [c, d]]
            where rows are variants, columns are outcomes
    
    Example:
        # Control: 900 no-convert, 100 convert
        # Treatment: 880 no-convert, 120 convert
        table = [[900, 100], [880, 120]]
        result = chi_square_test(table)
    """
    
    chi2, p_value, dof, expected = stats.chi2_contingency(contingency_table)
    
    alpha = 1 - confidence_level
    significant = p_value < alpha
    
    # Cramér's V for effect size
    n = sum(sum(row) for row in contingency_table)
    min_dim = min(len(contingency_table), len(contingency_table[0])) - 1
    cramers_v = math.sqrt(chi2 / (n * min_dim)) if min_dim > 0 else 0
    
    interpretation = (
        f"Chi-square = {chi2:.2f}, p = {p_value:.4f}. "
        f"{'Significant' if significant else 'Not significant'} association "
        f"between variant and outcome."
    )
    
    return TestResult(
        test_name="Chi-Square Test",
        statistic=chi2,
        p_value=p_value,
        significant=significant,
        confidence_level=confidence_level,
        effect_size=cramers_v,
        interpretation=interpretation,
    )


# ============================================================================
# CONTINUOUS METRIC TESTS (for revenue, etc.)
# ============================================================================

def t_test_independent(
    values_a: list[float],
    values_b: list[float],
    confidence_level: float = 0.95,
    equal_variance: bool = False,
) -> TestResult:
    """
    Independent samples t-test.
    
    Tests if two groups have significantly different means.
    
    Args:
        values_a: Values from group A (control)
        values_b: Values from group B (treatment)
        confidence_level: Confidence level
        equal_variance: If False, uses Welch's t-test (recommended)
    
    Example:
        # Compare average revenue per user
        control_revenue = [10, 20, 15, 0, 50, 0, 25, ...]
        treatment_revenue = [15, 30, 20, 0, 60, 10, 35, ...]
        result = t_test_independent(control_revenue, treatment_revenue)
    """
    
    a = np.array(values_a)
    b = np.array(values_b)
    
    # Calculate means
    mean_a = np.mean(a)
    mean_b = np.mean(b)
    
    # T-test
    t_stat, p_value = stats.ttest_ind(a, b, equal_var=equal_variance)
    
    # Significance
    alpha = 1 - confidence_level
    significant = p_value < alpha
    
    # Effect size (Cohen's d)
    pooled_std = np.sqrt(((len(a)-1)*np.std(a, ddof=1)**2 + (len(b)-1)*np.std(b, ddof=1)**2) / (len(a)+len(b)-2))
    cohens_d = (mean_b - mean_a) / pooled_std if pooled_std > 0 else 0
    
    # Confidence interval for difference
    se_diff = np.sqrt(np.var(a, ddof=1)/len(a) + np.var(b, ddof=1)/len(b))
    t_critical = stats.t.ppf(1 - alpha/2, df=len(a)+len(b)-2)
    diff = mean_b - mean_a
    ci_lower = diff - t_critical * se_diff
    ci_upper = diff + t_critical * se_diff
    
    # Relative lift
    relative_lift = (mean_b - mean_a) / mean_a if mean_a != 0 else float('inf')
    
    interpretation = (
        f"Control mean: {mean_a:.2f}, Treatment mean: {mean_b:.2f}. "
        f"Difference: {diff:+.2f} ({relative_lift:+.1%}). "
        f"{'Significant' if significant else 'Not significant'} (p={p_value:.4f}). "
        f"Cohen's d: {cohens_d:.2f}"
    )
    
    return TestResult(
        test_name="Independent T-Test",
        statistic=t_stat,
        p_value=p_value,
        significant=significant,
        confidence_level=confidence_level,
        effect_size=cohens_d,
        confidence_interval=(ci_lower, ci_upper),
        interpretation=interpretation,
    )


def mann_whitney_test(
    values_a: list[float],
    values_b: list[float],
    confidence_level: float = 0.95,
) -> TestResult:
    """
    Mann-Whitney U test (non-parametric).
    
    Use when data is not normally distributed (e.g., revenue with many zeros).
    
    Tests if one group tends to have larger values than another.
    """
    
    a = np.array(values_a)
    b = np.array(values_b)
    
    u_stat, p_value = stats.mannwhitneyu(a, b, alternative='two-sided')
    
    alpha = 1 - confidence_level
    significant = p_value < alpha
    
    # Effect size: rank-biserial correlation
    n1, n2 = len(a), len(b)
    r = 1 - (2*u_stat) / (n1*n2)
    
    interpretation = (
        f"Mann-Whitney U = {u_stat:.0f}, p = {p_value:.4f}. "
        f"{'Significant' if significant else 'Not significant'} difference. "
        f"Effect size r = {r:.3f}"
    )
    
    return TestResult(
        test_name="Mann-Whitney U Test",
        statistic=u_stat,
        p_value=p_value,
        significant=significant,
        confidence_level=confidence_level,
        effect_size=r,
        interpretation=interpretation,
    )


# ============================================================================
# SAMPLE SIZE CALCULATION
# ============================================================================

def calculate_sample_size(
    baseline_rate: float,
    min_detectable_effect: float,
    power: float = 0.8,
    significance_level: float = 0.05,
    ratio: float = 1.0,
) -> dict:
    """
    Calculate required sample size for an A/B test.
    
    Args:
        baseline_rate: Current conversion rate (e.g., 0.10 for 10%)
        min_detectable_effect: Minimum relative lift to detect (e.g., 0.05 for 5%)
        power: Statistical power (default 0.8 = 80%)
        significance_level: Alpha (default 0.05 = 5%)
        ratio: Ratio of treatment to control size (default 1:1)
    
    Returns:
        Dict with sample sizes and assumptions
    
    Example:
        # Detect 5% relative lift on 10% baseline
        result = calculate_sample_size(
            baseline_rate=0.10,
            min_detectable_effect=0.05  # 10% -> 10.5%
        )
        # Need ~31,000 per variant
    """
    
    # Treatment rate under alternative hypothesis
    treatment_rate = baseline_rate * (1 + min_detectable_effect)
    
    # Z-scores
    z_alpha = stats.norm.ppf(1 - significance_level / 2)  # Two-tailed
    z_beta = stats.norm.ppf(power)
    
    # Pooled proportion
    p_pooled = (baseline_rate + treatment_rate) / 2
    
    # Sample size formula
    numerator = (z_alpha * math.sqrt(2 * p_pooled * (1 - p_pooled)) + 
                 z_beta * math.sqrt(baseline_rate * (1 - baseline_rate) + 
                                    treatment_rate * (1 - treatment_rate))) ** 2
    denominator = (treatment_rate - baseline_rate) ** 2
    
    n_per_variant = math.ceil(numerator / denominator)
    
    # Adjust for ratio
    n_control = n_per_variant
    n_treatment = math.ceil(n_per_variant * ratio)
    
    return {
        'n_control': n_control,
        'n_treatment': n_treatment,
        'n_total': n_control + n_treatment,
        'assumptions': {
            'baseline_rate': baseline_rate,
            'treatment_rate': treatment_rate,
            'absolute_effect': treatment_rate - baseline_rate,
            'relative_effect': min_detectable_effect,
            'power': power,
            'significance_level': significance_level,
        }
    }


def calculate_duration(
    required_sample_size: int,
    daily_traffic: int,
    treatment_fraction: float = 0.5,
) -> dict:
    """
    Estimate experiment duration.
    
    Args:
        required_sample_size: Required samples per variant
        daily_traffic: Average daily users
        treatment_fraction: Fraction of traffic in experiment
    
    Returns:
        Estimated duration in days
    """
    
    daily_samples_per_variant = daily_traffic * treatment_fraction / 2
    days_needed = math.ceil(required_sample_size / daily_samples_per_variant)
    
    return {
        'days_needed': days_needed,
        'weeks_needed': math.ceil(days_needed / 7),
        'daily_samples_per_variant': daily_samples_per_variant,
    }


# ============================================================================
# CONFIDENCE INTERVALS
# ============================================================================

def get_confidence_interval_proportion(
    successes: int,
    total: int,
    confidence_level: float = 0.95,
    method: str = 'wilson',
) -> Tuple[float, float]:
    """
    Calculate confidence interval for a proportion.
    
    Args:
        successes: Number of successes
        total: Total trials
        confidence_level: Confidence level
        method: 'wilson' (recommended), 'normal', or 'exact'
    
    Returns:
        (lower_bound, upper_bound)
    """
    
    p = successes / total if total > 0 else 0
    alpha = 1 - confidence_level
    z = stats.norm.ppf(1 - alpha/2)
    
    if method == 'wilson':
        # Wilson score interval (better for small samples or extreme proportions)
        denominator = 1 + z**2/total
        center = (p + z**2/(2*total)) / denominator
        spread = z * math.sqrt((p*(1-p) + z**2/(4*total)) / total) / denominator
        return (center - spread, center + spread)
    
    elif method == 'normal':
        # Normal approximation
        se = math.sqrt(p * (1-p) / total)
        return (p - z * se, p + z * se)
    
    elif method == 'exact':
        # Clopper-Pearson exact interval
        lower = stats.beta.ppf(alpha/2, successes, total - successes + 1)
        upper = stats.beta.ppf(1 - alpha/2, successes + 1, total - successes)
        return (lower, upper)
    
    else:
        raise ValueError(f"Unknown method: {method}")


# ============================================================================
# POWER ANALYSIS
# ============================================================================

def calculate_power(
    baseline_rate: float,
    treatment_rate: float,
    n_per_variant: int,
    significance_level: float = 0.05,
) -> float:
    """
    Calculate statistical power given sample size.
    
    Args:
        baseline_rate: Control conversion rate
        treatment_rate: Expected treatment conversion rate
        n_per_variant: Sample size per variant
        significance_level: Alpha level
    
    Returns:
        Power (probability of detecting effect if it exists)
    """
    
    z_alpha = stats.norm.ppf(1 - significance_level / 2)
    
    p_pooled = (baseline_rate + treatment_rate) / 2
    se_null = math.sqrt(2 * p_pooled * (1 - p_pooled) / n_per_variant)
    se_alt = math.sqrt((baseline_rate * (1 - baseline_rate) + 
                        treatment_rate * (1 - treatment_rate)) / n_per_variant)
    
    effect = treatment_rate - baseline_rate
    z_beta = (effect - z_alpha * se_null) / se_alt
    
    power = stats.norm.cdf(z_beta)
    
    return power


# Example usage
if __name__ == '__main__':
    print("=" * 60)
    print("STATISTICAL TESTING EXAMPLES")
    print("=" * 60)
    
    # Example 1: Conversion rate test
    print("\n1. CONVERSION RATE TEST")
    print("-" * 40)
    result = z_test_proportions(
        conversions_a=100, total_a=1000,  # Control: 10%
        conversions_b=120, total_b=1000   # Treatment: 12%
    )
    print(f"Test: {result.test_name}")
    print(f"Z-statistic: {result.statistic:.3f}")
    print(f"P-value: {result.p_value:.4f}")
    print(f"Significant: {result.significant}")
    print(f"Effect size (relative lift): {result.effect_size:.1%}")
    print(f"\n{result.interpretation}")
    
    # Example 2: Sample size calculation
    print("\n2. SAMPLE SIZE CALCULATION")
    print("-" * 40)
    sample = calculate_sample_size(
        baseline_rate=0.10,
        min_detectable_effect=0.05,  # 5% relative lift
        power=0.8
    )
    print(f"Baseline: {sample['assumptions']['baseline_rate']:.0%}")
    print(f"Minimum detectable effect: {sample['assumptions']['relative_effect']:.0%}")
    print(f"Required per variant: {sample['n_control']:,}")
    print(f"Total required: {sample['n_total']:,}")
    
    # Duration estimate
    duration = calculate_duration(
        required_sample_size=sample['n_control'],
        daily_traffic=10000,
        treatment_fraction=1.0
    )
    print(f"With 10K daily users: ~{duration['days_needed']} days ({duration['weeks_needed']} weeks)")
    
    # Example 3: Revenue t-test
    print("\n3. REVENUE T-TEST")
    print("-" * 40)
    np.random.seed(42)
    control_revenue = np.random.exponential(25, 500)
    treatment_revenue = np.random.exponential(28, 500)  # 12% higher
    
    result = t_test_independent(
        list(control_revenue),
        list(treatment_revenue)
    )
    print(f"P-value: {result.p_value:.4f}")
    print(f"Significant: {result.significant}")
    print(f"\n{result.interpretation}")
