"""
Prompt Examples Library
Days 3-4: Prompt Engineering Lab

Comprehensive collection of prompt engineering patterns with examples.
"""

from typing import Dict, List, Tuple


class PromptExamples:
    """
    Collection of prompt engineering examples demonstrating best practices.
    Each example shows BAD vs GOOD prompts with explanations.
    """
    
    @staticmethod
    def zero_shot_examples() -> List[Dict]:
        """Zero-shot prompting examples."""
        return [
            {
                "name": "Sentiment Classification",
                "bad": {
                    "prompt": "Classify this",
                    "problems": [
                        "No context about what to classify",
                        "No output format specified",
                        "Missing the actual content to classify"
                    ]
                },
                "good": {
                    "prompt": """Classify the sentiment of the following customer review as positive, negative, or neutral.

Review: "The product arrived late but works great."

Sentiment:""",
                    "why_better": [
                        "Clear task definition",
                        "Specific output options",
                        "Includes the content to analyze"
                    ]
                }
            },
            {
                "name": "Code Explanation",
                "bad": {
                    "prompt": "Explain this code",
                    "problems": [
                        "No code provided",
                        "No specificity on what to explain",
                        "No target audience specified"
                    ]
                },
                "good": {
                    "prompt": """Explain the following Python function to a beginner programmer.
Focus on what it does, not how it works internally.

def factorial(n):
    if n == 0:
        return 1
    return n * factorial(n-1)

Explanation:""",
                    "why_better": [
                        "Target audience specified (beginner)",
                        "Guidance on focus area",
                        "Code is included"
                    ]
                }
            }
        ]
    
    @staticmethod
    def few_shot_examples() -> List[Dict]:
        """Few-shot prompting examples."""
        return [
            {
                "name": "Email Classification",
                "bad": {
                    "prompt": """Classify emails.

Email: "Meeting at 3pm tomorrow"
Category:""",
                    "problems": [
                        "Only one example (not really few-shot)",
                        "Categories not defined",
                        "No pattern established"
                    ]
                },
                "good": {
                    "prompt": """Classify business emails into categories: Meeting, Action Required, FYI, Urgent.

Examples:
Email: "Can you review this document by EOD?" → Category: Action Required
Email: "Quarterly results attached for your information" → Category: FYI
Email: "URGENT: Server down, need immediate attention" → Category: Urgent
Email: "Team standup moved to 2pm tomorrow" → Category: Meeting

Now classify this email:
Email: "Please approve the budget proposal by Friday"
Category:""",
                    "why_better": [
                        "4 clear examples showing pattern",
                        "All categories demonstrated",
                        "Consistent format"
                    ]
                }
            },
            {
                "name": "Data Extraction",
                "bad": {
                    "prompt": """Extract names.

Text: "John met Sarah yesterday"
Names:""",
                    "problems": [
                        "No format specified",
                        "Limited examples",
                        "Ambiguous output structure"
                    ]
                },
                "good": {
                    "prompt": """Extract person names from text and return as JSON array.

Examples:
Text: "Alice and Bob went to the store" → Names: ["Alice", "Bob"]
Text: "Dr. Smith consulted with Mary Johnson" → Names: ["Dr. Smith", "Mary Johnson"]
Text: "The meeting had no attendees" → Names: []

Now extract names from:
Text: "Yesterday, Michael Chen spoke with Jennifer about the project"
Names:""",
                    "why_better": [
                        "Clear output format (JSON array)",
                        "Multiple examples including edge cases",
                        "Handles empty results"
                    ]
                }
            }
        ]
    
    @staticmethod
    def chain_of_thought_examples() -> List[Dict]:
        """Chain-of-thought prompting examples."""
        return [
            {
                "name": "Math Problem",
                "bad": {
                    "prompt": "If a store has 15 apples and sells 40% of them, then receives 8 more, how many apples does it have?",
                    "problems": [
                        "No encouragement to show work",
                        "Model might skip steps",
                        "Harder to verify logic"
                    ]
                },
                "good": {
                    "prompt": """If a store has 15 apples and sells 40% of them, then receives 8 more, how many apples does it have?

Let's solve this step by step:""",
                    "why_better": [
                        "Magic phrase: 'step by step'",
                        "Encourages showing work",
                        "Makes reasoning visible and verifiable"
                    ]
                }
            },
            {
                "name": "Logic Puzzle",
                "bad": {
                    "prompt": "If all roses are flowers and some flowers fade quickly, do all roses fade quickly?",
                    "problems": [
                        "Complex logic hidden",
                        "Easy to make errors",
                        "No reasoning shown"
                    ]
                },
                "good": {
                    "prompt": """If all roses are flowers and some flowers fade quickly, do all roses fade quickly?

Let's think through the logic:
1. First, what do we know for certain?
2. What can we infer?
3. What's the conclusion?

Analysis:""",
                    "why_better": [
                        "Breaks down reasoning steps",
                        "Structured thinking",
                        "Reduces logical errors"
                    ]
                }
            }
        ]
    
    @staticmethod
    def role_prompting_examples() -> List[Dict]:
        """Role-based prompting examples."""
        return [
            {
                "name": "Technical Consulting",
                "bad": {
                    "prompt": "Should we use microservices or monolith?",
                    "problems": [
                        "No expertise context",
                        "Too generic",
                        "Missing project details"
                    ]
                },
                "good": {
                    "prompt": """You are a Senior Azure Solutions Architect with 15 years of experience in cloud architecture.

Context: A startup with 5 developers is building their first product - a B2B SaaS platform expected to have 100 users in year 1.

Question: Should we build with microservices architecture or a monolithic architecture?

Consider:
- Team size and experience
- Time to market
- Operational complexity
- Future scaling needs

Recommendation:""",
                    "why_better": [
                        "Specific expert role",
                        "Detailed context provided",
                        "Clear decision factors listed"
                    ]
                }
            },
            {
                "name": "Code Review",
                "bad": {
                    "prompt": "Review this code:\n[code]",
                    "problems": [
                        "No review criteria",
                        "No expertise specified",
                        "Unclear what to focus on"
                    ]
                },
                "good": {
                    "prompt": """You are a Python expert who specializes in writing production-grade, maintainable code following best practices.

Review this function for:
1. Code quality and readability
2. Potential bugs or edge cases
3. Performance issues
4. Security concerns

Code:
def process_user_data(data):
    result = eval(data)
    return result

Review:""",
                    "why_better": [
                        "Specific expertise defined",
                        "Clear review criteria",
                        "Focused evaluation points"
                    ]
                }
            }
        ]
    
    @staticmethod
    def constrained_output_examples() -> List[Dict]:
        """Constrained output format examples."""
        return [
            {
                "name": "Structured Bug Report",
                "bad": {
                    "prompt": "Find bugs in this code:\ndef divide(a, b):\n    return a / b",
                    "problems": [
                        "No output format",
                        "Unparseable response",
                        "Can't automate processing"
                    ]
                },
                "good": {
                    "prompt": """Analyze this code for bugs. Respond ONLY in valid JSON format:

{
  "has_bugs": true/false,
  "bug_count": number,
  "bugs": [
    {
      "line": number,
      "description": "string",
      "severity": "low"|"medium"|"high",
      "fix": "string"
    }
  ]
}

Code:
def divide(a, b):
    return a / b

JSON Response:""",
                    "why_better": [
                        "Exact format specified",
                        "Machine-parseable",
                        "Includes all needed fields"
                    ]
                }
            },
            {
                "name": "Feature Extraction",
                "bad": {
                    "prompt": "What are the features of this product?\n'iPhone 14, 128GB, Blue'",
                    "problems": [
                        "Free-form text response",
                        "Inconsistent structure",
                        "Hard to parse"
                    ]
                },
                "good": {
                    "prompt": """Extract product features in this exact format:

MODEL: [product model]
STORAGE: [storage capacity] 
COLOR: [color name]
SCREEN: [screen size if mentioned, else "Not specified"]

Product: "iPhone 14 Pro, 256GB, Space Black, 6.1-inch"

Extraction:""",
                    "why_better": [
                        "Exact format template",
                        "Handles missing data",
                        "Easy to parse"
                    ]
                }
            }
        ]
    
    @staticmethod
    def temperature_examples() -> List[Dict]:
        """Examples for different temperature settings."""
        return [
            {
                "name": "Creative Writing",
                "task": "Write a creative story opening",
                "recommended_temperature": 0.8,
                "rationale": "Higher temperature for creativity and variety"
            },
            {
                "name": "Classification",
                "task": "Classify customer sentiment",
                "recommended_temperature": 0.0,
                "rationale": "Zero temperature for deterministic, consistent results"
            },
            {
                "name": "Translation",
                "task": "Translate technical documentation",
                "recommended_temperature": 0.3,
                "rationale": "Low temperature for accuracy with slight flexibility"
            },
            {
                "name": "Brainstorming",
                "task": "Generate product name ideas",
                "recommended_temperature": 0.9,
                "rationale": "High temperature for diverse, creative options"
            },
            {
                "name": "Code Generation",
                "task": "Write a sorting algorithm",
                "recommended_temperature": 0.2,
                "rationale": "Low temperature for correct, standard implementations"
            }
        ]
    
    @staticmethod
    def system_message_examples() -> List[Dict]:
        """System message examples for Azure OpenAI."""
        return [
            {
                "name": "Azure Expert Assistant",
                "system_message": """You are an expert Azure Solutions Architect assistant. 
You provide accurate, up-to-date information about Azure services.
Always include code examples using Azure SDKs when relevant.
Format responses with clear sections and bullet points.
Mention pricing considerations when discussing services.""",
                "use_case": "Technical Azure consultations"
            },
            {
                "name": "Code Review Bot",
                "system_message": """You are a code review assistant focused on Python best practices.
You provide constructive feedback on:
- Code quality and readability
- Potential bugs and edge cases  
- Performance optimizations
- Security vulnerabilities

Always explain WHY something is an issue and HOW to fix it.
Be encouraging and educational.""",
                "use_case": "Automated code reviews"
            },
            {
                "name": "Data Extraction Bot",
                "system_message": """You are a data extraction specialist.
You extract structured information from unstructured text.
Always respond in valid JSON format.
If information is not found, use null values.
Never make up or infer data that isn't explicitly stated.""",
                "use_case": "Parsing documents and extracting data"
            }
        ]


