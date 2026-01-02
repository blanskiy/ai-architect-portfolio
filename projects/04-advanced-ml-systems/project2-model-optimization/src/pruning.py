"""
Model Pruning
Remove unimportant weights to reduce model size and computation.

Pruning strategies:
- Unstructured: Remove individual weights (highest compression, needs sparse libraries)
- Structured: Remove entire neurons/channels (easier to accelerate)
- Gradual: Prune incrementally during training (best accuracy)

Typical workflow:
1. Train full model
2. Identify unimportant weights
3. Remove (set to zero) or physically delete
4. Fine-tune to recover accuracy
"""

import logging
from typing import Optional, List, Dict, Any, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import copy

import torch
import torch.nn as nn
import torch.nn.utils.prune as prune
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PruningMethod(Enum):
    """Pruning methods."""
    MAGNITUDE = "magnitude"          # Remove smallest weights
    RANDOM = "random"                # Remove random weights
    L1_STRUCTURED = "l1_structured"  # Remove filters with smallest L1 norm
    LN_STRUCTURED = "ln_structured"  # Remove filters with smallest Ln norm


class PruningGranularity(Enum):
    """Granularity of pruning."""
    UNSTRUCTURED = "unstructured"    # Individual weights
    STRUCTURED = "structured"        # Entire channels/filters
    BLOCK = "block"                  # Blocks of weights


@dataclass
class PruningConfig:
    """Configuration for pruning."""
    method: PruningMethod = PruningMethod.MAGNITUDE
    granularity: PruningGranularity = PruningGranularity.UNSTRUCTURED
    
    # Target sparsity (fraction of weights to remove)
    sparsity: float = 0.5
    
    # Layers to prune (None = all supported layers)
    layers_to_prune: Optional[List[str]] = None
    
    # Layers to exclude from pruning
    layers_to_exclude: Optional[List[str]] = None
    
    # For structured pruning, which dimension to prune
    pruning_dim: int = 0  # 0 = output channels, 1 = input channels
    
    # For gradual pruning
    initial_sparsity: float = 0.0
    final_sparsity: float = 0.5
    pruning_steps: int = 10


class ModelPruner:
    """
    Prunes PyTorch models to reduce size and computation.
    
    Usage:
        pruner = ModelPruner(config=PruningConfig(sparsity=0.5))
        
        # One-shot pruning
        pruned_model = pruner.prune_model(model)
        
        # Gradual pruning during training
        for epoch in range(num_epochs):
            train(model)
            pruner.step()  # Increase sparsity
        pruner.finalize(model)
    """
    
    def __init__(self, config: Optional[PruningConfig] = None):
        self.config = config or PruningConfig()
        self._step_count = 0
    
    def prune_model(
        self,
        model: nn.Module,
        sparsity: Optional[float] = None,
    ) -> nn.Module:
        """
        Apply one-shot pruning to model.
        
        Args:
            model: PyTorch model
            sparsity: Fraction of weights to remove (overrides config)
        
        Returns:
            Pruned model (same instance, modified in place)
        """
        
        sparsity = sparsity or self.config.sparsity
        
        logger.info(f"Pruning model with {sparsity*100:.1f}% sparsity")
        
        # Get layers to prune
        layers = self._get_prunable_layers(model)
        
        logger.info(f"Found {len(layers)} prunable layers")
        
        # Apply pruning to each layer
        for name, module in layers:
            if self.config.granularity == PruningGranularity.UNSTRUCTURED:
                self._prune_unstructured(module, sparsity)
            else:
                self._prune_structured(module, sparsity)
        
        # Calculate actual sparsity
        actual_sparsity = self.calculate_sparsity(model)
        logger.info(f"Actual model sparsity: {actual_sparsity*100:.1f}%")
        
        return model
    
    def _get_prunable_layers(
        self,
        model: nn.Module,
    ) -> List[Tuple[str, nn.Module]]:
        """Get list of layers that can be pruned."""
        
        prunable_types = (nn.Conv2d, nn.Linear, nn.Conv1d)
        layers = []
        
        for name, module in model.named_modules():
            # Skip if not prunable type
            if not isinstance(module, prunable_types):
                continue
            
            # Check exclusion list
            if self.config.layers_to_exclude:
                if any(excl in name for excl in self.config.layers_to_exclude):
                    continue
            
            # Check inclusion list
            if self.config.layers_to_prune:
                if not any(incl in name for incl in self.config.layers_to_prune):
                    continue
            
            layers.append((name, module))
        
        return layers
    
    def _prune_unstructured(self, module: nn.Module, sparsity: float):
        """Apply unstructured (weight-level) pruning."""
        
        if self.config.method == PruningMethod.MAGNITUDE:
            prune.l1_unstructured(module, name='weight', amount=sparsity)
        elif self.config.method == PruningMethod.RANDOM:
            prune.random_unstructured(module, name='weight', amount=sparsity)
    
    def _prune_structured(self, module: nn.Module, sparsity: float):
        """Apply structured (channel-level) pruning."""
        
        if self.config.method == PruningMethod.L1_STRUCTURED:
            prune.ln_structured(
                module,
                name='weight',
                amount=sparsity,
                n=1,  # L1 norm
                dim=self.config.pruning_dim
            )
        elif self.config.method == PruningMethod.LN_STRUCTURED:
            prune.ln_structured(
                module,
                name='weight',
                amount=sparsity,
                n=2,  # L2 norm
                dim=self.config.pruning_dim
            )
    
    def calculate_sparsity(self, model: nn.Module) -> float:
        """
        Calculate the sparsity (fraction of zero weights) of a model.
        
        Args:
            model: PyTorch model
        
        Returns:
            Sparsity as fraction [0, 1]
        """
        
        total_params = 0
        zero_params = 0
        
        for name, param in model.named_parameters():
            if 'weight' in name:
                total_params += param.numel()
                zero_params += (param == 0).sum().item()
        
        return zero_params / total_params if total_params > 0 else 0.0
    
    def remove_pruning_reparameterization(self, model: nn.Module) -> nn.Module:
        """
        Make pruning permanent by removing the reparameterization.
        
        After this, the pruned weights are actually removed from the model,
        not just masked. This is needed before saving or exporting.
        
        Args:
            model: Pruned PyTorch model
        
        Returns:
            Model with pruning made permanent
        """
        
        for name, module in model.named_modules():
            if isinstance(module, (nn.Conv2d, nn.Linear, nn.Conv1d)):
                try:
                    prune.remove(module, 'weight')
                except ValueError:
                    # No pruning applied to this layer
                    pass
        
        return model
    
    def get_model_stats(self, model: nn.Module) -> Dict[str, Any]:
        """
        Get statistics about the model.
        
        Args:
            model: PyTorch model
        
        Returns:
            Dict with model statistics
        """
        
        total_params = 0
        zero_params = 0
        layer_stats = []
        
        for name, module in model.named_modules():
            if isinstance(module, (nn.Conv2d, nn.Linear, nn.Conv1d)):
                weight = module.weight.data
                params = weight.numel()
                zeros = (weight == 0).sum().item()
                
                total_params += params
                zero_params += zeros
                
                layer_stats.append({
                    "name": name,
                    "type": type(module).__name__,
                    "params": params,
                    "zeros": zeros,
                    "sparsity": zeros / params if params > 0 else 0,
                })
        
        return {
            "total_params": total_params,
            "zero_params": zero_params,
            "nonzero_params": total_params - zero_params,
            "overall_sparsity": zero_params / total_params if total_params > 0 else 0,
            "layer_stats": layer_stats,
        }


