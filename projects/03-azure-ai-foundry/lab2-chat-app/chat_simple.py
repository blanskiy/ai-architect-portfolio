"""Simple Chat Completion with Azure OpenAI"""

from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv

load_dotenv()

# Get token provider for Azure AD auth
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default"
)

# Initialize client - use Azure OpenAI endpoint (not project endpoint!)
client = AzureOpenAI(
    azure_endpoint="https://blans-mjiyrqgp-westus.openai.azure.com/",  # Fixed!
    azure_ad_token_provider=token_provider,
    api_version="2024-10-21"
)

# Simple chat completion
response = client.chat.completions.create(
    model="gpt-4o",  # Your deployment name
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is Azure AI Foundry in one sentence?"}
    ]
)

print("Response:")
print(response.choices[0].message.content)