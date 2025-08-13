# Level 1: Echo Handler

## Objective
Create a simple handler that echoes back any message it receives with a prefix.

## Requirements
1. Handler must inherit from `HotHandler`
2. Must respond to messages of type "echo"
3. Must prefix the response with "ECHO: "
4. Must include the sender's ID in the response

## Test Cases
```python
# Input
{
    "type": "echo",
    "payload": "Hello World",
    "from": "node123"
}

# Expected Output
{
    "type": "echo_response", 
    "payload": "ECHO: Hello World",
    "original_sender": "node123"
}
```

## Evaluation Criteria
- Loads without errors: 20 points
- Processes echo messages: 40 points
- Returns correct format: 20 points
- Includes sender ID: 20 points