# Best practices guide
BEST_PRACTICES = """
╔══════════════════════════════════════════════════════════════╗
║           PROMPT ENGINEERING BEST PRACTICES                   ║
╚══════════════════════════════════════════════════════════════╝

1. BE SPECIFIC
   ❌ "Summarize this"
   ✅ "Summarize this article in 3 bullet points, each under 20 words"

2. PROVIDE CONTEXT
   ❌ "Is this good?"
   ✅ "Is this Python code following PEP 8 style guidelines?"

3. USE EXAMPLES (Few-Shot)
   - Show 3-5 examples of desired input/output
   - Include edge cases
   - Keep examples consistent

4. REQUEST REASONING (Chain-of-Thought)
   - Add "Let's think step by step"
   - Ask for explanations
   - Request intermediate steps

5. SET THE ROLE
   - "You are a [expert type]"
   - Specify experience level
   - Define the perspective

6. CONSTRAIN OUTPUT FORMAT
   - Specify JSON, CSV, or structured format
   - Provide templates
   - Define field names

7. CONTROL TEMPERATURE
   - 0.0-0.3: Factual, deterministic (classification, extraction)
   - 0.4-0.7: Balanced (general Q&A, summaries)
   - 0.8-1.0: Creative (writing, brainstorming)

8. ITERATE AND TEST
   - Test prompts with multiple inputs
   - Measure consistency
   - Refine based on results

9. USE DELIMITERS
   - Triple quotes \"\"\" for long text
   - <tags> for sections
   - --- for separators

10. ERROR HANDLING
    - Specify behavior for edge cases
    - Request fallback responses
    - Define acceptable outputs
"""


