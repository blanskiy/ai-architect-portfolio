"""
MLOps Quality Gate
Checks if model meets quality thresholds for deployment.

Usage:
    python quality_gate.py --results evaluation_results.json --min-accuracy 0.85
"""

import argparse
import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class QualityCheck:
    name: str
    passed: bool
    actual_value: float
    threshold: float
    operator: str  # 'gte', 'lte', 'gt', 'lt'
    severity: str  # 'blocker', 'warning'
    message: str


def check_quality_gates(
    results: dict,
    min_accuracy: float = 0.85,
    max_accuracy_drop: float = 0.01,
    max_latency_p95: float = 100.0,
    max_model_size: float = 500.0,
) -> list[QualityCheck]:
    """Run all quality gate checks."""
    
    checks = []
    challenger = results.get('challenger', {})
    comparison = results.get('comparison', {})
    
    # Check 1: Minimum accuracy
    accuracy = challenger.get('accuracy', 0)
    checks.append(QualityCheck(
        name='minimum_accuracy',
        passed=accuracy >= min_accuracy,
        actual_value=accuracy,
        threshold=min_accuracy,
        operator='gte',
        severity='blocker',
        message=f"Accuracy {accuracy:.4f} {'≥' if accuracy >= min_accuracy else '<'} {min_accuracy}"
    ))
    
    # Check 2: Accuracy drop vs champion
    accuracy_diff = comparison.get('accuracy_diff', 0)
    if results.get('champion'):
        checks.append(QualityCheck(
            name='accuracy_drop',
            passed=accuracy_diff >= -max_accuracy_drop,
            actual_value=accuracy_diff,
            threshold=-max_accuracy_drop,
            operator='gte',
            severity='blocker',
            message=f"Accuracy diff {accuracy_diff:+.4f} {'≥' if accuracy_diff >= -max_accuracy_drop else '<'} {-max_accuracy_drop}"
        ))
    
    # Check 3: Latency P95
    latency_p95 = challenger.get('latency_p95_ms', 0)
    checks.append(QualityCheck(
        name='latency_p95',
        passed=latency_p95 <= max_latency_p95,
        actual_value=latency_p95,
        threshold=max_latency_p95,
        operator='lte',
        severity='blocker',
        message=f"Latency P95 {latency_p95:.2f}ms {'≤' if latency_p95 <= max_latency_p95 else '>'} {max_latency_p95}ms"
    ))
    
    # Check 4: Model size (warning only)
    model_size = challenger.get('model_size_mb', 0)
    if model_size > 0:
        checks.append(QualityCheck(
            name='model_size',
            passed=model_size <= max_model_size,
            actual_value=model_size,
            threshold=max_model_size,
            operator='lte',
            severity='warning',
            message=f"Model size {model_size:.2f}MB {'≤' if model_size <= max_model_size else '>'} {max_model_size}MB"
        ))
    
    return checks


def evaluate_gates(checks: list[QualityCheck]) -> tuple[bool, dict]:
    """Evaluate all checks and determine overall pass/fail."""
    
    blockers_passed = all(c.passed for c in checks if c.severity == 'blocker')
    warnings = [c for c in checks if c.severity == 'warning' and not c.passed]
    
    summary = {
        'passed': blockers_passed,
        'total_checks': len(checks),
        'passed_checks': sum(1 for c in checks if c.passed),
        'failed_blockers': [c.name for c in checks if c.severity == 'blocker' and not c.passed],
        'warnings': [c.name for c in warnings],
        'checks': [
            {
                'name': c.name,
                'passed': c.passed,
                'actual': c.actual_value,
                'threshold': c.threshold,
                'severity': c.severity,
                'message': c.message,
            }
            for c in checks
        ]
    }
    
    return blockers_passed, summary


def print_report(checks: list[QualityCheck], passed: bool):
    """Print formatted quality gate report."""
    
    print("\n" + "="*60)
    print("🔒 QUALITY GATE REPORT")
    print("="*60)
    
    for check in checks:
        status = "✅" if check.passed else ("⚠️" if check.severity == 'warning' else "❌")
        print(f"\n{status} {check.name.upper()}")
        print(f"   {check.message}")
        print(f"   Severity: {check.severity}")
    
    print("\n" + "-"*60)
    if passed:
        print("✅ QUALITY GATE: PASSED")
        print("   Model is approved for deployment")
    else:
        print("❌ QUALITY GATE: FAILED")
        print("   Model is blocked from deployment")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description='Quality gate check')
    parser.add_argument('--results', type=str, required=True,
                        help='Path to evaluation results JSON')
    parser.add_argument('--min-accuracy', type=float, default=0.85,
                        help='Minimum accuracy threshold')
    parser.add_argument('--max-accuracy-drop', type=float, default=0.01,
                        help='Maximum allowed accuracy drop vs champion')
    parser.add_argument('--max-latency-p95', type=float, default=100.0,
                        help='Maximum P95 latency in ms')
    parser.add_argument('--max-model-size', type=float, default=500.0,
                        help='Maximum model size in MB')
    parser.add_argument('--output-file', type=str, default='gate_results.json',
                        help='Output file for gate results')
    
    args = parser.parse_args()
    
    # Load evaluation results
    with open(args.results, 'r') as f:
        results = json.load(f)
    
    # Run quality checks
    checks = check_quality_gates(
        results,
        min_accuracy=args.min_accuracy,
        max_accuracy_drop=args.max_accuracy_drop,
        max_latency_p95=args.max_latency_p95,
        max_model_size=args.max_model_size,
    )
    
    # Evaluate
    passed, summary = evaluate_gates(checks)
    
    # Print report
    print_report(checks, passed)
    
    # Save results
    with open(args.output_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nResults saved to {args.output_file}")
    
    # Exit with appropriate code
    if not passed:
        exit(1)


if __name__ == '__main__':
    main()
