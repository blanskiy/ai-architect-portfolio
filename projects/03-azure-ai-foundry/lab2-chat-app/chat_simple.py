"""Simple Chat Completion with Azure AI Foundry"""

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
import os


load_dotenv()

# Initialize client
client = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint=os.getenv("https://bl-az-foundry.services.ai.azure.com/api/projects/stihl-sales-analytics")
)

# Simple chat completion
response = client.inference.get_chat_completions(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is Azure AI Foundry in one sentence?"}
    ]
)

print("Response:")
print(response.choices[0].message.content)