# QLoRA Fine-tuning Results

## Model
- Base: Llama 3.1 8B Instruct
- Method: QLoRA (4-bit quantization + LoRA)
- Platform: Google Colab T4 GPU (free)

## Training
- Examples: 12 SQL Q&A pairs
- Steps: 60
- Time: ~3 minutes
- Initial Loss: 2.134
- Final Loss: 0.069 (97% reduction)
- Trainable Params: 0.52% (41M of 8B)

## Results
The fine-tuned model correctly generates:
- JOIN queries with GROUP BY and ORDER BY
- Window functions (running totals, rankings)
- Subqueries (above average patterns)

## Key Learnings
1. QLoRA enables fine-tuning 8B models on free T4 GPU
2. Only 0.52% of parameters trained, yet significant improvement
3. 12 examples sufficient for domain-specific patterns
4. Training time: 3 min vs hours for full fine-tuning
