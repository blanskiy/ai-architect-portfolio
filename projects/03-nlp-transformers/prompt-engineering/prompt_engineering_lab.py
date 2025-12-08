"""
Prompt Engineering Lab - Interactive Testing Suite
Days 3-4: Hands-on Prompt Engineering

This lab provides interactive exercises to practice prompt engineering techniques.
"""

import time
from typing import List, Dict, Tuple, Optional
from azure_openai_config import AzureOpenAIConfig
from prompt_examples import PromptExamples, print_best_practices


class PromptEvaluator:
    """
    Evaluates prompt effectiveness using multiple criteria.
    """
    
    @staticmethod
    def evaluate_prompt(prompt: str) -> Dict:
        """
        Evaluate a prompt based on best practices.
        
        Args:
            prompt: The prompt string to evaluate
            
        Returns:
            Dictionary with scores and recommendations
        """
        score = 0
        max_score = 100
        feedback = []
        
        # Criterion 1: Clarity (20 points)
        if len(prompt) > 20:
            score += 10
            feedback.append("✅ Prompt has sufficient detail")
        else:
            feedback.append("❌ Prompt is too short, add more context")
        
        if any(word in prompt.lower() for word in ['classify', 'extract', 'summarize', 'explain', 'generate']):
            score += 10
            feedback.append("✅ Clear task verb identified")
        else:
            feedback.append("❌ Add a clear action verb (classify, extract, etc.)")
        
        # Criterion 2: Context (20 points)
        if any(word in prompt.lower() for word in ['you are', 'role:', 'context:', 'background:']):
            score += 20
            feedback.append("✅ Context or role provided")
        else:
            feedback.append("⚠️  Consider adding context or role")
        
        # Criterion 3: Examples (20 points)
        if 'example' in prompt.lower() or '→' in prompt or 'input:' in prompt.lower():
            score += 20
            feedback.append("✅ Examples provided (few-shot)")
        else:
            feedback.append("⚠️  Consider adding examples for better results")
        
        # Criterion 4: Output Format (20 points)
        if any(word in prompt.lower() for word in ['json', 'format:', 'structure:', 'template']):
            score += 20
            feedback.append("✅ Output format specified")
        else:
            feedback.append("⚠️  Specify desired output format")
        
        # Criterion 5: Reasoning (20 points)
        if 'step by step' in prompt.lower() or 'think through' in prompt.lower() or 'reasoning' in prompt.lower():
            score += 20
            feedback.append("✅ Encourages step-by-step reasoning")
        else:
            feedback.append("⚠️  Consider adding 'let's think step by step'")
        
        return {
            'score': score,
            'max_score': max_score,
            'percentage': (score / max_score) * 100,
            'grade': PromptEvaluator._get_grade(score, max_score),
            'feedback': feedback
        }
    
    @staticmethod
    def _get_grade(score: int, max_score: int) -> str:
        """Convert score to letter grade."""
        percentage = (score / max_score) * 100
        if percentage >= 90:
            return 'A'
        elif percentage >= 80:
            return 'B'
        elif percentage >= 70:
            return 'C'
        elif percentage >= 60:
            return 'D'
        else:
            return 'F'
    
    @staticmethod
    def compare_prompts(prompt1: str, prompt2: str) -> None:
        """Compare two prompts side by side."""
        print("\n" + "="*70)
        print("PROMPT COMPARISON")
        print("="*70)
        
        eval1 = PromptEvaluator.evaluate_prompt(prompt1)
        eval2 = PromptEvaluator.evaluate_prompt(prompt2)
        
        print(f"\n{'Prompt 1':^35} | {'Prompt 2':^35}")
        print("─"*70)
        print(f"{'Score: ' + str(eval1['score']):<35} | {'Score: ' + str(eval2['score']):<35}")
        print(f"{'Grade: ' + eval1['grade']:<35} | {'Grade: ' + eval2['grade']:<35}")
        
        print("\nPrompt 1 Feedback:")
        for item in eval1['feedback']:
            print(f"  {item}")
        
        print("\nPrompt 2 Feedback:")
        for item in eval2['feedback']:
            print(f"  {item}")
        
        if eval1['score'] > eval2['score']:
            print(f"\n🏆 Prompt 1 is better (+{eval1['score'] - eval2['score']} points)")
        elif eval2['score'] > eval1['score']:
            print(f"\n🏆 Prompt 2 is better (+{eval2['score'] - eval1['score']} points)")
        else:
            print("\n🤝 Both prompts score equally")


