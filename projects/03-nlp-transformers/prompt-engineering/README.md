# Prompt Engineering Lab - Days 3-4

## 🎯 Overview

This lab teaches you **Prompt Engineering** - the critical skill of designing effective inputs to get the best outputs from Large Language Models (LLMs) like GPT-4, Claude, and Azure OpenAI.

## 📚 What You'll Learn

### Core Techniques
1. **Zero-Shot Prompting** - Getting results without examples
2. **Few-Shot Prompting** - Using examples to guide the model
3. **Chain-of-Thought** - Encouraging step-by-step reasoning
4. **Role-Based Prompting** - Setting expert personas
5. **Constrained Output** - Forcing specific formats
6. **Temperature Control** - Balancing creativity vs consistency

### Practical Skills
- Writing clear, effective prompts
- Evaluating prompt quality
- Optimizing for Azure OpenAI
- Handling different use cases
- Debugging poor outputs

## 📁 Files in This Lab

```
prompt-engineering/
├── README.md                    ← You are here
├── azure_openai_config.py      ← Azure OpenAI setup & connection
├── prompt_examples.py          ← Example library (good vs bad)
├── prompt_engineering_lab.py   ← Interactive exercises
└── outputs/                    ← Generated results
```

## 🚀 Getting Started

### Option 1: Mock Mode (No API Key Required)
```bash
# Just run it! Uses mock responses for learning
python prompt_engineering_lab.py
```

### Option 2: With Real Azure OpenAI

**Step 1: Set Environment Variables**

Windows PowerShell:
```powershell
$env:AZURE_OPENAI_API_KEY="your-key-here"
$env:AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
$env:AZURE_OPENAI_DEPLOYMENT="gpt-4"
```

Linux/Mac:
```bash
export AZURE_OPENAI_API_KEY="your-key-here"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="gpt-4"
```

**Step 2: Run the Lab**
```bash
python prompt_engineering_lab.py
```

## 🎓 Lab Exercises

### Exercise 1: Zero-Shot Prompting
Learn to write clear, specific prompts without examples.

**Bad Prompt:**
```
Classify this
```

**Good Prompt:**
```
Classify the sentiment of the following customer review as positive, negative, or neutral.

Review: "The product arrived late but works great."

Sentiment:
```

**Key Lessons:**
- Be specific about the task
- Provide context
- Specify output format

---

### Exercise 2: Few-Shot Prompting
Use examples to teach the model the desired pattern.

**Example:**
```
Extract product information in JSON format.

Examples:
Input: "iPhone 14 Pro, 256GB, Gold"
Output: {"model": "iPhone 14 Pro", "storage": "256GB", "color": "Gold"}

Input: "Samsung Galaxy S23, 128GB, Black"
Output: {"model": "Samsung Galaxy S23", "storage": "128GB", "color": "Black"}

Now extract from:
Input: "MacBook Pro 14-inch, M3, 16GB, 512GB, Space Gray"
Output:
```

**Key Lessons:**
- Show 3-5 examples
- Keep format consistent
- Include edge cases

---

### Exercise 3: Chain-of-Thought
Encourage step-by-step reasoning for complex tasks.

**Magic Phrase:** "Let's think step by step"

**Example:**
```
A company has 50 employees. They hire 20% more, then 10% quit. How many remain?

Let's solve this step by step:
1. First, calculate how many are hired
2. Then, calculate the new total
3. Next, calculate how many quit
4. Finally, calculate how many remain

Solution:
```

**Key Lessons:**
- Use for math, logic, and multi-step problems
- Breaks down complex reasoning
- Improves accuracy significantly

---

### Exercise 4: Role-Based Prompting
Set a specific expert persona for better domain knowledge.

**Example:**
```
You are a Senior Azure Solutions Architect with 15 years of experience.

A client asks: "Should we use Event Hubs or Service Bus for 1M events/sec?"

Consider:
- Performance and throughput
- Cost implications  
- Operational complexity
- Use case fit

Recommendation:
```

**Key Lessons:**
- Specify expertise level
- Provide context
- List decision factors

---

### Exercise 5: Temperature Comparison
Control creativity vs consistency.

**Temperature Guide:**
- **0.0-0.3**: Deterministic, factual (classification, extraction)
- **0.4-0.7**: Balanced (Q&A, summaries)
- **0.8-1.0**: Creative (writing, brainstorming)

**Example:**
```python
# For classification (want same answer every time)
temperature = 0.0

# For creative naming (want variety)
temperature = 0.9
```

---

### Exercise 6: Constrained Output
Force specific output formats for automation.

**Example:**
```
Review this code and respond ONLY with valid JSON:

{
  "has_issues": true/false,
  "issues": [
    {"type": "bug", "description": "string", "line": number}
  ]
}

Code:
def divide(a, b):
    return a / b

JSON Response:
```

