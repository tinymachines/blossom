# Level 5: Sync Pair Handlers

## Objective
Create TWO handlers that work together: a SourceHandler that collects data and a SyncHandler that aggregates it from multiple sources.

## SourceHandler Requirements
1. Collect local system metrics every 10 seconds
2. Store last 10 readings
3. Respond to "sync_request" with stored data
4. Include node identification
5. Implement data versioning

## SyncHandler Requirements
1. Broadcast "sync_request" every 30 seconds
2. Collect responses from all SourceHandlers
3. Aggregate data (calculate averages)
4. Store aggregated results
5. Respond to "sync_status" with summary

## Protocol Flow
```
SyncHandler                    SourceHandler(s)
    |                               |
    |-------- sync_request -------->|
    |                               |
    |<------ sync_response ---------|
    |         (with data)           |
    |                               |
    | (aggregate)                   |
    |                               |
    |-------- sync_complete ------->|
    |         (broadcast)           |
```

## Test Cases
```python
# Sync request from SyncHandler
{
    "type": "sync_request",
    "payload": {
        "request_id": "sync_001",
        "timestamp": "2024-01-13T12:00:00Z"
    }
}

# Response from SourceHandler
{
    "type": "sync_response",
    "payload": {
        "request_id": "sync_001",
        "node_id": "source_node_1",
        "data": [
            {"timestamp": "2024-01-13T11:59:50Z", "cpu": 45.2, "memory": 62.1},
            {"timestamp": "2024-01-13T12:00:00Z", "cpu": 48.7, "memory": 61.8}
        ],
        "version": 1
    }
}

# Aggregated broadcast from SyncHandler
{
    "type": "sync_complete",
    "payload": {
        "request_id": "sync_001",
        "nodes_reporting": 3,
        "aggregated": {
            "avg_cpu": 46.8,
            "avg_memory": 59.4,
            "min_cpu": 41.2,
            "max_cpu": 52.3
        }
    }
}

# Status query
{
    "type": "sync_status",
    "payload": {}
}

# Status response from SyncHandler
{
    "type": "sync_status_response",
    "payload": {
        "last_sync": "2024-01-13T12:00:00Z",
        "nodes_tracked": 3,
        "sync_count": 15,
        "next_sync_in": 18
    }
}
```

## Evaluation Criteria

### SourceHandler (50 points)
- Collects metrics: 10 points
- Stores history: 10 points
- Responds to sync: 15 points
- Includes identification: 10 points
- Implements versioning: 5 points

### SyncHandler (50 points)
- Broadcasts requests: 10 points
- Collects responses: 10 points
- Aggregates correctly: 15 points
- Stores results: 10 points
- Status reporting: 5 points

## Bonus Challenge
Implement conflict resolution when multiple SyncHandlers are present (prevent sync storms).