class GradualPruner:
    """
    Implements gradual pruning during training.
    
    Gradual pruning increases sparsity over time, allowing the model
    to adapt. This typically results in better accuracy than one-shot pruning.
    
    Usage:
        pruner = GradualPruner(
            model=model,
            initial_sparsity=0.0,
            final_sparsity=0.9,
            begin_step=1000,
            end_step=10000,
            frequency=100
        )
        
        for step in range(num_steps):
            loss = train_step(model)
            pruner.step()  # Updates pruning masks
        
        pruner.finalize()  # Make pruning permanent
    """
    
    def __init__(
        self,
        model: nn.Module,
        initial_sparsity: float = 0.0,
        final_sparsity: float = 0.9,
        begin_step: int = 0,
        end_step: int = 10000,
        frequency: int = 100,
    ):
        """
        Initialize gradual pruner.
        
        Args:
            model: PyTorch model to prune
            initial_sparsity: Starting sparsity
            final_sparsity: Target sparsity
            begin_step: Step to begin pruning
            end_step: Step to end pruning
            frequency: How often to update pruning (in steps)
        """
        
        self.model = model
        self.initial_sparsity = initial_sparsity
        self.final_sparsity = final_sparsity
        self.begin_step = begin_step
        self.end_step = end_step
        self.frequency = frequency
        
        self.current_step = 0
        self.pruner = ModelPruner()
        
        # Apply initial pruning if needed
        if initial_sparsity > 0:
            self.pruner.prune_model(model, initial_sparsity)
    
    def _get_current_sparsity(self) -> float:
        """Calculate target sparsity for current step."""
        
        if self.current_step < self.begin_step:
            return self.initial_sparsity
        
        if self.current_step >= self.end_step:
            return self.final_sparsity
        
        # Cubic sparsity schedule (common choice)
        progress = (self.current_step - self.begin_step) / (self.end_step - self.begin_step)
        sparsity = self.final_sparsity + (self.initial_sparsity - self.final_sparsity) * (1 - progress) ** 3
        
        return sparsity
    
    def step(self):
        """
        Update pruning based on current step.
        
        Call this after each training step.
        """
        
        self.current_step += 1
        
        # Only update at specified frequency
        if self.current_step % self.frequency != 0:
            return
        
        # Only update during pruning window
        if self.current_step < self.begin_step or self.current_step > self.end_step:
            return
        
        # Calculate and apply new sparsity
        target_sparsity = self._get_current_sparsity()
        
        # Remove old pruning and apply new
        self.pruner.remove_pruning_reparameterization(self.model)
        self.pruner.prune_model(self.model, target_sparsity)
        
        logger.debug(f"Step {self.current_step}: Updated sparsity to {target_sparsity:.3f}")
    
    def finalize(self):
        """Make pruning permanent and remove masks."""
        self.pruner.remove_pruning_reparameterization(self.model)
        
        actual_sparsity = self.pruner.calculate_sparsity(self.model)
        logger.info(f"Pruning finalized. Final sparsity: {actual_sparsity*100:.1f}%")


