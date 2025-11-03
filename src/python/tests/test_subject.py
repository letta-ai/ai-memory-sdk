import sys
import types
import pytest


# Create a fake letta_client module so tests run offline
letta_client = types.ModuleType("letta_client")


def _id(prefix=["agent", 0]):
    # Simple counter-based id generator
    if prefix[0] == "agent":
        prefix[1] += 1
        return f"agent-{prefix[1]}"


class _Storage:
    def __init__(self):
        self.agents = {}  # id -> {id, name, tags}
        self.agent_blocks = {}  # agent_id -> [block_ids]
        self.blocks = {}  # id -> {id, label, description, limit, value}
        self.run_counter = 0


_store = _Storage()


class _AgentsBlocks:
    def attach(self, agent_id: str, block_id: str):
        _store.agent_blocks.setdefault(agent_id, [])
        if block_id not in _store.agent_blocks[agent_id]:
            _store.agent_blocks[agent_id].append(block_id)

    def list(self, agent_id: str):
        ids = _store.agent_blocks.get(agent_id, [])
        return [types.SimpleNamespace(**_store.blocks[i]) for i in ids]

    def detach(self, agent_id: str, block_id: str):
        ids = _store.agent_blocks.get(agent_id, [])
        _store.agent_blocks[agent_id] = [i for i in ids if i != block_id]

    def retrieve(self, agent_id: str, label: str):
        ids = _store.agent_blocks.get(agent_id, [])
        for i in ids:
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
        # Only agents.passages.create is used when skip_vector_storage=False, but our tests skip it
        self.agents = types.SimpleNamespace(passages=_AgentsPassages())


letta_client.Letta = Letta
letta_client.AsyncLetta = AsyncLetta
sys.modules['letta_client'] = letta_client


from ai_memory_sdk import Memory  # noqa: E402


def test_instance_scoped_subject():
    memory = Memory(subject_id="user_sarah")

    memory.initialize_memory(
        label="preferences",
        description="Known user preferences.",
        value="Likes cats",
        reset=True,
    )

    # Use unified add_messages with bound subject
    run = memory.add_messages([
        {"role": "user", "content": "I love cats"}
    ])
    memory.wait_for_run(run)

    raw = memory.get_memory("preferences")
    assert raw == "Likes cats"

    formatted = memory.get_memory("preferences", prompt_formatted=True)
    assert formatted is not None and formatted.startswith("<preferences") and "Likes cats" in formatted

    blocks = memory.list_blocks()
    labels = [getattr(b, 'label', None) or b.get('label') for b in blocks]
    assert labels == ["preferences"]

    memory.delete_block("preferences")
    assert memory.get_memory("preferences") is None


def test_explicit_subject():
    memory = Memory()

    agent_id = memory.initialize_subject("project_alpha", reset=True)
    assert isinstance(agent_id, str)

    memory.initialize_memory(
        label="spec",
        description="Project spec",
        value="v1",
        subject_id="project_alpha",
    )

    run = memory.add_messages_for_subject("project_alpha", [{"role": "user", "content": "Kickoff complete"}])
    memory.wait_for_run(run)

    spec = memory.get_memory("spec", subject_id="project_alpha")
    assert spec == "v1"
