#!/usr/bin/env python3
"""Batch manager for efficient request processing."""

import asyncio
import torch
from typing import List, Tuple
import time
import logging

logger = logging.getLogger(__name__)


class BatchManager:
    """Manages batching of inference requests for improved throughput."""
    
    def __init__(self, max_batch_size: int = 8, max_wait_time: float = 0.05):
        """
        Initialize batch manager.
        
        Args:
            max_batch_size: Maximum number of requests to batch together
            max_wait_time: Maximum time (seconds) to wait for batch to fill
        """
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time
        
        # Queue to hold pending requests
        self.queue = []
        
        # Lock for thread-safe operations
        self.lock = asyncio.Lock()
        
        # Event to signal when batch is ready
        self.batch_ready = asyncio.Event()
        
        # Processing task
        self.processing_task = None
        
        logger.info(f"BatchManager initialized: max_batch_size={max_batch_size}, max_wait_time={max_wait_time}s")
    
    async def add_to_batch(self, tensor: torch.Tensor, request_id: str) -> Tuple[torch.Tensor, float]:
        """
        Add a request to the batch and wait for result.
        
        Args:
            tensor: Input tensor for this request
            request_id: Unique identifier for this request
            
        Returns:
            Tuple of (output_tensor, inference_time)
        """
        # Create a future to hold the result
        future = asyncio.Future()
        
        # Add to queue
        async with self.lock:
            self.queue.append({
                'tensor': tensor,
                'request_id': request_id,
                'future': future,
                'arrival_time': time.time()
            })
            queue_size = len(self.queue)
            logger.debug(f"Request {request_id} added to queue. Queue size: {queue_size}")
        
        # Wait for result
        result = await future
        return result
    
    async def process_batch(self, model, batch_items: List[dict]) -> None:
        """
        Process a batch of requests.
        
        Args:
            model: PyTorch model to use for inference
            batch_items: List of request items to process
        """
        if not batch_items:
            return
        
        batch_size = len(batch_items)
        logger.info(f"Processing batch of size {batch_size}")
        
        start_time = time.time()
        
        try:
            # Stack tensors into a batch
            batch_tensor = torch.stack([item['tensor'] for item in batch_items])
            logger.debug(f"Batch tensor shape: {batch_tensor.shape}")
            
            # Run inference
            with torch.no_grad():
                batch_output = model(batch_tensor)
            
            inference_time = time.time() - start_time
            logger.info(f"Batch inference completed in {inference_time*1000:.2f}ms")
            
            # Split results and set futures
            for i, item in enumerate(batch_items):
                output = batch_output[i]
                item['future'].set_result((output, inference_time))
                logger.debug(f"Result set for request {item['request_id']}")
        
        except Exception as e:
            logger.error(f"Batch processing error: {e}", exc_info=True)
            # Set exception for all futures
            for item in batch_items:
                if not item['future'].done():
                    item['future'].set_exception(e)
    
    async def run_batching_loop(self, model):
        """
        Main batching loop that collects and processes batches.
        
        Args:
            model: PyTorch model to use for inference
        """
        logger.info("Batching loop started")
        
        while True:
            try:
                # Wait for queue to have items or timeout
                await asyncio.sleep(self.max_wait_time)
                
                # Get batch to process
                async with self.lock:
                    if not self.queue:
                        continue
                    
                    # Take up to max_batch_size items
                    batch_items = self.queue[:self.max_batch_size]
                    self.queue = self.queue[self.max_batch_size:]
                
                # Process the batch
                if batch_items:
                    await self.process_batch(model, batch_items)
            
            except asyncio.CancelledError:
                logger.info("Batching loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in batching loop: {e}", exc_info=True)
    
    def start(self, model):
        """Start the batching loop."""
        if self.processing_task is None:
            self.processing_task = asyncio.create_task(self.run_batching_loop(model))
            logger.info("Batching loop task created")
    
    def stop(self):
        """Stop the batching loop."""
        if self.processing_task:
            self.processing_task.cancel()
            self.processing_task = None
            logger.info("Batching loop stopped")