class StructuredPruner:
    """
    Structured pruning that removes entire channels/filters.
    
    Unlike unstructured pruning, structured pruning actually reduces
    model dimensions, leading to real speedups without sparse libraries.
    """
    
    @staticmethod
    def calculate_importance(
        module: nn.Module,
        method: str = "l1_norm"
    ) -> torch.Tensor:
        """
        Calculate importance scores for each filter/channel.
        
        Args:
            module: Conv2d or Linear module
            method: Importance calculation method
        
        Returns:
            Tensor of importance scores per output channel
        """
        
        weight = module.weight.data
        
        if method == "l1_norm":
            # Sum of absolute values per output channel
            if len(weight.shape) == 4:  # Conv2d
                importance = weight.abs().sum(dim=(1, 2, 3))
            else:  # Linear
                importance = weight.abs().sum(dim=1)
        
        elif method == "l2_norm":
            # L2 norm per output channel
            if len(weight.shape) == 4:  # Conv2d
                importance = weight.pow(2).sum(dim=(1, 2, 3)).sqrt()
            else:  # Linear
                importance = weight.pow(2).sum(dim=1).sqrt()
        
        elif method == "random":
            importance = torch.rand(weight.shape[0])
        
        else:
            raise ValueError(f"Unknown importance method: {method}")
        
        return importance
    
    @staticmethod
    def get_channels_to_prune(
        importance: torch.Tensor,
        prune_ratio: float,
    ) -> List[int]:
        """
        Get indices of channels to prune based on importance.
        
        Args:
            importance: Importance scores per channel
            prune_ratio: Fraction of channels to prune
        
        Returns:
            List of channel indices to prune
        """
        
        num_to_prune = int(len(importance) * prune_ratio)
        
        # Get indices of least important channels
        _, indices = torch.sort(importance)
        channels_to_prune = indices[:num_to_prune].tolist()
        
        return channels_to_prune
    
    @staticmethod
    def prune_conv_layer(
        conv: nn.Conv2d,
        channels_to_keep: List[int],
    ) -> nn.Conv2d:
        """
        Create new Conv2d with only specified output channels.
        
        Args:
            conv: Original Conv2d layer
            channels_to_keep: Indices of output channels to keep
        
        Returns:
            New Conv2d with pruned channels
        """
        
        new_conv = nn.Conv2d(
            in_channels=conv.in_channels,
            out_channels=len(channels_to_keep),
            kernel_size=conv.kernel_size,
            stride=conv.stride,
            padding=conv.padding,
            dilation=conv.dilation,
            groups=conv.groups,
            bias=conv.bias is not None,
        )
        
        # Copy weights for kept channels
        new_conv.weight.data = conv.weight.data[channels_to_keep]
        
        if conv.bias is not None:
            new_conv.bias.data = conv.bias.data[channels_to_keep]
        
        return new_conv


# Utility functions

def count_parameters(model: nn.Module) -> int:
    """Count total trainable parameters."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def count_nonzero_parameters(model: nn.Module) -> int:
    """Count non-zero parameters."""
    return sum((p != 0).sum().item() for p in model.parameters())


def estimate_flops_reduction(sparsity: float, structured: bool = False) -> float:
    """
    Estimate FLOPs reduction from pruning.
    
    Args:
        sparsity: Model sparsity
        structured: Whether structured pruning was used
    
    Returns:
        Estimated FLOPs reduction factor
    """
    
    if structured:
        # Structured pruning gives ~linear speedup
        return 1.0 / (1.0 - sparsity)
    else:
        # Unstructured pruning needs sparse libraries
        # Effective speedup depends on hardware/library support
        # Rough estimate: ~50% of theoretical maximum
        return 1.0 / (1.0 - sparsity * 0.5)


# Example usage
if __name__ == "__main__":
    import torchvision.models as models
    
    # Load model
    model = models.resnet18(pretrained=True)
    
    # Create pruner
    config = PruningConfig(
        method=PruningMethod.MAGNITUDE,
        granularity=PruningGranularity.UNSTRUCTURED,
        sparsity=0.5
    )
    pruner = ModelPruner(config)
    
    # Get stats before pruning
    print("Before pruning:")
    print(f"  Total params: {count_parameters(model):,}")
    print(f"  Sparsity: {pruner.calculate_sparsity(model)*100:.1f}%")
    
    # Prune
    pruner.prune_model(model)
    
    # Get stats after pruning
    print("\nAfter pruning:")
    print(f"  Total params: {count_parameters(model):,}")
    print(f"  Sparsity: {pruner.calculate_sparsity(model)*100:.1f}%")
    print(f"  Non-zero params: {count_nonzero_parameters(model):,}")
