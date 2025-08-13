# Level 3: Data Collector Handler

## Objective
Create a handler that collects network metrics and saves them to a CSV file.

## Requirements
1. Collect data from "metric" type messages
2. Store timestamp, sender, metric_name, and value
3. Save to CSV file every 10 messages or 60 seconds
4. Handle file I/O errors gracefully
5. Rotate files when they exceed 1000 rows

## Test Cases
```python
# Input messages
{"type": "metric", "payload": {"name": "cpu_usage", "value": 45.2}, "from": "node1"}
{"type": "metric", "payload": {"name": "memory_free", "value": 1024}, "from": "node2"}
{"type": "metric", "payload": {"name": "network_latency", "value": 12.5}, "from": "node1"}

# Expected CSV format (metrics_20240113_120000.csv)
timestamp,sender,metric_name,value
2024-01-13T12:00:00,node1,cpu_usage,45.2
2024-01-13T12:00:01,node2,memory_free,1024.0
2024-01-13T12:00:02,node1,network_latency,12.5

# Response to metric message
{
    "type": "metric_ack",
    "payload": {
        "received": true,
        "total_collected": 3
    }
}
```

## Evaluation Criteria
- Collects metrics correctly: 20 points
- Creates valid CSV: 20 points
- Implements file rotation: 20 points
- Handles I/O errors: 20 points
- Proper timestamp format: 20 points