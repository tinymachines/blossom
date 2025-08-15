"""
Prompt optimization for small LLMs
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class PromptStrategy:
    """Strategy for prompting different model types"""
    model_name: str
    model_type: str  # 'code', 'reasoning', 'general'
    max_tokens: int
    temperature: float
    system_prompt: str
    
    
class PromptOptimizer:
    """Optimize prompts for small language models"""
    
    # Model-specific strategies
    STRATEGIES = {
        'qwen2.5-coder:1.5b': PromptStrategy(
            model_name='qwen2.5-coder:1.5b',
            model_type='code',
            max_tokens=2048,
            temperature=0.3,
            system_prompt="You are an expert Python programmer. Write clean, working code."
        ),
        'deepcoder:1.5b': PromptStrategy(
            model_name='deepcoder:1.5b',
            model_type='code',
            max_tokens=2048,
            temperature=0.3,
            system_prompt="You write production-ready Python code. Follow best practices."
        ),
        'qwen3:0.6b': PromptStrategy(
            model_name='qwen3:0.6b',
            model_type='general',
            max_tokens=1024,
            temperature=0.5,
            system_prompt="You help create simple Python handlers. Be concise."
        ),
        'qwen3:1.7b': PromptStrategy(
            model_name='qwen3:1.7b',
            model_type='general',
            max_tokens=1024,
            temperature=0.5,
            system_prompt="You help create simple Python handlers. Be concise."
        ),
        'gemma3:1b': PromptStrategy(
            model_name='gemma3:1b',
            model_type='general',
            max_tokens=1536,
            temperature=0.4,
            system_prompt="You are a helpful coding assistant. Create working handlers."
        ),
        'deepseek-r1:1.5b': PromptStrategy(
            model_name='deepseek-r1:1.5b',
            model_type='reasoning',
            max_tokens=2048,
            temperature=0.2,
            system_prompt="Think step by step to create a working Zephyr handler."
        )
    }
    
    def __init__(self):
        self.template_dir = Path(__file__).parent.parent / 'templates'
        
    def create_prompt(self, model: str, challenge: str, level: int) -> str:
        """Create optimized prompt for model and challenge"""
        
        strategy = self.STRATEGIES.get(model)
        if not strategy:
            # Fallback strategy for unsupported models
            strategy = self._get_fallback_strategy(model)
            
        # Load challenge description
        challenge_path = Path(__file__).parent.parent / 'challenges' / f'{challenge}.md'
        with open(challenge_path) as f:
            challenge_desc = f.read()
            
        # Load appropriate template
        template = self._get_template(level, strategy.model_type)
        
        # Build prompt based on model type
        if strategy.model_type == 'code':
            return self._build_code_prompt(challenge_desc, template, level)
        elif strategy.model_type == 'reasoning':
            return self._build_reasoning_prompt(challenge_desc, template, level)
        else:
            return self._build_simple_prompt(challenge_desc, template, level)
            
    def _get_template(self, level: int, model_type: str) -> str:
        """Get appropriate template for level and model type"""
        
        if level == 1:
            template_file = 'minimal_handler.py'
        elif level <= 3:
            template_file = 'stateful_handler.py'
        else:
            template_file = 'broadcast_handler.py'
            
        template_path = self.template_dir / template_file
        if template_path.exists():
            with open(template_path) as f:
                return f.read()
        return ""
        
    def _build_code_prompt(self, challenge: str, template: str, level: int) -> str:
        """Build prompt for code-specialized models"""
        
        # Extract key information from challenge
        requirements = self._extract_requirements(challenge)
        test_cases = self._extract_test_cases(challenge)
        
        prompt = f"""Create a Python handler for the Zephyr network.

TEMPLATE TO MODIFY:
```python
{template}
```

REQUIREMENTS:
{requirements}

TEST CASES:
{test_cases}

IMPORTANT:
- Modify the template above to meet the requirements
- Keep all imports and base class inheritance
- Return complete, working Python code
- Include proper error handling

OUTPUT (complete handler code):
```python"""
        
        return prompt
        
    def _build_reasoning_prompt(self, challenge: str, template: str, level: int) -> str:
        """Build prompt for reasoning models"""
        
        requirements = self._extract_requirements(challenge)
        
        prompt = f"""Let's think step by step to create a Zephyr handler.

STEP 1: Understand the requirements
{requirements}

STEP 2: Identify what needs to be modified in this template:
```python
{template}
```

STEP 3: Plan the implementation
- What state variables do we need?
- What message types to handle?
- What responses to return?

STEP 4: Implement the solution

Now, implement the complete handler:
```python"""
        
        return prompt
        
    def _build_simple_prompt(self, challenge: str, template: str, level: int) -> str:
        """Build prompt for small general models"""
        
        # Simplify requirements
        simple_reqs = self._simplify_requirements(challenge)
        
        prompt = f"""Fill in the template to create a handler.