def print_best_practices():
    """Print best practices guide."""
    print(BEST_PRACTICES)


def demonstrate_examples():
    """Demonstrate all example categories."""
    examples = PromptExamples()
    
    print("\n" + "="*70)
    print("PROMPT ENGINEERING EXAMPLES")
    print("="*70)
    
    categories = [
        ("Zero-Shot", examples.zero_shot_examples()),
        ("Few-Shot", examples.few_shot_examples()),
        ("Chain-of-Thought", examples.chain_of_thought_examples()),
        ("Role Prompting", examples.role_prompting_examples()),
        ("Constrained Output", examples.constrained_output_examples())
    ]
    
    for category_name, category_examples in categories:
        print(f"\n{'─'*70}")
        print(f"📚 {category_name.upper()}")
        print('─'*70)
        
        for ex in category_examples:
            print(f"\n🔸 {ex['name']}")
            print(f"\n❌ BAD PROMPT:")
            print(f"{ex['bad']['prompt']}")
            print(f"\n   Problems:")
            for problem in ex['bad']['problems']:
                print(f"   • {problem}")
            
            print(f"\n✅ GOOD PROMPT:")
            print(f"{ex['good']['prompt']}")
            print(f"\n   Why Better:")
            for reason in ex['good']['why_better']:
                print(f"   • {reason}")
            print()


if __name__ == "__main__":
    print_best_practices()
    demonstrate_examples()
