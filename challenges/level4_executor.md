# Level 4: Command Executor Handler

## Objective
Create a handler that safely executes system commands and returns output.

## Requirements
1. Accept "command" type messages
2. Validate commands against a whitelist
3. Execute using asyncio subprocess
4. Capture stdout and stderr
5. Implement timeout (max 10 seconds)
6. Return execution results

## Allowed Commands (Whitelist)
- `ls` (with safe paths only)
- `date`
- `uptime`
- `df -h`
- `free -m`
- `hostname`
- `pwd`
- `echo` (with sanitized input)

## Test Cases
```python
# Valid command
{
    "type": "command",
    "payload": {
        "cmd": "date",
        "args": []
    }
}

# Expected response
{
    "type": "command_result",
    "payload": {
        "success": true,
        "stdout": "Sat Jan 13 12:00:00 UTC 2024\n",
        "stderr": "",
        "return_code": 0,
        "execution_time": 0.042
    }
}

# Invalid command (not in whitelist)
{
    "type": "command",
    "payload": {
        "cmd": "rm",
        "args": ["-rf", "/"]
    }
}

# Expected response
{
    "type": "command_result",
    "payload": {
        "success": false,
        "error": "Command 'rm' not in whitelist",
        "return_code": -1
    }
}
```

## Security Requirements
- NO shell=True in subprocess
- NO user input in command strings
- Must validate all paths
- Must sanitize echo arguments
- Must enforce timeout

## Evaluation Criteria
- Executes valid commands: 20 points
- Blocks invalid commands: 20 points
- Proper async implementation: 20 points
- Timeout enforcement: 20 points
- Security validation: 20 points