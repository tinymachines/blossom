# Level 2: Counter Handler

## Objective
Create a handler that counts messages and periodically broadcasts statistics.

## Requirements
1. Count all messages received (any type)
2. Track messages by type
3. Broadcast statistics every 30 seconds
4. Respond to "stats" messages with current counts
5. Maintain state between messages

## Test Cases
```python
# Inputs (sequence)
{"type": "chat", "payload": "Hello"}
{"type": "chat", "payload": "World"}
{"type": "data", "payload": {"value": 42}}
{"type": "stats", "payload": "request"}

# Expected response to stats request
{
    "type": "stats_response",
    "payload": {
        "total_messages": 4,
        "by_type": {
            "chat": 2,
            "data": 1,
            "stats": 1
        },
        "uptime_seconds": 45
    }
}

# Expected broadcast (every 30s)
{
    "type": "counter_broadcast",
    "payload": {
        "total_messages": 4,
        "messages_per_second": 0.089
    }
}
```

## Evaluation Criteria
- Maintains count state: 25 points
- Tracks by type: 25 points
- Broadcasts periodically: 25 points
- Responds to stats: 25 points