class PromptEngineeringLab:
    """
    Interactive lab for practicing prompt engineering.
    """
    
    def __init__(self):
        """Initialize the lab with Azure OpenAI configuration."""
        self.config = AzureOpenAIConfig()
        self.client = self.config.get_client()
        self.examples = PromptExamples()
        self.evaluator = PromptEvaluator()
    
    def run_exercise(self, exercise_name: str, user_prompt: str, 
                    temperature: float = 0.7) -> Dict:
        """
        Run a prompt engineering exercise.
        
        Args:
            exercise_name: Name of the exercise
            user_prompt: The prompt to test
            temperature: Temperature setting
            
        Returns:
            Results dictionary
        """
        print(f"\n{'='*70}")
        print(f"📝 EXERCISE: {exercise_name}")
        print('='*70)
        
        # Evaluate the prompt
        evaluation = self.evaluator.evaluate_prompt(user_prompt)
        
        print(f"\n📊 Prompt Quality Assessment:")
        print(f"   Score: {evaluation['score']}/{evaluation['max_score']} ({evaluation['percentage']:.0f}%)")
        print(f"   Grade: {evaluation['grade']}")
        print(f"\n   Feedback:")
        for item in evaluation['feedback']:
            print(f"   {item}")
        
        # Test with Azure OpenAI
        print(f"\n🤖 Testing with Azure OpenAI (temperature={temperature})...")
        
        messages = [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": user_prompt}
        ]
        
        start_time = time.time()
        response = self.config.create_completion(
            self.client, 
            messages, 
            temperature=temperature
        )
        end_time = time.time()
        
        if response:
            result = response['choices'][0]['message']['content']
            tokens = response['usage']['total_tokens']
            
            print(f"\n✅ Response (took {end_time - start_time:.2f}s, {tokens} tokens):")
            print("─"*70)
            print(result)
            print("─"*70)
            
            return {
                'evaluation': evaluation,
                'response': result,
                'tokens': tokens,
                'time': end_time - start_time,
                'success': True
            }
        else:
            print("❌ Failed to get response")
            return {
                'evaluation': evaluation,
                'success': False
            }
    
    def exercise_1_zero_shot(self):
        """Exercise 1: Practice zero-shot prompting."""
        print("\n" + "🎯"*35)
        print("EXERCISE 1: ZERO-SHOT PROMPTING")
        print("🎯"*35)
        
        print("\nTask: Classify customer reviews as positive, negative, or neutral")
        
        bad_prompt = "Classify this review"
        good_prompt = """Classify the sentiment of the following customer review as positive, negative, or neutral.

Review: "The product arrived damaged but customer service was helpful in resolving the issue."

Provide ONLY the classification (positive, negative, or neutral) followed by a one-sentence explanation.

Classification:"""
        
        print("\n" + "─"*70)
        print("BAD PROMPT EXAMPLE:")
        print("─"*70)
        print(bad_prompt)
        
        self.run_exercise("Bad Zero-Shot Prompt", bad_prompt, temperature=0.0)
        
        print("\n" + "─"*70)
        print("GOOD PROMPT EXAMPLE:")
        print("─"*70)
        print(good_prompt)
        
        self.run_exercise("Good Zero-Shot Prompt", good_prompt, temperature=0.0)
        
        # Compare
        self.evaluator.compare_prompts(bad_prompt, good_prompt)
    
    def exercise_2_few_shot(self):
        """Exercise 2: Practice few-shot prompting."""
        print("\n" + "🎯"*35)
        print("EXERCISE 2: FEW-SHOT PROMPTING")
        print("🎯"*35)
        
        print("\nTask: Extract structured data from product descriptions")
        
        few_shot_prompt = """Extract product information in JSON format.

Examples:
Input: "iPhone 14 Pro, 256GB, Gold"
Output: {"model": "iPhone 14 Pro", "storage": "256GB", "color": "Gold"}

Input: "Samsung Galaxy S23, 128GB, Phantom Black"
Output: {"model": "Samsung Galaxy S23", "storage": "128GB", "color": "Phantom Black"}

Input: "Google Pixel 7, 256GB, Snow"
Output: {"model": "Google Pixel 7", "storage": "256GB", "color": "Snow"}

Now extract from this:
Input: "MacBook Pro 14-inch, M3 chip, 16GB RAM, 512GB SSD, Space Gray"
Output:"""
        
        self.run_exercise("Few-Shot Data Extraction", few_shot_prompt, temperature=0.0)
    
    def exercise_3_chain_of_thought(self):
        """Exercise 3: Practice chain-of-thought prompting."""
        print("\n" + "🎯"*35)
        print("EXERCISE 3: CHAIN-OF-THOUGHT PROMPTING")
        print("🎯"*35)
        
        print("\nTask: Solve a multi-step reasoning problem")
        
        direct_prompt = """A company has 50 employees. They hire 20% more employees, then 10% of the total quit. How many employees remain?"""
        
        cot_prompt = """A company has 50 employees. They hire 20% more employees, then 10% of the total quit. How many employees remain?

Let's solve this step by step:
1. First, calculate how many employees are hired
2. Then, calculate the new total
3. Next, calculate how many quit
4. Finally, calculate how many remain

Solution:"""
        
        print("\n" + "─"*70)
        print("❌ BAD PROMPT (Without Chain-of-Thought):")
        print("─"*70)
        print(direct_prompt)
        print("\n⚠️  Problem: No encouragement to show reasoning steps")
        
        self.run_exercise("Direct Problem Solving", direct_prompt, temperature=0.0)
        
        print("\n" + "─"*70)
        print("✅ GOOD PROMPT (With Chain-of-Thought):")
        print("─"*70)
        print(cot_prompt)
        print("\n💡 Key Addition: 'Let's solve this step by step' with numbered steps")
        
        self.run_exercise("Chain-of-Thought Problem Solving", cot_prompt, temperature=0.0)
    
    def exercise_4_role_prompting(self):
        """Exercise 4: Practice role-based prompting."""
        print("\n" + "🎯"*35)
        print("EXERCISE 4: ROLE-BASED PROMPTING")
        print("🎯"*35)
        
        print("\nTask: Get expert advice on cloud architecture")
        
        role_prompt = """You are a Senior Azure Solutions Architect with 15 years of experience in designing enterprise cloud solutions.

A client asks: "We're building a real-time data analytics platform that needs to process 1 million events per second. Should we use Azure Event Hubs or Azure Service Bus?"

Provide a detailed technical recommendation considering:
- Performance and throughput requirements
- Cost implications
- Operational complexity
- Scalability
- Use case fit

Recommendation:"""
        
        self.run_exercise("Azure Architecture Consulting", role_prompt, temperature=0.3)
    
    def exercise_5_temperature_comparison(self):
        """Exercise 5: Compare different temperature settings."""
        print("\n" + "🎯"*35)
        print("EXERCISE 5: TEMPERATURE COMPARISON")
        print("🎯"*35)
        
        print("\nTask: Generate a creative product name")
        
        creative_prompt = """Generate 5 creative names for a new AI-powered code review tool that helps developers write better code.

Each name should be:
- Memorable and catchy
- Related to code or development
- Easy to pronounce
- Available as a .com domain (hypothetically)

Names:"""
        
        print("\n" + "─"*70)
        print("LOW TEMPERATURE (0.3) - More deterministic:")
        print("─"*70)
        self.run_exercise("Creative Names (Low Temp)", creative_prompt, temperature=0.3)
        
        print("\n" + "─"*70)
        print("HIGH TEMPERATURE (0.9) - More creative:")
        print("─"*70)
        self.run_exercise("Creative Names (High Temp)", creative_prompt, temperature=0.9)
    
    def exercise_6_constrained_output(self):
        """Exercise 6: Practice constrained output formats."""
        print("\n" + "🎯"*35)
        print("EXERCISE 6: CONSTRAINED OUTPUT")
        print("🎯"*35)
        
        print("\nTask: Code review with structured output")
        
        constrained_prompt = """Review this Python code and respond ONLY with valid JSON in this exact format:

{
  "has_issues": true/false,
  "severity": "low"|"medium"|"high",
  "issues": [
    {
      "type": "bug"|"security"|"performance"|"style",
      "description": "string",
      "line": number,
      "suggestion": "string"
    }
  ],
  "overall_score": 0-10
}

Code to review:
```python
def calculate_discount(price, customer_type):
    if customer_type == "premium":
        discount = price * 0.2
    elif customer_type == "regular":
        discount = price * 0.1
    return price - discount
```

JSON Response:"""
        
        self.run_exercise("Structured Code Review", constrained_prompt, temperature=0.0)
    
    def run_all_exercises(self):
        """Run all exercises in sequence."""
        print("\n" + "🚀"*35)
        print("PROMPT ENGINEERING LAB - COMPLETE WORKSHOP")
        print("🚀"*35)
        
        print("\nThis lab will guide you through 6 hands-on exercises:")
        print("1. Zero-Shot Prompting")
        print("2. Few-Shot Prompting")
        print("3. Chain-of-Thought")
        print("4. Role-Based Prompting")
        print("5. Temperature Comparison")
        print("6. Constrained Output")
        
        input("\nPress Enter to start Exercise 1...")
        self.exercise_1_zero_shot()
        
        input("\nPress Enter to continue to Exercise 2...")
        self.exercise_2_few_shot()
        
        input("\nPress Enter to continue to Exercise 3...")
        self.exercise_3_chain_of_thought()
        
        input("\nPress Enter to continue to Exercise 4...")
        self.exercise_4_role_prompting()
        
        input("\nPress Enter to continue to Exercise 5...")
        self.exercise_5_temperature_comparison()
        
        input("\nPress Enter to continue to Exercise 6...")
        self.exercise_6_constrained_output()
        
        print("\n" + "🎉"*35)
        print("LAB COMPLETE! You've practiced all major prompt engineering techniques!")
        print("🎉"*35)


