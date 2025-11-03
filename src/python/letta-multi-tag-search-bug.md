# Bug Report: Multi-Tag Passage Search Returns No Results

## Summary
The `agents.passages.search()` API endpoint returns empty results when multiple tags are provided, regardless of the `tag_match_mode` setting. Single-tag searches work correctly.

## Expected Behavior
According to the [API documentation](https://docs.letta.com/api-reference/agents/passages/search), when searching with multiple tags:
- `tag_match_mode='any'` (default) should return passages that have ANY of the specified tags
- `tag_match_mode='all'` should return passages that have ALL of the specified tags

## Actual Behavior
When providing multiple tags in the search, the API returns zero results even when passages exist that match the tags.

## Reproduction Steps

```python
import os
from ai_memory_sdk import Memory

client = Memory(api_key=os.getenv("LETTA_API_KEY"))
user_id = "test_user_123"

# Initialize and create passages with tags
client.initialize_user_memory(user_id, reset=True)
messages = [
    {"role": "user", "content": "I love cats"}
]
run = client.add_messages(user_id, messages=messages, skip_vector_storage=False)
client.wait_for_run(run)

agent = client._get_matching_agent(tags=[user_id])

# Verify passages exist with correct tags
passages = client.letta_client.agents.passages.list(agent_id=agent.id)
for p in passages:
    print(f"Text: {p.text}, Tags: {p.tags}")
# Output shows: Text: I love cats, Tags: ['ai-memory-sdk', 'user']

# Search with single tag - WORKS
response = client.letta_client.agents.passages.search(
    agent_id=agent.id,
    query="animals",
    tags=["user"]
)
print(f"Single tag results: {len(response.results)}")  # Returns 1 result ✓

# Search with multiple tags - FAILS
response = client.letta_client.agents.passages.search(
    agent_id=agent.id,
    query="animals",
    tags=["ai-memory-sdk", "user"],
    tag_match_mode="any"
)
print(f"Multi-tag results: {len(response.results)}")  # Returns 0 results ✗

# Even with 'all' mode - FAILS
response = client.letta_client.agents.passages.search(
    agent_id=agent.id,
    query="animals",
    tags=["ai-memory-sdk", "user"],
    tag_match_mode="all"
)
print(f"Multi-tag 'all' results: {len(response.results)}")  # Returns 0 results ✗
```

## Test Results

| Search Configuration | Expected | Actual |
|---------------------|----------|---------|
| `tags=["user"]` | 2 results | 2 results ✓ |
| `tags=["ai-memory-sdk"]` | 4 results | 4 results ✓ |
| `tags=[]` | 4 results | 4 results ✓ |
| `tags=["ai-memory-sdk", "user"]` (default mode) | 2 results | 0 results ✗ |
| `tags=["ai-memory-sdk", "user"], tag_match_mode="any"` | 2 results | 0 results ✗ |
| `tags=["ai-memory-sdk", "user"], tag_match_mode="all"` | 2 results | 0 results ✗ |

## Impact
This bug causes the test `tests/test_messages.py::test_conversational_memory` to fail in the ai-memory-sdk, as it relies on multi-tag search functionality to filter user messages.

## Environment
- Letta API: Production endpoint (api.letta.com)
- Client: letta-client Python SDK
- Test date: 2025-10-02

## Workaround
Use single-tag searches instead of multi-tag searches. For example, change:
```python
tags=["ai-memory-sdk", "user"]
```
to:
```python
tags=["user"]
```

## Additional Notes
- The passages are correctly created with multiple tags (verified via `passages.list()`)
- The issue appears to be in the search filtering logic, not in passage storage
- Tag order in passages may vary (e.g., `['user', 'ai-memory-sdk']` vs `['ai-memory-sdk', 'user']`), which might be related to the issue
