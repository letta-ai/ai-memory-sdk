import sys
import types
import pytest
import time


# Create a fake letta_client module with a slow run
letta_client = types.ModuleType("letta_client")


class _Storage:
    def __init__(self):
        self.agents = {}
        self.agent_blocks = {}
        self.blocks = {}
        self.run_counter = 0
        self.slow_runs = set()  # runs that never complete


_store = _Storage()


def _id(prefix=["agent", 0]):
    if prefix[0] == "agent":
        prefix[1] += 1
        return f"agent-{prefix[1]}"


class _AgentsBlocks:
    def attach(self, agent_id: str, block_id: str):
        _store.agent_blocks.setdefault(agent_id, [])
        if block_id not in _store.agent_blocks[agent_id]:
            _store.agent_blocks[agent_id].append(block_id)

    def list(self, agent_id: str):
        ids = _store.agent_blocks.get(agent_id, [])
        return [types.SimpleNamespace(**_store.blocks[i]) for i in ids]


class _AgentsMessages:
    def create_async(self, agent_id: str, messages):
        _store.run_counter += 1
        run_id = f"run-{_store.run_counter}"
        # Mark some runs as slow
        if _store.run_counter % 2 == 0:
            _store.slow_runs.add(run_id)
        return types.SimpleNamespace(id=run_id)


class _AgentsPassages:
    def create(self, agent_id: str, text: str, tags=None):
        return types.SimpleNamespace(id=f"passage-{agent_id}")


class _Agents:
    def __init__(self):
        self.blocks = _AgentsBlocks()
        self.messages = _AgentsMessages()
        self.passages = _AgentsPassages()

    def create(self, name: str, model: str, agent_type: str, initial_message_sequence, tags):
        agent_id = _id()
        _store.agents[agent_id] = {"id": agent_id, "name": name, "tags": tags}
        _store.agent_blocks[agent_id] = []
        return types.SimpleNamespace(id=agent_id)

    def list(self, tags, match_all_tags=True):
        def has_all(t):
            return all(tag in t for tag in tags)
        results = [types.SimpleNamespace(**a) for a in _store.agents.values() if has_all(a["tags"])]
        return results


class _Blocks:
    def __init__(self):
        self._counter = 0

    def create(self, label: str, description: str, limit: int, value: str):
        self._counter += 1
        block_id = f"block-{self._counter}"
        _store.blocks[block_id] = {
            "id": block_id,
            "label": label,
            "description": description,
            "limit": limit,
            "value": value,
        }
        return types.SimpleNamespace(**_store.blocks[block_id])


class _Runs:
    def retrieve(self, run_id: str):
        # Slow runs never complete
        if run_id in _store.slow_runs:
            return types.SimpleNamespace(id=run_id, status="running")
        return types.SimpleNamespace(id=run_id, status="completed")


class Letta:
    def __init__(self, token=None):
        self.agents = _Agents()
        self.blocks = _Blocks()
        self.runs = _Runs()


class AsyncLetta:
    def __init__(self, token=None):
        self.agents = types.SimpleNamespace(passages=_AgentsPassages())


letta_client.Letta = Letta
letta_client.AsyncLetta = AsyncLetta
sys.modules['letta_client'] = letta_client


from ai_memory_sdk import Memory  # noqa: E402


def test_wait_for_run_timeout():
    """Test that wait_for_run raises TimeoutError when run doesn't complete"""
    # Reset run counter for test isolation
    _store.run_counter = 0
    _store.slow_runs.clear()

    memory = Memory(subject_id="user_test")

    memory.initialize_memory(
        label="test",
        description="Test block",
        value="initial",
        reset=True,
    )

    # Add messages to get run IDs
    # Run counter starts at 0, so first call is 1 (odd, fast)
    # Second call is 2 (even, slow)
    run1 = memory.add_messages([{"role": "user", "content": "first"}])
    run2 = memory.add_messages([{"role": "user", "content": "second"}])

    # First run should complete (odd numbered)
    memory.wait_for_run(run1, timeout=1)

    # Second run should timeout (even numbered, marked as slow)
    with pytest.raises(TimeoutError) as exc_info:
        memory.wait_for_run(run2, timeout=1)

    assert "did not complete within 1 seconds" in str(exc_info.value)


def test_wait_for_run_default_timeout():
    """Test that default timeout is reasonable (300s)"""
    memory = Memory(subject_id="user_test2")

    memory.initialize_memory(label="test", description="Test", value="v", reset=True)

    # Odd numbered run completes immediately
    run = memory.add_messages([{"role": "user", "content": "test"}])

    # Should complete well before default timeout
    start = time.time()
    memory.wait_for_run(run)  # uses default timeout of 300s
    elapsed = time.time() - start

    assert elapsed < 2, "Fast run should complete quickly"
