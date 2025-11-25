#!/usr/bin/env python3
"""
Create performance visualization for the optimization journey.

This script creates a bar chart showing the performance improvements
across all optimization stages.
"""

import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Create docs directory if it doesn't exist
Path("docs").mkdir(exist_ok=True)

# Performance data
stages = ['Baseline\n(Sync)', 'Async\nProcessing', 'Request\nBatching', 
          'Redis\nCaching', 'ONNX\n(Benchmarked)']
rps = [0.32, 1.20, 1.85, 7.0, 13.0]
colors = ['#e74c3c', '#e67e22', '#f39c12', '#2ecc71', '#27ae60']
improvements = ['1×', '3.8×', '5.8×', '22×', '~40×']

# Create figure with two subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# Subplot 1: RPS Bar Chart
bars = ax1.bar(stages, rps, color=colors, edgecolor='black', linewidth=1.5)
ax1.set_ylabel('Requests Per Second (RPS)', fontsize=12, fontweight='bold')
ax1.set_title('High-Throughput ML Serving: Performance Journey', 
              fontsize=14, fontweight='bold', pad=20)
ax1.axhline(y=1.0, color='gray', linestyle='--', linewidth=1, label='Baseline (0.32 RPS)')
ax1.set_ylim(0, 15)
ax1.grid(axis='y', alpha=0.3, linestyle='--')
ax1.legend(loc='upper left', fontsize=10)

# Add value labels on bars
for bar, improvement, value in zip(bars, improvements, rps):
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height + 0.3,
             f'{value} RPS\n({improvement})',
             ha='center', va='bottom', fontsize=10, fontweight='bold')

# Subplot 2: Latency Comparison
categories = ['Baseline', 'Batching', 'Caching\n(Hit)', 'Caching\n(Miss)', 'ONNX\n(Projected)']
latencies = [3125, 540, 15, 718, 368]
latency_colors = ['#e74c3c', '#f39c12', '#2ecc71', '#e67e22', '#27ae60']

bars2 = ax2.bar(categories, latencies, color=latency_colors, edgecolor='black', linewidth=1.5)
ax2.set_ylabel('Latency (milliseconds)', fontsize=12, fontweight='bold')
ax2.set_title('Latency Improvements', fontsize=14, fontweight='bold', pad=20)
ax2.grid(axis='y', alpha=0.3, linestyle='--')

# Add value labels on bars
for bar, value in zip(bars2, latencies):
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height + 100,
             f'{value}ms',
             ha='center', va='bottom', fontsize=10, fontweight='bold')

# Add subtitle
fig.text(0.5, 0.02, 'ResNet-50 Inference API | Week 2 Final Results | 22× Production Improvement (40× with ONNX)', 
         ha='center', fontsize=10, style='italic', color='gray')

plt.tight_layout(rect=[0, 0.03, 1, 1])
plt.savefig('docs/performance_chart.png', dpi=300, bbox_inches='tight', facecolor='white')
print("✓ Performance chart saved to: docs/performance_chart.png")

# Create a second chart: Cost comparison
fig2, ax = plt.subplots(figsize=(10, 6))

cost_stages = ['Baseline', 'Optimized\n(Current)', 'With ONNX\n(Projected)']
cost_per_1k = [0.41, 0.009, 0.005]
cost_colors = ['#e74c3c', '#2ecc71', '#27ae60']

bars3 = ax.bar(cost_stages, cost_per_1k, color=cost_colors, edgecolor='black', linewidth=1.5)
ax.set_ylabel('Cost per 1,000 Requests ($)', fontsize=12, fontweight='bold')
ax.set_title('Cost Optimization', fontsize=14, fontweight='bold', pad=20)
ax.grid(axis='y', alpha=0.3, linestyle='--')

# Add value labels
for bar, value in zip(bars3, cost_per_1k):
    height = bar.get_height()
    savings = ((0.41 - value) / 0.41) * 100 if value < 0.41 else 0
    label = f'${value:.3f}\n({savings:.0f}% savings)' if savings > 0 else f'${value:.3f}'
    ax.text(bar.get_x() + bar.get_width()/2., height + 0.01,
            label,
            ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig('docs/cost_comparison.png', dpi=300, bbox_inches='tight', facecolor='white')
print("✓ Cost comparison chart saved to: docs/cost_comparison.png")

# Create a third chart: Timeline view
fig3, ax = plt.subplots(figsize=(12, 8))

# Timeline data
timeline_stages = [
    'Day 1-2:\nBaseline API',
    'Day 3:\nAsync Processing',
    'Day 4:\nRequest Batching',
    'Day 5:\nMonitoring',
    'Day 6:\nDocker',
    'Day 7:\nRedis Caching',
    'Day 8:\nONNX Benchmarking'
]

timeline_rps = [0.32, 1.20, 1.85, 1.85, 1.85, 7.0, 13.0]
timeline_colors = ['#e74c3c', '#e67e22', '#f39c12', '#f39c12', '#f39c12', '#2ecc71', '#27ae60']

y_pos = np.arange(len(timeline_stages))
bars4 = ax.barh(y_pos, timeline_rps, color=timeline_colors, edgecolor='black', linewidth=1.5)
ax.set_yticks(y_pos)
ax.set_yticklabels(timeline_stages)
ax.set_xlabel('Requests Per Second (RPS)', fontsize=12, fontweight='bold')
ax.set_title('Week 2 Performance Journey: Day-by-Day Progress', 
             fontsize=14, fontweight='bold', pad=20)
ax.grid(axis='x', alpha=0.3, linestyle='--')

# Add value labels
for i, (bar, value) in enumerate(zip(bars4, timeline_rps)):
    width = bar.get_width()
    improvement = f'{value/0.32:.1f}×' if value > 0.32 else '1×'
    ax.text(width + 0.3, bar.get_y() + bar.get_height()/2.,
            f'{value} RPS ({improvement})',
            ha='left', va='center', fontsize=10, fontweight='bold')

plt.tight_layout()
plt.savefig('docs/timeline_progress.png', dpi=300, bbox_inches='tight', facecolor='white')
print("✓ Timeline chart saved to: docs/timeline_progress.png")

print("\n" + "="*60)
print("✅ All performance charts created successfully!")
print("="*60)
print("\nFiles created:")
print("  1. docs/performance_chart.png - RPS and latency comparison")
print("  2. docs/cost_comparison.png - Cost optimization")
print("  3. docs/timeline_progress.png - Day-by-day progress")
print("\nAdd these to your documentation!")