WHAT TO DO:
{simple_reqs}

TEMPLATE (fill in the marked sections):
```python
{self._add_placeholders(template)}
```

Complete handler:
```python"""
        
        return prompt
        
    def _extract_requirements(self, challenge: str) -> str:
        """Extract requirements section from challenge"""
        lines = challenge.split('\n')
        in_requirements = False
        requirements = []
        
        for line in lines:
            if '## Requirements' in line:
                in_requirements = True
                continue
            elif line.startswith('##') and in_requirements:
                break
            elif in_requirements and line.strip():
                requirements.append(line)
                
        return '\n'.join(requirements)
        
    def _extract_test_cases(self, challenge: str) -> str:
        """Extract test cases from challenge"""
        lines = challenge.split('\n')
        in_test = False
        test_cases = []
        
        for line in lines:
            if '## Test Cases' in line:
                in_test = True
                continue
            elif line.startswith('##') and in_test:
                break
            elif in_test:
                test_cases.append(line)
                
        return '\n'.join(test_cases)
        
    def _simplify_requirements(self, challenge: str) -> str:
        """Simplify requirements for small models"""
        requirements = self._extract_requirements(challenge)
        
        # Extract just the numbered items
        simple = []
        for line in requirements.split('\n'):
            if line.strip().startswith(('1.', '2.', '3.', '4.', '5.')):
                # Remove complex words
                simplified = line.replace('inherit from', 'use')
                simplified = simplified.replace('Must', '')
                simplified = simplified.replace('broadcast', 'send')
                simple.append(simplified)
                
        return '\n'.join(simple[:3])  # Limit to 3 main points
        
    def _add_placeholders(self, template: str) -> str:
        """Add clear placeholders for small models"""
        
        template = template.replace('YOUR_MESSAGE_TYPE', '### PUT MESSAGE TYPE HERE ###')
        template = template.replace('YOUR_RESPONSE_TYPE', '### PUT RESPONSE TYPE HERE ###')
        template = template.replace('# Your response data', '### ADD YOUR DATA HERE ###')
        template = template.replace('# Initialize any state here', '### ADD VARIABLES HERE (like: self.count = 0) ###')
        
        return template
    
    def _get_fallback_strategy(self, model: str) -> PromptStrategy:
        """Create a fallback strategy for unsupported models"""
        
        # Determine model type from name heuristics
        model_lower = model.lower()
        if 'code' in model_lower or 'coder' in model_lower or 'deepseek' in model_lower:
            model_type = 'code'
            system_prompt = "You are a Python programmer. Write clean, working code for the Zephyr network handler system."
            max_tokens = 2048
        elif 'reason' in model_lower or 'think' in model_lower:
            model_type = 'reasoning'
            system_prompt = "Think step by step to create a working Zephyr network handler in Python."
            max_tokens = 2048
        else:
            model_type = 'general'
            system_prompt = "You are a helpful assistant. Create a Python handler for the Zephyr network following the given template."
            max_tokens = 1536
        
        # Return fallback strategy
        return PromptStrategy(
            model_name=model,
            model_type=model_type,
            max_tokens=max_tokens,
            temperature=0.4,  # Conservative temperature for unknown models
            system_prompt=system_prompt
        )
    
    def _build_universal_prompt(self, challenge: str, template: str, level: int) -> str:
        """Build a universal prompt that works with any model"""
        
        requirements = self._extract_requirements(challenge)
        test_cases = self._extract_test_cases(challenge)
        
        prompt = f"""Task: Create a Python handler for the Zephyr network system.

Instructions:
1. Modify the provided template to meet the requirements
2. Keep all imports and class structure intact
3. Focus on implementing the handle() and can_handle() methods
4. Ensure the code is complete and working

Template to modify:
```python
{template}
```

Requirements to implement:
{requirements}

Expected behavior (test cases):
{test_cases}

Rules:
- Output must be valid Python code
- Must inherit from base handler class
- Must handle messages according to requirements
- Include error handling where appropriate

Generate the complete handler implementation:
```python"""
        
        return prompt
