import sys
import types
import pytest


# Reuse the mock setup from test_subject.py
letta_client = types.ModuleType("letta_client")


def _id(prefix=["agent", 0]):
    if prefix[0] == "agent":
        prefix[1] += 1
        return f"agent-{prefix[1]}"


class _Storage:
    def __init__(self):
        self.agents = {}
        self.agent_blocks = {}
        self.blocks = {}
        self.run_counter = 0


_store = _Storage()


class _AgentsBlocks:
    def attach(self, agent_id: str, block_id: str):
        _store.agent_blocks.setdefault(agent_id, [])
        if block_id not in _store.agent_blocks[agent_id]:
            _store.agent_blocks[agent_id].append(block_id)

    def list(self, agent_id: str):
        ids = _store.agent_blocks.get(agent_id, [])
        return [types.SimpleNamespace(**_store.blocks[i]) for i in ids if i in _store.blocks]

    def detach(self, agent_id: str, block_id: str):
        ids = _store.agent_blocks.get(agent_id, [])
        _store.agent_blocks[agent_id] = [i for i in ids if i != block_id]

    def retrieve(self, agent_id: str, label: str):
        ids = _store.agent_blocks.get(agent_id, [])
        for i in ids:
            if i in _store.blocks:
                b = _store.blocks[i]
                if b["label"] == label:
                    return types.SimpleNamespace(**b)
        raise KeyError("Block not found")


class _AgentsMessages:
    def create_async(self, agent_id: str, messages):
        _store.run_counter += 1
        return types.SimpleNamespace(id=f"run-{_store.run_counter}")


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

    def delete(self, agent_id: str):
        _store.agents.pop(agent_id, None)
        _store.agent_blocks.pop(agent_id, None)


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

    def delete(self, block_id: str):
        _store.blocks.pop(block_id, None)


class _Runs:
    def retrieve(self, run_id: str):
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


def test_no_subject_id_raises_error():
    """Test that methods raise error when no subject_id is provided"""
    memory = Memory()  # No subject_id

    with pytest.raises(ValueError, match="No subject_id provided"):
        memory.initialize_memory("test", "Test block")

    with pytest.raises(ValueError, match="No subject_id provided"):
        memory.get_memory("test")

    with pytest.raises(ValueError, match="No subject_id provided"):
        memory.list_blocks()


def test_block_reset_functionality():
    """Test that reset=True properly recreates blocks"""
    memory = Memory(subject_id="user_reset_test")

    # Create initial block
    memory.initialize_memory("config", "Configuration", value="v1", reset=True)
    assert memory.get_memory("config") == "v1"

    # Reset block with new value
    memory.initialize_memory("config", "Configuration", value="v2", reset=True)
    assert memory.get_memory("config") == "v2"

    # Without reset, should keep existing value
    memory.initialize_memory("config", "Configuration", value="v3", reset=False)
    assert memory.get_memory("config") == "v2"  # unchanged


def test_multiple_blocks_per_subject():
    """Test that multiple blocks can be attached to one subject"""
    memory = Memory(subject_id="user_multi")

    memory.initialize_memory("human", "Human info", value="Alice", reset=True)
    memory.initialize_memory("summary", "Summary", value="First conversation", reset=True)
    memory.initialize_memory("preferences", "User preferences", value="Likes Python", reset=True)

    blocks = memory.list_blocks()
    labels = sorted([getattr(b, 'label', None) or b.get('label') for b in blocks])

    assert labels == ["human", "preferences", "summary"]
    assert memory.get_memory("human") == "Alice"
    assert memory.get_memory("summary") == "First conversation"
    assert memory.get_memory("preferences") == "Likes Python"


def test_empty_block_value():
    """Test that blocks can be created with empty values"""
    memory = Memory(subject_id="user_empty")

    memory.initialize_memory("notes", "User notes", value="", reset=True)
    result = memory.get_memory("notes")

    assert result == ""


def test_nonexistent_block_returns_none():
    """Test that getting a nonexistent block returns None"""
    memory = Memory(subject_id="user_none")

    result = memory.get_memory("nonexistent")
    assert result is None


def test_subject_initialization_reset():
    """Test that initialize_subject with reset=True recreates the agent"""
    memory = Memory()

    # Create subject with a block
    memory.initialize_subject("project_x", reset=True)
    memory.initialize_memory("status", "Status", value="active", subject_id="project_x")
    assert memory.get_memory("status", subject_id="project_x") == "active"

    # Reset subject (deletes agent and recreates)
    memory.initialize_subject("project_x", reset=True)

    # Block should be gone
    assert memory.get_memory("status", subject_id="project_x") is None


def test_subject_initialization_without_reset_raises():
    """Test that initializing existing subject without reset raises error"""
    memory = Memory()

    memory.initialize_subject("project_y", reset=True)

    with pytest.raises(ValueError, match="already exists"):
        memory.initialize_subject("project_y", reset=False)


def test_special_characters_in_block_labels():
    """Test blocks with underscores and dashes in labels"""
    memory = Memory(subject_id="user_special")

    memory.initialize_memory("user_name", "User name", value="Bob", reset=True)
    memory.initialize_memory("api-key", "API key", value="secret", reset=True)

    assert memory.get_memory("user_name") == "Bob"
    assert memory.get_memory("api-key") == "secret"


def test_long_block_value():
    """Test that long values near char_limit work correctly"""
    memory = Memory(subject_id="user_long")

    long_value = "x" * 5000
    memory.initialize_memory("data", "Large data", value=long_value, char_limit=10000, reset=True)

    result = memory.get_memory("data")
    assert result == long_value
    assert len(result) == 5000