def main():
    """Main function to run the lab."""
    print("\n" + "╔" + "═"*68 + "╗")
    print("║" + " "*15 + "PROMPT ENGINEERING LAB - DAYS 3-4" + " "*20 + "║")
    print("╚" + "═"*68 + "╝")
    
    # Show menu
    print("\nWhat would you like to do?")
    print("1. Run all exercises (full workshop)")
    print("2. Run individual exercise")
    print("3. View best practices")
    print("4. View example prompts")
    print("5. Test your own prompt")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    lab = PromptEngineeringLab()
    
    if choice == "1":
        lab.run_all_exercises()
    elif choice == "2":
        print("\nAvailable exercises:")
        print("1. Zero-Shot Prompting")
        print("2. Few-Shot Prompting")
        print("3. Chain-of-Thought")
        print("4. Role-Based Prompting")
        print("5. Temperature Comparison")
        print("6. Constrained Output")
        
        ex_choice = input("\nChoose exercise (1-6): ").strip()
        
        exercises = {
            "1": lab.exercise_1_zero_shot,
            "2": lab.exercise_2_few_shot,
            "3": lab.exercise_3_chain_of_thought,
            "4": lab.exercise_4_role_prompting,
            "5": lab.exercise_5_temperature_comparison,
            "6": lab.exercise_6_constrained_output
        }
        
        if ex_choice in exercises:
            exercises[ex_choice]()
        else:
            print("Invalid choice")
    elif choice == "3":
        print_best_practices()
    elif choice == "4":
        from prompt_examples import demonstrate_examples
        demonstrate_examples()
    elif choice == "5":
        print("\nEnter your prompt (end with empty line):")
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        
        user_prompt = "\n".join(lines)
        
        if user_prompt:
            temp = input("\nEnter temperature (0.0-1.0, default 0.7): ").strip()
            temp = float(temp) if temp else 0.7
            
            lab.run_exercise("Custom Prompt Test", user_prompt, temperature=temp)
        else:
            print("No prompt entered")
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
