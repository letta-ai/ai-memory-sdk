# AI Memory SDK

The AI Memory SDK is a lightweight wrapper around [Letta](https://letta.com)'s advanced memory management capabilities. Letta is a platform for building stateful AI agents that truly remember, learn, and evolve. The memory SDK exposes Letta's sophisticated memory architecture through a simplified interface for general-purpose use cases like user profiles, conversation summaries, and domain-specific knowledge bases.

Under the hood, the SDK creates a "subconscious agent"—a Letta agent configured to manage memory blocks. When you send messages, the agent asynchronously processes them and updates its memory blocks. This architecture leverages Letta's core strengths in persistent memory and stateful learning while providing a streamlined API for common memory patterns.

The SDK organizes memory around three concepts:

- **Subjects**: what memory is "about" (e.g., `user_sarah`, `project_alpha`, `team_support`). Each subject is backed by a Letta agent with its own memory state.
- **Blocks**: named memory sections within a subject (e.g., `human`, `summary`, `policies`, `history`, `preferences`). These correspond to Letta's [memory blocks](https://docs.letta.com/guides/agents/memory-blocks)—customizable, labeled sections that persist in the agent's core memory.
- **Messages**: conversation turns you send to update memory. When you add messages, the Letta agent processes them and updates relevant blocks asynchronously.

This enables user profiles and conversation summaries, plus broader use cases like policy digests, running histories, study guides, or any domain‑specific memory you define.

See Letta's YouTube channel for more information on how to design memory architecture. [This video](https://youtu.be/o4boci1xSbM) provides a general overview.

Quick mental model—blocks live in the agent's context window (core memory), updated automatically as messages flow through:
```
+========================================+
|         SYSTEM PROMPT                  |
+========================================+
|   CORE MEMORY (BLOCKS)                 | <- Letta agent updates over time
|   - <human> ... </human>               |
|   - <summary> ... </summary>           |
|   - <policies> ... </policies>         |
|   - <history> ... </history>           |
+========================================+
|           MESSAGES                     |
|  * User -> Assistant                   |
|  * User -> Assistant                   |
|  * ...                                 |
+========================================+
```

Messages can optionally be stored in archival memory (Letta's external long-term storage) by setting `skip_vector_storage=False`, enabling semantic search to retrieve relevant passages and inject them back into context.

## Subject Model (Generalized API)

In addition to the user-specific helpers, the SDK supports a generalized "subject" model:
- **Subject**: the unit we learn for (one subject = one Letta agent). For example, `user_sarah`, `team_alpha`, or `project_123`.
- **Blocks**: named pieces of memory (e.g. `human`, `summary`, `preferences`) attached to the subject's agent.
- **Messages**: conversation turns the learner uses to update one or more blocks.

You can bind a Memory instance to a subject at construction time, or pass a subject per call.

### Naming conventions

- **Agents**: the subject_id is embedded in the agent name (e.g., `subconscious_agent_subject_<subject_id>`). Ensure your `subject_id` uses only characters allowed by Letta agent names. Recommended: letters, numbers, underscores, and dashes. Avoid characters like `:` or other punctuation.
- **Blocks and tags**: follow your Letta deployment’s rules. Recommended: letters, numbers, underscores, and dashes.


**Python (instance-scoped)**:
```python
from ai_memory_sdk import Memory

memory = Memory(subject_id="user_sarah")

# Create a new block in this subject (no-op if it exists and reset=False)
memory.initialize_memory(
    label="preferences",
    description="Known user preferences.",
    value="Likes cats",
)

# Add conversation messages to the bound subject (unified API)
memory.add_messages([
    {"role": "user", "content": "I love cats"}
])

# Retrieve a block (raw or prompt formatted)
raw = memory.get_memory("preferences")
formatted = memory.get_memory("preferences", prompt_formatted=True)
```


**Python (explicit subject)**:
```python
from ai_memory_sdk import Memory

memory = Memory()
memory.initialize_subject("project_alpha", reset=True)
memory.initialize_memory("spec", "Project spec", value="v1", subject_id="project_alpha")
run = memory.add_messages_for_subject("project_alpha", [{"role": "user", "content": "Kickoff done"}])
memory.wait_for_run(run)
spec = memory.get_memory("spec", subject_id="project_alpha")
```


**TypeScript (instance-scoped)**:
```ts
import { Memory } from '@letta-ai/memory-sdk'

const memory = new Memory({ subjectId: 'user_sarah' })
await memory.initializeMemory('preferences', 'Known user preferences.', 'Likes cats')
// unified API when instance is bound to a context
await memory.addMessages([{ role: 'user', content: 'I love cats' }])
const formatted = await memory.getMemory('preferences', true)
```


**TypeScript (explicit subject)**:
```ts
const memory = new Memory()
await memory.initializeSubject('project_alpha', true)
await memory.initializeMemory('spec', 'Project spec', 'v1', 10000, false, 'project_alpha')
const run = await memory.addMessagesToSubject('project_alpha', [{ role: 'user', content: 'Kickoff done' }])
await memory.waitForRun(run)
```

## Quickstart

1. Create a [Letta API key](https://app.letta.com/api-keys)
2. Install: `pip install ai-memory-sdk`

### Usage: Generic Memory Blocks
Leverage Letta's memory block system to maintain persistent, evolving memory. Define blocks (human, summary, policies, history, study_guide, ...) with custom labels and descriptions. As you send messages, the Letta agent updates relevant blocks based on their descriptions. Retrieve blocks and inject them into your system prompts for context-aware interactions.

**Example:** Create a basic OpenAI `gpt-4o-mini` chat agent with subject‑scoped memory

```python
from openai import OpenAI
from ai_memory_sdk import Memory

# Memory is a lightweight wrapper around Letta's memory management.
# It creates a Letta agent to handle persistent memory for your conversations.
#
# Assumes LETTA_API_KEY environment variable, or pass api_key="your_api_key"
memory = Memory()

# Set up your OpenAI client like you normally would.
# This example assumes that the OpenAI key is stored in the OPENAI_API_KEY
# environment variable.
openai_client = OpenAI()

def chat_with_memories(message: str, user_id: str = "default_user") -> str:
    # Retrieve or initialize the subject (using user helpers for simplicity)
    user_memory = memory.get_user_memory(user_id)
    if not user_memory:
        memory.initialize_user_memory(user_id, reset=True)
        user_memory = memory.get_user_memory(user_id)

    # the contents of the human block formatted as a prompt:
    #
    # <human description="Details about the human user you are speaking to.">
    # Name: Sarah
    # Interests: Likes cats (2025-09-04)
    # </human>
    user_memory_prompt= memory.get_user_memory(user_id, prompt_formatted=True)
    print(user_memory_prompt)

    # Generate the assistant response using the inference engine of your choice,
    # OpenAI in this case.
    system_prompt = f"<system>You are a helpful AI assistant</system>"
    system_prompt += f"\n{user_memory_prompt}"

    # Create the list of message
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message}
    ]

    # Send the messages to the OpenAI API
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    # Extract the assistant's message from the API response
    assistant_response = response.choices[0].message.content

    # Send the conversation to the Letta agent to update memory blocks
    print("Updating memory...")
    messages.append({"role": "assistant", "content": assistant_response})
    memory.add_messages(user_id, messages)

    return assistant_response

def main():
    print("Chat with AI (type 'exit' to quit)")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == 'exit':
            print("Goodbye!")
            break
        print(f"AI: {chat_with_memories(user_input)}")

if __name__ == "__main__":
    main()

```
You can also search archival memory with `memory.search(user_id, query)` to retrieve relevant historical messages (requires `skip_vector_storage=False` when adding messages).

## SDK Reference

You can initialize the memory SDK with:
```python
from ai_memory_sdk import Memory

memory = Memory(api_key="LETTA_API_KEY")
```

### Adding memories

Send messages to the Letta agent to update memory blocks:
```python
run = memory.add_messages("user_id", [{"role": "user", "content": "hi"}])
```
The Letta agent processes messages asynchronously and updates relevant blocks based on their descriptions. The `run` object tracks this processing.
> [!WARNING]
> Each call to `add_messages(...)` invokes the Letta agent. To reduce costs, send messages in batches (recommended 5-10) or only when messages are evicted from context.

### Waiting for learning to complete

Messages are processed asynchronously, so to ensure all memory updates are reflected you should wait for the Letta agent to complete processing.
```python
memory.wait_for_run(run)
```
This blocks until the Letta agent finishes updating memory blocks.

### Getting memories for a user

Retrieve memory blocks (core memory) for the summary and/or user memory:
```python
summary = memory.get_summary("user_id", prompt_formatted=True)
user_memory = memory.get_user_memory("user_id", prompt_formatted=True)
```
To get the raw block value instead of formatted XML, pass `prompt_formatted=False`.

### Generalized Subject API

You can work with arbitrary subjects (one subject = one Letta agent) and labeled blocks within them. You can bind a `Memory` instance to a subject or pass a subject per call.

Constructor (instance-scoped subject):
```python
from ai_memory_sdk import Memory
memory = Memory(subject_id="user_sarah")
```

**Subject methods (Python)**:
- `initialize_subject(subject_id: str, reset: bool = False) -> str`
- `list_blocks(subject_id: Optional[str] = None) -> list`
- `initialize_memory(label: str, description: str, value: str = "", char_limit: int = 10000, reset: bool = False, subject_id: Optional[str] = None) -> str`
- `get_memory(label: str, prompt_formatted: bool = False, subject_id: Optional[str] = None) -> Optional[str]`
- `delete_block(label: str, subject_id: Optional[str] = None) -> None`
- `add_messages_for_subject(subject_id: str, messages: list, skip_vector_storage: bool = True) -> str`
- Unified: `add_messages(messages: list, skip_vector_storage: bool = True) -> str` (uses bound `subject_id`)

Example:
```python
memory = Memory(subject_id="user_sarah")
memory.initialize_memory("preferences", "Known user preferences.", "Likes cats")
run = memory.add_messages([{ "role": "user", "content": "I love cats" }])
memory.wait_for_run(run)
print(memory.get_memory("preferences", prompt_formatted=True))
```

### Searching messages

Search archival memory (passages) with semantic search:
```python
messages = memory.search("user_id", query="Favorite foods")
```

This searches Letta's archival memory (requires `skip_vector_storage=False` when adding messages). By default it filters to SDK-authored user messages (tags=["ai-memory-sdk", "user"]). To customize:
```python
messages = memory.search("user_id", query="system prompts", tags=["assistant"])  # assistant passages
messages = memory.search("user_id", query="any", tags=[])  # no tag filter
```

### Retrieving the memory agent

Each subject is backed by a Letta agent (using the sleeptime architecture). Get the agent's ID with:
```python
agent_id = memory.get_memory_agent_id("user_id")
```
View the agent at `https://app.letta.com/agents/<AGENT_ID>` to inspect its memory blocks and message history.

### Deleting user memories

Delete the Letta agent and all associated data (blocks, passages) for a user:
```python
memory.delete_user("user_id")
```


## Examples

- Conversational memory with user helpers: `examples/chat.py`
- Subject-based demo (generalized API): `examples/subject.py`
- Archival memory and semantic search: `examples/archival_search.py`
- Multi-block customer support bot: `examples/customer_support.py`
- TypeScript subject demo: `examples/subject.ts`
- Full tutorial: `docs/tutorial.md`
- Complete examples guide: `examples/README.md`


## Roadmap

- [x] Save messages as archival memories
- [x] Query messages
- [ ] Query messages by time
- [x] TypeScript support
- [ ] Learning from files
- [ ] Add "sleep" (offline collective revisioning of all data)

### Implementation notes

- Agents and passages created by this SDK include the tag `ai-memory-sdk` for discoverability and ops. The default search uses this tag in addition to role tags.
