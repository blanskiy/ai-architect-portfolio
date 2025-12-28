"""Interactive Chat Application with Conversation History"""

from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

# Setup Azure OpenAI client
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default"
)

client = AzureOpenAI(
    azure_endpoint="https://blans-mjiyrqgp-westus.openai.azure.com/",
    azure_ad_token_provider=token_provider,
    api_version="2024-10-21"
)

class SalesChatbot:
    def __init__(self):
        self.system_prompt = """You are a STIHL Sales Analytics Expert. Your role is to:
1. Analyze sales data and identify trends
2. Provide actionable business insights
3. Create clear summaries for executives

Always structure your responses with:
- **Key Finding**: The main insight
- **Supporting Data**: Relevant numbers
- **Recommendation**: What action to take

Be concise but thorough."""
        
        # Conversation history starts with system message
        self.messages = [{"role": "system", "content": self.system_prompt}]
    
    def chat(self, user_message: str) -> str:
        # Add user message to history
        self.messages.append({"role": "user", "content": user_message})
        
        # Get response
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=self.messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        # Extract and store assistant response
        assistant_message = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": assistant_message})
        
        return assistant_message
    
    def reset(self):
        """Clear conversation history"""
        self.messages = [{"role": "system", "content": self.system_prompt}]
        print("\n✓ Conversation reset.\n")


def main():
    print("=" * 60)
    print("   STIHL Sales Analytics Chatbot")
    print("=" * 60)
    print("\nCommands: 'quit' to exit, 'reset' to start over\n")
    
    chatbot = SalesChatbot()
    
    while True:
        user_input = input("You: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() == 'quit':
            print("Goodbye!")
            break
        
        if user_input.lower() == 'reset':
            chatbot.reset()
            continue
        
        response = chatbot.chat(user_input)
        print(f"\nAssistant: {response}\n")


if __name__ == "__main__":
    main()