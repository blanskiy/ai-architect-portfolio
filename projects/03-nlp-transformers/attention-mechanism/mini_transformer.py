"""
Mini-Transformer Implementation from Scratch
Month 2, Week 1: Understanding Self-Attention

This implements:
1. Self-Attention mechanism
2. Multi-Head Attention
3. Positional Encoding
4. Attention visualization
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Tuple, List

# Set random seed for reproducibility
np.random.seed(42)


class SelfAttention:
    """
    Implements the core self-attention mechanism.
    
    Formula:
    Attention(Q, K, V) = softmax(Q·K^T / √d_k) · V
    """
    
    def __init__(self, d_model: int, d_k: int):
        """
        Args:
            d_model: Dimension of input embeddings (e.g., 512)
            d_k: Dimension of query/key (e.g., 64)
        """
        self.d_model = d_model
        self.d_k = d_k
        
        # Initialize weight matrices (in real transformers, these are learned)
        self.W_q = np.random.randn(d_model, d_k) * 0.1  # Query weights
        self.W_k = np.random.randn(d_model, d_k) * 0.1  # Key weights
        self.W_v = np.random.randn(d_model, d_k) * 0.1  # Value weights
        
    def forward(self, X: np.ndarray, return_attention: bool = True) -> Tuple:
        """
        Forward pass through self-attention.
        
        Args:
            X: Input matrix (seq_len, d_model)
            return_attention: Whether to return attention weights
            
        Returns:
            output: Attention output (seq_len, d_k)
            attention_weights: Attention weights if return_attention=True
        """
        # Step 1: Create Q, K, V by multiplying input with weight matrices
        Q = X @ self.W_q  # (seq_len, d_k)
        K = X @ self.W_k  # (seq_len, d_k)
        V = X @ self.W_v  # (seq_len, d_k)
        
        print(f"Q shape: {Q.shape}, K shape: {K.shape}, V shape: {V.shape}")
        
        # Step 2: Calculate attention scores
        # Q·K^T gives us similarity scores between all pairs of positions
        scores = Q @ K.T  # (seq_len, seq_len)
        
        # Step 3: Scale by √d_k (prevents gradients from vanishing)
        scores = scores / np.sqrt(self.d_k)
        
        # Step 4: Apply softmax to get attention weights (probabilities)
        attention_weights = self._softmax(scores)  # (seq_len, seq_len)
        
        print(f"Attention weights shape: {attention_weights.shape}")
        print(f"Each row sums to 1: {np.allclose(attention_weights.sum(axis=1), 1.0)}")
        
        # Step 5: Weighted sum of values
        output = attention_weights @ V  # (seq_len, d_k)
        
        if return_attention:
            return output, attention_weights
        return output
    
    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        """Numerically stable softmax."""
        exp_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return exp_x / exp_x.sum(axis=-1, keepdims=True)


class MultiHeadAttention:
    """
    Implements multi-head attention.
    
    Uses multiple attention heads to learn different relationship patterns.
    """
    
    def __init__(self, d_model: int, num_heads: int):
        """
        Args:
            d_model: Dimension of input embeddings
            num_heads: Number of attention heads
        """
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads  # Dimension per head
        
        # Create multiple attention heads
        self.heads = [SelfAttention(d_model, self.d_k) for _ in range(num_heads)]
        
        # Output projection
        self.W_o = np.random.randn(d_model, d_model) * 0.1
        
    def forward(self, X: np.ndarray) -> Tuple:
        """
        Forward pass through multi-head attention.
        
        Returns:
            output: Combined output from all heads
            all_attention_weights: List of attention weights from each head
        """
        outputs = []
        attention_weights = []
        
        # Run each attention head
        for i, head in enumerate(self.heads):
            head_output, head_attention = head.forward(X, return_attention=True)
            outputs.append(head_output)
            attention_weights.append(head_attention)
            print(f"Head {i+1} output shape: {head_output.shape}")
        
        # Concatenate outputs from all heads
        concatenated = np.concatenate(outputs, axis=-1)  # (seq_len, d_model)
        
        # Final linear projection
        output = concatenated @ self.W_o
        
        return output, attention_weights


class PositionalEncoding:
    """
    Adds positional information to embeddings using sin/cos functions.
    
    PE(pos, 2i) = sin(pos / 10000^(2i/d_model))
    PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
    """
    
    @staticmethod
    def create(seq_len: int, d_model: int) -> np.ndarray:
        """
        Create positional encodings.
        
        Args:
            seq_len: Length of sequence
            d_model: Dimension of embeddings
            
        Returns:
            Positional encodings (seq_len, d_model)
        """
        position = np.arange(seq_len)[:, np.newaxis]  # (seq_len, 1)
        div_term = np.exp(np.arange(0, d_model, 2) * -(np.log(10000.0) / d_model))
        
        pe = np.zeros((seq_len, d_model))
        pe[:, 0::2] = np.sin(position * div_term)  # Even indices
        pe[:, 1::2] = np.cos(position * div_term)  # Odd indices
        
        return pe


def visualize_attention(attention_weights: np.ndarray, 
                       tokens: List[str],
                       title: str = "Attention Patterns"):
    """
    Visualize attention weights as a heatmap.
    
    Args:
        attention_weights: Attention matrix (seq_len, seq_len)
        tokens: List of token strings
        title: Plot title
    """
    plt.figure(figsize=(10, 8))
    
    sns.heatmap(
        attention_weights,
        xticklabels=tokens,
        yticklabels=tokens,
        cmap='YlOrRd',
        annot=True,
        fmt='.2f',
        cbar_kws={'label': 'Attention Weight'}
    )
    
    plt.title(title, fontsize=14, fontweight='bold')
    plt.xlabel('Key (what we attend TO)', fontsize=12)
    plt.ylabel('Query (what is attending)', fontsize=12)
    plt.tight_layout()


def demo_self_attention():
    """
    Demonstrate self-attention with a simple example.
    """
    print("=" * 70)
    print("SELF-ATTENTION DEMO")
    print("=" * 70)
    
    # Example sentence
    sentence = "The animal didn't cross the street because it was tired"
    tokens = sentence.split()
    
    print(f"\nInput sentence: '{sentence}'")
    print(f"Number of tokens: {len(tokens)}")
    print(f"Tokens: {tokens}")
    
    # Hyperparameters
    d_model = 512  # Embedding dimension (like GPT/BERT)
    seq_len = len(tokens)
    
    # Step 1: Create random embeddings (in real transformers, these come from a learned embedding layer)
    print(f"\n{'Step 1: Create Embeddings':-^70}")
    embeddings = np.random.randn(seq_len, d_model)
    print(f"Embedding matrix shape: {embeddings.shape}")
    print(f"Each word is represented by a {d_model}-dimensional vector")
    
    # Step 2: Add positional encodings
    print(f"\n{'Step 2: Add Positional Encoding':-^70}")
    pos_encoding = PositionalEncoding.create(seq_len, d_model)
    embeddings_with_pos = embeddings + pos_encoding
    print(f"Positional encoding shape: {pos_encoding.shape}")
    print(f"Final input shape: {embeddings_with_pos.shape}")
    
    # Visualize positional encoding
    plt.figure(figsize=(12, 4))
    plt.subplot(1, 2, 1)
    plt.imshow(pos_encoding.T, cmap='RdBu', aspect='auto')
    plt.colorbar()
    plt.title('Positional Encoding Patterns')
    plt.xlabel('Position in Sequence')
    plt.ylabel('Embedding Dimension')
    
    plt.subplot(1, 2, 2)
    plt.plot(pos_encoding[:, :20])  # Plot first 20 dimensions
    plt.title('Positional Encoding Values (first 20 dims)')
    plt.xlabel('Position in Sequence')
    plt.ylabel('Encoding Value')
    plt.legend([f'Dim {i}' for i in range(20)], ncol=4, fontsize=8)
    plt.tight_layout()
    plt.savefig('positional_encoding.png', dpi=150, bbox_inches='tight')
    print("Saved positional encoding visualization!")
    
    # Step 3: Apply self-attention
    print(f"\n{'Step 3: Apply Self-Attention':-^70}")
    d_k = 64  # Dimension for Q, K, V
    attention = SelfAttention(d_model, d_k)
    output, attention_weights = attention.forward(embeddings_with_pos)
    
    print(f"\nOutput shape: {output.shape}")
    print(f"Attention weights shape: {attention_weights.shape}")
    
    # Step 4: Visualize attention patterns
    print(f"\n{'Step 4: Visualize Attention':-^70}")
    visualize_attention(attention_weights, tokens)
    plt.savefig('attention_single_head.png', dpi=150, bbox_inches='tight')
    print("Saved single-head attention visualization!")
    
    # Analyze which words "it" attends to
    it_index = tokens.index("it")
    it_attention = attention_weights[it_index]
    
    print(f"\nWhat does 'it' attend to?")
    print("-" * 70)
    for i, (token, weight) in enumerate(sorted(zip(tokens, it_attention), 
                                               key=lambda x: x[1], 
                                               reverse=True)):
        print(f"{token:15s} → {weight:.4f} {'█' * int(weight * 50)}")
    
    return embeddings_with_pos, attention_weights, tokens


def demo_multi_head_attention():
    """
    Demonstrate multi-head attention.
    """
    print("\n" + "=" * 70)
    print("MULTI-HEAD ATTENTION DEMO")
    print("=" * 70)
    
    # Example sentence
    sentence = "The animal didn't cross the street because it was tired"
    tokens = sentence.split()
    
    # Hyperparameters
    d_model = 512
    num_heads = 8
    seq_len = len(tokens)
    
    # Create input
    embeddings = np.random.randn(seq_len, d_model)
    pos_encoding = PositionalEncoding.create(seq_len, d_model)
    input_seq = embeddings + pos_encoding
    
    # Apply multi-head attention
    print(f"\n{'Processing with {num_heads} Attention Heads':-^70}")
    mha = MultiHeadAttention(d_model, num_heads)
    output, all_attention_weights = mha.forward(input_seq)
    
    print(f"\nFinal output shape: {output.shape}")
    print(f"Number of attention heads: {len(all_attention_weights)}")
    
    # Visualize each head
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    axes = axes.flatten()
    
    for i, attention_weights in enumerate(all_attention_weights):
        ax = axes[i]
        sns.heatmap(
            attention_weights,
            xticklabels=tokens,
            yticklabels=tokens,
            cmap='YlOrRd',
            ax=ax,
            cbar=False,
            annot=False
        )
        ax.set_title(f'Head {i+1}', fontweight='bold')
        if i >= 4:
            ax.set_xlabel('Key')
        if i % 4 == 0:
            ax.set_ylabel('Query')
    
    plt.suptitle('Multi-Head Attention Patterns (8 heads)', 
                 fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig('attention_multi_head.png', dpi=150, bbox_inches='tight')
    print("\nSaved multi-head attention visualization!")
    
    # Analyze what different heads learn
    print(f"\n{'What Different Heads Learn':-^70}")
    it_index = tokens.index("it")
    
    for head_idx, attention in enumerate(all_attention_weights[:4]):  # Show first 4 heads
        it_attention = attention[it_index]
        top_word_idx = np.argmax(it_attention)
        top_word = tokens[top_word_idx]
        top_weight = it_attention[top_word_idx]
        
        print(f"Head {head_idx+1}: 'it' → '{top_word}' (weight: {top_weight:.3f})")


def main():
    """Run all demonstrations."""
    print("\n" + "🚀" * 35)
    print("MINI-TRANSFORMER: SELF-ATTENTION FROM SCRATCH")
    print("🚀" * 35)
    
    # Demo 1: Single-head self-attention
    embeddings, attention_weights, tokens = demo_self_attention()
    
    # Demo 2: Multi-head attention
    demo_multi_head_attention()
    
    print("\n" + "=" * 70)
    print("✅ DEMOS COMPLETE!")
    print("=" * 70)
    print("\nGenerated visualizations:")
    print("  1. positional_encoding.png - How position is encoded")
    print("  2. attention_single_head.png - Single attention head patterns")
    print("  3. attention_multi_head.png - 8 parallel attention heads")
    print("\nKey Takeaways:")
    print("  • Self-attention lets words 'look at' each other")
    print("  • Attention weights show what the model focuses on")
    print("  • Multi-head learns different relationship patterns")
    print("  • Positional encoding gives sense of word order")
    print("\n" + "🎉" * 35)


if __name__ == "__main__":
    main()
