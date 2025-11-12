#!/usr/bin/env python3
"""
Extract plots from executed notebook and save to plots/ directory
"""
import json
import base64
from pathlib import Path

# Read the executed notebook
notebook_path = Path("notebooks/ml_basics_executed.ipynb")
plots_dir = Path("plots")
plots_dir.mkdir(exist_ok=True)

with open(notebook_path, 'r', encoding='utf-8') as f:
    notebook = json.load(f)

# Counter for naming plots
plot_counter = 1

# Iterate through cells and extract PNG outputs
for cell_idx, cell in enumerate(notebook['cells']):
    if 'outputs' in cell:
        for output in cell['outputs']:
            if 'data' in output and 'image/png' in output['data']:
                # Get the base64 encoded image
                img_data = output['data']['image/png']

                # Decode and save
                img_bytes = base64.b64decode(img_data)

                # Try to infer plot name from cell source
                cell_source = ''.join(cell.get('source', []))

                if 'Actual vs Predicted' in cell_source:
                    filename = f"01_regression_actual_vs_predicted.png"
                elif 'Confusion Matrix' in cell_source:
                    filename = f"02_classification_confusion_matrix.png"
                elif 'feature_importances' in cell_source:
                    filename = f"03_feature_importances.png"
                elif 'Model Complexity' in cell_source or 'CV Accuracy' in cell_source:
                    filename = f"04_model_complexity_cv.png"
                else:
                    filename = f"plot_{plot_counter:02d}.png"

                output_path = plots_dir / filename
                with open(output_path, 'wb') as img_file:
                    img_file.write(img_bytes)

                print(f"Saved: {output_path}")
                plot_counter += 1

print(f"\nExtracted {plot_counter - 1} plots to {plots_dir}/")
