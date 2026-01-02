"""
Sample Models for Optimization Testing
Provides simple models to test the optimization pipeline.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class SimpleCNN(nn.Module):
    """
    Simple CNN for testing optimization techniques.
    Small enough to optimize quickly, complex enough to be meaningful.
    """
    
    def __init__(self, num_classes: int = 10):
        super().__init__()
        
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(32)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(64)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm2d(128)
        
        self.pool = nn.MaxPool2d(2, 2)
        self.dropout = nn.Dropout(0.25)
        
        # Assuming input is 32x32 (like CIFAR-10)
        self.fc1 = nn.Linear(128 * 4 * 4, 256)
        self.fc2 = nn.Linear(256, num_classes)
    
    def forward(self, x):
        # Conv block 1
        x = self.pool(F.relu(self.bn1(self.conv1(x))))
        
        # Conv block 2
        x = self.pool(F.relu(self.bn2(self.conv2(x))))
        
        # Conv block 3
        x = self.pool(F.relu(self.bn3(self.conv3(x))))
        
        # Flatten
        x = x.view(x.size(0), -1)
        
        # FC layers
        x = self.dropout(F.relu(self.fc1(x)))
        x = self.fc2(x)
        
        return x


class SimpleImageClassifier(nn.Module):
    """
    Simple image classifier for 224x224 inputs.
    Compatible with ImageNet-style preprocessing.
    """
    
    def __init__(self, num_classes: int = 1000):
        super().__init__()
        
        self.features = nn.Sequential(
            # Block 1
            nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2, padding=1),
            
            # Block 2
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
            
            # Block 3
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
            
            # Block 4
            nn.Conv2d(256, 512, kernel_size=3, padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(512, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.5),
            nn.Linear(256, num_classes),
        )
    
    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x


class SimpleTransformerBlock(nn.Module):
    """
    Simple transformer block for testing.
    """
    
    def __init__(self, embed_dim: int = 256, num_heads: int = 8):
        super().__init__()
        
        self.attention = nn.MultiheadAttention(embed_dim, num_heads, batch_first=True)
        self.norm1 = nn.LayerNorm(embed_dim)
        self.norm2 = nn.LayerNorm(embed_dim)
        
        self.ffn = nn.Sequential(
            nn.Linear(embed_dim, embed_dim * 4),
            nn.GELU(),
            nn.Linear(embed_dim * 4, embed_dim),
        )
    
    def forward(self, x):
        # Self-attention with residual
        attn_out, _ = self.attention(x, x, x)
        x = self.norm1(x + attn_out)
        
        # FFN with residual
        x = self.norm2(x + self.ffn(x))
        
        return x


class SimpleNLPModel(nn.Module):
    """
    Simple NLP model for testing optimization on transformer-like models.
    """
    
    def __init__(
        self,
        vocab_size: int = 30000,
        embed_dim: int = 256,
        num_heads: int = 8,
        num_layers: int = 4,
        num_classes: int = 2,
        max_seq_len: int = 128,
    ):
        super().__init__()
        
        self.embedding = nn.Embedding(vocab_size, embed_dim)
        self.pos_embedding = nn.Embedding(max_seq_len, embed_dim)
        
        self.layers = nn.ModuleList([
            SimpleTransformerBlock(embed_dim, num_heads)
            for _ in range(num_layers)
        ])
        
        self.classifier = nn.Linear(embed_dim, num_classes)
    
    def forward(self, x):
        batch_size, seq_len = x.shape
        
        # Embeddings
        positions = torch.arange(seq_len, device=x.device).unsqueeze(0)
        x = self.embedding(x) + self.pos_embedding(positions)
        
        # Transformer layers
        for layer in self.layers:
            x = layer(x)
        
        # Classification (use CLS token or mean pooling)
        x = x.mean(dim=1)  # Mean pooling
        x = self.classifier(x)
        
        return x


def get_sample_model(model_type: str = "cnn", **kwargs):
    """
    Factory function to get sample models.
    
    Args:
        model_type: "cnn", "imagenet", "nlp"
        **kwargs: Model-specific arguments
    
    Returns:
        PyTorch model
    """
    
    models = {
        "cnn": SimpleCNN,
        "imagenet": SimpleImageClassifier,
        "nlp": SimpleNLPModel,
    }
    
    if model_type not in models:
        raise ValueError(f"Unknown model type: {model_type}. Choose from {list(models.keys())}")
    
    return models[model_type](**kwargs)


def count_parameters(model: nn.Module) -> int:
    """Count total parameters in model."""
    return sum(p.numel() for p in model.parameters())


def get_model_size_mb(model: nn.Module) -> float:
    """Get model size in MB."""
    param_size = sum(p.numel() * p.element_size() for p in model.parameters())
    buffer_size = sum(b.numel() * b.element_size() for b in model.buffers())
    return (param_size + buffer_size) / (1024 * 1024)


# Example usage
if __name__ == "__main__":
    # Create and inspect models
    print("Sample Models for Optimization Testing")
    print("=" * 50)
    
    # CNN model
    cnn = get_sample_model("cnn", num_classes=10)
    print(f"\nSimpleCNN:")
    print(f"  Parameters: {count_parameters(cnn):,}")
    print(f"  Size: {get_model_size_mb(cnn):.2f} MB")
    print(f"  Input: (batch, 3, 32, 32)")
    
    # Test forward pass
    x = torch.randn(1, 3, 32, 32)
    out = cnn(x)
    print(f"  Output shape: {out.shape}")
    
    # ImageNet model
    imagenet = get_sample_model("imagenet", num_classes=1000)
    print(f"\nSimpleImageClassifier:")
    print(f"  Parameters: {count_parameters(imagenet):,}")
    print(f"  Size: {get_model_size_mb(imagenet):.2f} MB")
    print(f"  Input: (batch, 3, 224, 224)")
    
    # Test forward pass
    x = torch.randn(1, 3, 224, 224)
    out = imagenet(x)
    print(f"  Output shape: {out.shape}")
    
    # NLP model
    nlp = get_sample_model("nlp", vocab_size=30000, num_classes=2)
    print(f"\nSimpleNLPModel:")
    print(f"  Parameters: {count_parameters(nlp):,}")
    print(f"  Size: {get_model_size_mb(nlp):.2f} MB")
    print(f"  Input: (batch, seq_len) with vocab indices")
    
    # Test forward pass
    x = torch.randint(0, 30000, (1, 128))
    out = nlp(x)
    print(f"  Output shape: {out.shape}")
