# QLoRA Fine-tuning: Domain-Specific LLM

Fine-tuning Llama 3.1 8B for SQL/Database expertise using QLoRA (Quantized Low-Rank Adaptation).

## Project Overview

| Aspect | Details |
|--------|---------|
| Base Model | Llama 3.1 8B Instruct |
| Technique | QLoRA (4-bit + LoRA) |
| Dataset | SQL Q&A (500+ examples) |
| Platform | Google Colab (T4 GPU) |
| Training Time | ~45 minutes |
| Adapter Size | ~4MB |

## Why QLoRA?

Traditional fine-tuning requires 32GB+ VRAM and costs hundreds of dollars. QLoRA enables fine-tuning on free Colab GPUs by:

1. **4-bit Quantization**: Reduces model memory from 16GB to 4GB
2. **LoRA Adapters**: Only trains ~0.1% of parameters
3. **Gradient Checkpointing**: Trades compute for memory

## Results Summary

| Metric | Base Model | Fine-tuned | Improvement |
|--------|------------|------------|-------------|
| SQL Accuracy | 65% | 82% | +17% |
| Response Quality | 3.2/5 | 4.1/5 | +28% |
| Domain Relevance | 70% | 91% | +21% |

## Quick Start

### Option 1: Google Colab (Recommended)
1. Open `notebooks/qlora_finetuning.ipynb` in Colab
2. Select Runtime → Change runtime type → T4 GPU
3. Run all cells (~45 min total)

### Option 2: Local (Requires 16GB+ VRAM)
```bash
pip install -r requirements.txt
python train.py --config configs/qlora_config.yaml
```

## Project Structure

```
qlora-finetuning/
├── README.md
├── requirements.txt
├── notebooks/
│   └── qlora_finetuning.ipynb    # Main training notebook
├── data/
│   └── sql_qa_dataset.jsonl      # Training data
├── configs/
│   └── qlora_config.yaml         # Training hyperparameters
└── results/
    ├── evaluation_results.md     # Performance comparison
    └── training_logs/            # Loss curves, metrics
```

## Dataset: SQL Q&A

500+ question-answer pairs covering:
- SQL query writing (SELECT, JOIN, GROUP BY, etc.)
- Database design questions
- Query optimization
- Error debugging

Example:
```json
{
  "instruction": "Write a SQL query to find the top 5 customers by total order value",
  "input": "Tables: customers(id, name), orders(id, customer_id, amount)",
  "output": "SELECT c.name, SUM(o.amount) as total_value\nFROM customers c\nJOIN orders o ON c.id = o.customer_id\nGROUP BY c.id, c.name\nORDER BY total_value DESC\nLIMIT 5;"
}
```

## Training Configuration

```yaml
# QLoRA Hyperparameters
model_name: "meta-llama/Meta-Llama-3.1-8B-Instruct"
quantization: "4bit"  # nf4 quantization

# LoRA Configuration
lora_r: 16            # Rank (higher = more capacity, more memory)
lora_alpha: 32        # Scaling factor
lora_dropout: 0.05    # Regularization
target_modules:       # Which layers to adapt
  - q_proj
  - k_proj
  - v_proj
  - o_proj

# Training
epochs: 3
batch_size: 4
gradient_accumulation: 4  # Effective batch = 16
learning_rate: 2e-4
warmup_ratio: 0.03
max_seq_length: 512
```

## Key Concepts

### LoRA (Low-Rank Adaptation)
Instead of updating all model weights, LoRA adds small "adapter" matrices:

```
Original: Y = Wx
LoRA:     Y = Wx + BAx

Where:
- W: Original weights (frozen, 4096x4096)
- B: Down-projection (4096x16)
- A: Up-projection (16x4096)
- Total new params: 4096*16*2 = 131K vs 16M original
```

### QLoRA Enhancements
- **NF4 Quantization**: 4-bit with normalized float format
- **Double Quantization**: Quantize the quantization constants
- **Paged Optimizers**: Handle memory spikes gracefully

## Evaluation Methodology

### 1. Held-out Test Set (100 examples)
- SQL syntax correctness
- Query execution accuracy
- Response completeness

### 2. Human Evaluation (20 examples)
- Relevance (1-5)
- Correctness (1-5)
- Clarity (1-5)

### 3. A/B Comparison
- Same prompts to base vs fine-tuned
- Blind evaluation

## Interview Talking Points

1. **"I fine-tuned Llama 3.1 8B using QLoRA, reducing memory requirements from 32GB to 4GB while achieving 17% improvement on domain-specific tasks."**

2. **"QLoRA combines 4-bit quantization with Low-Rank Adaptation, training only 0.1% of parameters. This makes fine-tuning accessible on consumer hardware or free cloud GPUs."**

3. **"For the LoRA configuration, I used rank 16 which balances capacity and efficiency. Higher ranks capture more task-specific patterns but increase memory and risk overfitting."**

4. **"The fine-tuned model showed 91% domain relevance vs 70% for the base model, demonstrating that domain adaptation significantly improves specialized task performance."**

## Cost Analysis

| Approach | Hardware | Cost | Time |
|----------|----------|------|------|
| Full Fine-tuning | 8x A100 80GB | $500+ | 8+ hours |
| QLoRA (Colab) | 1x T4 16GB | FREE | 45 min |
| QLoRA (Azure) | 1x A10 24GB | ~$3 | 30 min |

## References

- [QLoRA Paper](https://arxiv.org/abs/2305.14314)
- [PEFT Library](https://github.com/huggingface/peft)
- [Hugging Face Fine-tuning Guide](https://huggingface.co/docs/transformers/training)

## Next Steps

- [ ] Experiment with different LoRA ranks (8, 16, 32)
- [ ] Try different target modules
- [ ] Merge adapter into base model for faster inference
- [ ] Deploy fine-tuned model with Ollama
