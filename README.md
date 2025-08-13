# Blossom: LLM Handler Generation Test Harness

## Overview

Blossom is a test harness designed to evaluate the capability of small language models (1.5B-3B parameters) to generate working Zephyr handlers. It progressively challenges models with increasingly complex handler requirements, testing their ability to understand APIs, implement logic, and create functional distributed system components.

## Models Under Test

| Model | Size | Type | Expected Strengths |
|-------|------|------|-------------------|
| qwen2.5-coder:1.5b | 1.5B | Code-specialized | Python syntax, API usage |
| deepcoder:1.5b | 1.5B | Code-specialized | Code generation, debugging |
| qwen3:0.6b | 0.6B | General | Basic logic, simple handlers |
| gemma3:1b | 1B | General | Instruction following |
| deepseek-r1:1.5b | 1.5B | Reasoning | Logic, multi-step tasks |

## Challenge Levels

### Level 1: Echo Handler (Basic)
- **Objective**: Create a handler that echoes received messages
- **Skills Tested**: Basic handler structure, message processing
- **Success Criteria**: Handler loads, processes messages, returns responses

### Level 2: Counter Handler (State Management)
- **Objective**: Create a handler that counts messages and broadcasts totals
- **Skills Tested**: State management, periodic tasks, broadcasting
- **Success Criteria**: Maintains count, broadcasts every 30 seconds

### Level 3: Data Collector (File I/O)
- **Objective**: Create a handler that collects network data and saves to CSV
- **Skills Tested**: File operations, data formatting, error handling
- **Success Criteria**: Creates valid CSV, handles errors gracefully

### Level 4: Command Executor (System Integration)
- **Objective**: Create a handler that safely executes system commands
- **Skills Tested**: Subprocess management, security awareness, async operations
- **Success Criteria**: Executes commands, returns output, validates input

### Level 5: Sync Pair (Distributed Coordination)
- **Objective**: Create source and sync handlers that coordinate data collection
- **Skills Tested**: Multi-handler coordination, protocol design, state synchronization
- **Success Criteria**: Handlers communicate, data syncs correctly

## Prompt Engineering Strategy

### Core Principles for Small Models

1. **Explicit Structure**: Provide clear templates and examples
2. **Chunked Instructions**: Break complex tasks into steps
3. **Concrete Examples**: Show working code snippets
4. **Focused Context**: Include only relevant API information
5. **Validation Hints**: Specify expected outputs and formats

### Prompt Template Structure

```
ROLE: You are creating a Zephyr network handler.

HANDLER TEMPLATE:
[Minimal working example]

YOUR TASK:
[Specific, clear objective]

REQUIREMENTS:
1. [Concrete requirement]
2. [Concrete requirement]

API REFERENCE:
[Only relevant methods]

OUTPUT FORMAT:
```python
# Complete handler code here
```
```

## Evaluation Metrics

### Functionality Scores
- **Loads** (10 pts): Handler imports and initializes without errors
- **Activates** (10 pts): Handler activates successfully
- **Processes** (20 pts): Handler processes test messages correctly
- **Broadcasts** (20 pts): Handler sends messages as expected
- **State** (20 pts): Handler maintains state correctly
- **Resilience** (20 pts): Handler handles errors gracefully

### Code Quality Scores
- **Structure** (25 pts): Follows handler patterns
- **Async** (25 pts): Proper async/await usage
- **Safety** (25 pts): No dangerous operations
- **Efficiency** (25 pts): Reasonable resource usage

## Directory Structure

```
blossom/
├── README.md                 # This file
├── .env                     # API keys and configuration
├── requirements.txt         # Python dependencies
├── challenges/              # Challenge descriptions
│   ├── level1_echo.md
│   ├── level2_counter.md
│   ├── level3_collector.md
│   ├── level4_executor.md
│   └── level5_sync.md
├── templates/               # Handler templates for models
│   ├── minimal_handler.py
│   ├── stateful_handler.py
│   └── broadcast_handler.py
├── generated/               # Model-generated handlers
│   ├── {model_name}/
│   │   └── {challenge}/
│   │       └── handler.py
├── evaluation/              # Test results and reports
│   ├── results.json
│   └── report.html
└── scripts/                 # Test automation
    ├── run_challenge.py     # Main test runner
    ├── evaluate_handler.py  # Handler evaluation
    ├── prompt_optimizer.py  # Prompt generation
    └── model_client.py      # LLM API wrapper
```

## Usage

### Quick Start

```bash
# Install dependencies
cd blossom
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your API keys

# Run a single challenge
python scripts/run_challenge.py --model qwen2.5-coder:1.5b --level 1

# Run full evaluation suite
python scripts/run_challenge.py --all-models --all-levels

# Generate report
python scripts/generate_report.py
```

### Running Individual Tests

```python
# Test a specific handler
from scripts.evaluate_handler import evaluate_handler

score = evaluate_handler(
    handler_path="generated/qwen2.5-coder/level1/handler.py",
    test_messages=[
        {"type": "echo", "payload": "Hello"}
    ]
)
print(f"Score: {score}/100")
```

## Optimization Techniques

### For Code Models (qwen2.5-coder, deepcoder)
- Emphasize syntax and API usage
- Provide import statements
- Show type hints
- Include docstring examples

### For Reasoning Models (deepseek-r1)
- Break down logic step-by-step
- Explain the "why" behind requirements
- Provide decision trees
- Include edge cases

### For Small General Models (qwen3:0.6b, gemma3:1b)
- Keep prompts very simple
- Provide complete templates with placeholders
- Focus on single responsibilities
- Use repetition for important points

## Success Criteria

A model is considered successful at a level if:
- Handler loads without errors
- Handler processes test messages correctly
- Handler meets level-specific requirements
- Score >= 70/100

## Safety Considerations

All generated handlers are:
1. Sandboxed during testing
2. Reviewed for dangerous operations
3. Limited to specific API calls
4. Tested with timeout limits
5. Validated against security patterns

## Results Tracking

Results are stored in `evaluation/results.json`:

```json
{
  "model": "qwen2.5-coder:1.5b",
  "challenge": "level1_echo",
  "timestamp": "2024-01-13T12:00:00Z",
  "scores": {
    "functionality": 80,
    "quality": 75,
    "total": 77.5
  },
  "handler_path": "generated/qwen2.5-coder/level1/handler.py",
  "test_output": "...",
  "errors": []
}
```

## Contributing

To add new challenges:
1. Create challenge description in `challenges/`
2. Add test cases to `scripts/test_cases.py`
3. Update evaluation metrics if needed
4. Document expected outcomes

## Next Steps

1. Implement prompt caching for efficiency
2. Add multi-turn refinement for failed attempts
3. Create handler complexity analyzer
4. Build visualization dashboard
5. Implement A/B testing for prompt variations