**Key Lessons:**
- Specify exact format
- Include all required fields
- Makes responses parseable

---

## 📊 Prompt Quality Evaluation

The lab automatically evaluates prompts on 5 criteria:

| Criterion | Points | What It Checks |
|-----------|--------|----------------|
| **Clarity** | 20 | Clear task verb, sufficient detail |
| **Context** | 20 | Role, background, or context provided |
| **Examples** | 20 | Few-shot examples included |
| **Format** | 20 | Output structure specified |
| **Reasoning** | 20 | Step-by-step thinking encouraged |

**Grading Scale:**
- A (90-100): Excellent prompt
- B (80-89): Good prompt  
- C (70-79): Adequate prompt
- D (60-69): Needs improvement
- F (< 60): Poor prompt

## 🎯 Best Practices Checklist

### Before Writing a Prompt:
- [ ] What exactly do I want the model to do?
- [ ] What context does it need?
- [ ] Should I provide examples?
- [ ] What output format do I want?
- [ ] Is this a creative or factual task?

### The 5 C's:
- **Clear**: Unambiguous instructions
- **Concise**: Only necessary information
- **Contextual**: Relevant background
- **Constrained**: Specific output format
- **Complete**: All needed information

### Common Mistakes to Avoid:
- ❌ Too vague: "Tell me about AI"
- ❌ No context: "Is this good?"
- ❌ Missing output format: "Extract data from this"
- ❌ No examples for complex tasks
- ❌ Wrong temperature for the task

## 💡 Real-World Use Cases

### 1. Customer Support Automation
```python
# System message
"You are a customer support assistant for Azure services. 
Always be helpful, provide exact documentation links, 
and suggest next steps."

# Temperature: 0.3 (consistent, accurate)
```

### 2. Code Review Bot
```python
# Few-shot with constrained output
"Review code for bugs. Respond in JSON format..."

# Temperature: 0.0 (deterministic)
```

### 3. Creative Content Generation
```python
# Role-based with high creativity
"You are a creative marketing copywriter..."

# Temperature: 0.8 (creative, varied)
```

### 4. Data Extraction Pipeline
```python
# Constrained output for parsing
"Extract fields in this exact format: {...}"

# Temperature: 0.0 (consistent structure)
```

## 🔧 Troubleshooting

### Problem: Inconsistent outputs
**Solution:** Lower temperature (0.0-0.3)

### Problem: Model doesn't follow format
**Solution:** 
- Be more explicit about format
- Use few-shot examples
- Add "Respond ONLY in this format"

### Problem: Poor reasoning
**Solution:** Add "Let's think step by step"

### Problem: Generic responses
**Solution:** 
- Add role and context
- Provide domain-specific examples
- Be more specific in instructions

## 📖 Running the Lab

### Interactive Mode
```bash
python prompt_engineering_lab.py

# Menu options:
# 1. Run all exercises (full workshop)
# 2. Run individual exercise
# 3. View best practices
# 4. View example prompts
# 5. Test your own prompt
```

### View Examples Only
```bash
python prompt_examples.py
```

### Test Configuration
```bash
python azure_openai_config.py
```

## 🎓 Learning Path

**After This Lab:**
1. ✅ You understand core prompting techniques
2. ✅ You can write effective prompts
3. ✅ You know when to use each technique
4. ✅ You can evaluate prompt quality

**Next Steps:**
- Week 2: RAG Systems (using prompts with retrieval)
- Week 3: Fine-tuning (when prompting isn't enough)
- Week 4: Production deployment

## 📚 Additional Resources

### Azure OpenAI Documentation
- [Prompt Engineering Guide](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/prompt-engineering)
- [System Messages](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/system-message)
- [Best Practices](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/advanced-prompt-engineering)

### Academic Papers
- "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models" (Wei et al., 2022)
- "Language Models are Few-Shot Learners" (Brown et al., 2020)

## ✅ Success Criteria

You've mastered prompt engineering when you can:
- [ ] Write prompts that consistently get desired outputs
- [ ] Choose appropriate temperature for each task
- [ ] Debug poor responses by improving prompts
- [ ] Evaluate and improve existing prompts
- [ ] Apply techniques to real-world problems

## 🎯 Interview Preparation

**Be ready to explain:**
1. What is prompt engineering and why it matters
2. Difference between zero-shot and few-shot
3. When to use chain-of-thought reasoning
4. How temperature affects outputs
5. Examples from your hands-on experience

**Practice explaining:**
- "I used few-shot prompting to improve classification accuracy from 70% to 95%"
- "By adding chain-of-thought, I reduced reasoning errors in complex calculations"
- "Setting temperature to 0.0 ensured consistent JSON output for our API"

---

**Date Completed:** December 6, 2024  
**Time Invested:** 3-4 hours  
**Status:** ✅ Complete
