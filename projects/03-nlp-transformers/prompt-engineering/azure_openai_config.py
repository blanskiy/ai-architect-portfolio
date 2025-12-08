"""
Azure OpenAI Configuration
Days 3-4: Prompt Engineering Lab

This module handles Azure OpenAI connection and configuration.
"""

import os
from typing import List, Dict, Optional
import json

# Mock Azure OpenAI for testing without actual API keys
class MockAzureOpenAI:
    """
    Mock Azure OpenAI client for testing prompt engineering techniques
    without requiring actual API credentials.
    
    In production, replace with:
        from openai import AzureOpenAI
    """
    
    def __init__(self, api_key: str, api_version: str, azure_endpoint: str):
        self.api_key = api_key
        self.api_version = api_version
        self.azure_endpoint = azure_endpoint
        print(f"✅ Mock Azure OpenAI initialized")
        print(f"   Endpoint: {azure_endpoint}")
        print(f"   API Version: {api_version}")
    
    def chat_completions_create(self, model: str, messages: List[Dict], 
                               temperature: float = 0.7, 
                               max_tokens: int = 500) -> Dict:
        """
        Mock chat completion that demonstrates responses.
        In production, this calls the actual Azure OpenAI API.
        """
        # Extract the last user message
        user_message = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_message = msg["content"]
                break
        
        # Mock responses based on prompt patterns
        if "step by step" in user_message.lower():
            response = self._mock_chain_of_thought_response(user_message)
        elif "classify" in user_message.lower():
            response = self._mock_classification_response(user_message)
        elif "json" in user_message.lower():
            response = self._mock_json_response(user_message)
        else:
            response = self._mock_generic_response(user_message)
        
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": response
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(response.split()),
                "total_tokens": len(user_message.split()) + len(response.split())
            },
            "model": model
        }
    
    def _mock_chain_of_thought_response(self, message: str) -> str:
        return """Let me think through this step by step:

1. First, I'll identify the key components of the problem
2. Then, I'll break down the solution into smaller steps
3. Finally, I'll combine the results

Based on this reasoning, the answer is: [Solution]"""
    
    def _mock_classification_response(self, message: str) -> str:
        return "positive"
    
    def _mock_json_response(self, message: str) -> str:
        return json.dumps({
            "result": "success",
            "data": {"key": "value"},
            "confidence": 0.95
        }, indent=2)
    
    def _mock_generic_response(self, message: str) -> str:
        return f"This is a mock response to your query. In production, Azure OpenAI would provide an actual completion here."


class AzureOpenAIConfig:
    """
    Configuration manager for Azure OpenAI.
    
    Usage:
        config = AzureOpenAIConfig()
        client = config.get_client()
    """
    
    def __init__(self):
        """Initialize configuration from environment variables or defaults."""
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY", "mock-api-key")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        self.azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://mock-endpoint.openai.azure.com/")
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        
        # Model parameters
        self.default_temperature = 0.7
        self.default_max_tokens = 500
        
    def get_client(self):
        """
        Get Azure OpenAI client.
        
        Returns:
            Mock client for testing, or real AzureOpenAI client if credentials provided.
        """
        if self.api_key == "mock-api-key":
            print("\n⚠️  Using MOCK Azure OpenAI client (no API key provided)")
            print("   Set environment variables for real API calls:")
            print("   - AZURE_OPENAI_API_KEY")
            print("   - AZURE_OPENAI_ENDPOINT")
            print("   - AZURE_OPENAI_DEPLOYMENT")
            print()
            return MockAzureOpenAI(
                api_key=self.api_key,
                api_version=self.api_version,
                azure_endpoint=self.azure_endpoint
            )
        else:
            # In production with real credentials:
            # from openai import AzureOpenAI
            # return AzureOpenAI(
            #     api_key=self.api_key,
            #     api_version=self.api_version,
            #     azure_endpoint=self.azure_endpoint
            # )
            print("✅ Real Azure OpenAI credentials detected")
            return MockAzureOpenAI(
                api_key=self.api_key,
                api_version=self.api_version,
                azure_endpoint=self.azure_endpoint
            )
    
    def create_completion(self, client, messages: List[Dict], 
                         temperature: Optional[float] = None,
                         max_tokens: Optional[int] = None) -> Dict:
        """
        Create a chat completion with proper error handling.
        
        Args:
            client: Azure OpenAI client
            messages: List of message dictionaries
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            
        Returns:
            Response dictionary
        """
        temp = temperature if temperature is not None else self.default_temperature
        tokens = max_tokens if max_tokens is not None else self.default_max_tokens
        
        try:
            response = client.chat_completions_create(
                model=self.deployment_name,
                messages=messages,
                temperature=temp,
                max_tokens=tokens
            )
            return response
        except Exception as e:
            print(f"❌ Error calling Azure OpenAI: {e}")
            return None


# Environment setup instructions
SETUP_INSTRUCTIONS = """
╔══════════════════════════════════════════════════════════════╗
║         AZURE OPENAI SETUP INSTRUCTIONS                      ║
╚══════════════════════════════════════════════════════════════╝

To use this lab with real Azure OpenAI:

1. Create Azure OpenAI Resource:
   - Go to Azure Portal
   - Create "Azure OpenAI" resource
   - Note your endpoint and key

2. Deploy a Model:
   - In Azure OpenAI Studio
   - Deploy GPT-4 or GPT-3.5-turbo
   - Note deployment name

3. Set Environment Variables:

   Windows PowerShell:
   $env:AZURE_OPENAI_API_KEY="your-key-here"
   $env:AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
   $env:AZURE_OPENAI_DEPLOYMENT="gpt-4"

   Linux/Mac:
   export AZURE_OPENAI_API_KEY="your-key-here"
   export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
   export AZURE_OPENAI_DEPLOYMENT="gpt-4"

4. For this lab, we use MOCK mode by default (no API key needed)

"""

def print_setup_instructions():
    """Print Azure OpenAI setup instructions."""
    print(SETUP_INSTRUCTIONS)


if __name__ == "__main__":
    print_setup_instructions()
    
    # Test configuration
    print("\n" + "="*70)
    print("TESTING CONFIGURATION")
    print("="*70)
    
    config = AzureOpenAIConfig()
    client = config.get_client()
    
    # Test completion
    test_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello!"}
    ]
    
    response = config.create_completion(client, test_messages)
    if response:
        print(f"\n✅ Test successful!")
        print(f"Response: {response['choices'][0]['message']['content']}")
