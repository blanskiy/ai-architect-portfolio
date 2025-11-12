# Week 1 ML Basics - Execution Summary

**Executed:** 2025-11-12
**Notebook:** [ml_basics_executed.ipynb](./notebooks/ml_basics_executed.ipynb)
**Environment:** Python 3.10.11 with scikit-learn 1.7.2

---

## Results

### 1. Regression (Diabetes Dataset)

**Models:**
- Linear Regression
- Ridge Regression (α=1.0)

**Performance:**
```
Linear Regression:
- MSE: 2900.194
- R²:  0.453

Ridge Regression:
- R²:  0.419
```

**Key Insight:** Linear regression slightly outperforms Ridge at α=1.0, suggesting minimal overfitting on this dataset. Further hyperparameter tuning for Ridge could improve results.

**Visualization:** [Actual vs Predicted plot](./plots/01_regression_actual_vs_predicted.png)

---

### 2. Classification (Breast Cancer Dataset)

**Model:** Decision Tree (max_depth=4)

**Performance:**
```
Accuracy:  93.9%
Precision: 95.8%
Recall:    94.4%
F1 Score:  95.1%
```

**Confusion Matrix:**
- True Negatives: 39/42 (92.9%)
- True Positives: 68/72 (94.4%)
- False Positives: 3
- False Negatives: 4

**Key Insight:** Excellent performance with simple decision tree. High precision (95.8%) means low false positive rate, which is critical for medical diagnostics.

**Visualizations:**
- [Confusion Matrix](./plots/02_classification_confusion_matrix.png)
- [Feature Importances](./plots/03_feature_importances.png)

---

### 3. Model Complexity Analysis

**Cross-Validation (5-fold) across tree depths 1-10:**

Optimal depth around 3-4, showing:
- Depths 1-2: Underfitting (~90% CV accuracy)
- Depths 3-5: Optimal performance (~94% CV accuracy)
- Depths 6+: Minimal improvement, risk of overfitting

**Visualization:** [Model Complexity vs Performance](./plots/04_model_complexity_cv.png)

---

## Key Takeaways

1. **Train/Test Splitting:** Used 80/20 split with stratification for classification
2. **Evaluation Metrics:**
   - Regression: MSE, R²
   - Classification: Accuracy, Precision, Recall, F1, Confusion Matrix
3. **Model Selection:** Cross-validation curves guide optimal model complexity
4. **Regularization:** Compared Linear vs Ridge regression

---

## Portfolio-Ready Artifacts

✅ 4 professional plots saved to `plots/`
✅ Metrics demonstrating ML fundamentals
✅ Reproducible notebook with all outputs
✅ Code demonstrates best practices (CV, stratified splits, multiple metrics)

---

## Next Steps

- [ ] Experiment with other regression models (Lasso, ElasticNet)
- [ ] Try ensemble methods (Random Forest, Gradient Boosting)
- [ ] Add feature engineering examples
- [ ] Implement hyperparameter tuning (GridSearchCV)
- [ ] Add learning curves to diagnose bias/variance
