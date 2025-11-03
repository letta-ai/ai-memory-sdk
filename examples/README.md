# AI Memory SDK Examples

This directory contains practical examples demonstrating different use cases and features of the AI Memory SDK.

## Quick Start Examples

### Basic Chat (`chat.py`)
Simple conversational AI with user memory.

```bash
python examples/chat.py
```

**Demonstrates:**
- User-focused memory helpers
- Injecting memory blocks into system prompts
- Basic conversational flow

---

### Subject API (`subject.py`)
Core subject-based memory management.

```bash
python examples/subject.py
```

**Demonstrates:**
- Instance-scoped subjects
- Explicit subject management
- Creating and managing multiple memory blocks
- Block CRUD operations

---

### Multiple Memory Blocks (`multicontext.py`)
Working with multiple blocks per subject.

```bash
python examples/multicontext.py
```

**Demonstrates:**
- Creating multiple blocks with different purposes
- How Letta agents update blocks based on descriptions
- Retrieving and displaying block contents

---

## Advanced Examples

### Archival Memory Search (`archival_search.py`)
Using Letta's archival memory for semantic search.

```bash
python examples/archival_search.py
```

**Demonstrates:**
- Storing messages in archival memory (`skip_vector_storage=False`)
- Semantic search over conversation history
- Injecting search results into context
- Building context-aware responses

**Key concepts:**
- Archival memory is opt-in via `skip_vector_storage=False`
- Search returns relevant passages from all stored messages
- Useful for long conversations or historical context

---

### Customer Support Bot (`customer_support.py`)
Real-world customer support use case with multiple specialized blocks.

```bash
python examples/customer_support.py
```

**Demonstrates:**
- Multiple memory blocks serving different purposes:
  - `customer_profile`: Slowly-changing customer information
  - `support_history`: Evolving summary of interactions
  - `policies`: Read-only reference information
- How block descriptions guide the Letta agent's updates
- Building comprehensive system prompts from multiple blocks
- Practical workflow for interactive applications

**Key concepts:**
- Different blocks have different update patterns
- Well-written descriptions help the agent update blocks correctly
- Memory blocks can serve as both writeable state and read-only reference

---

### Memory Compaction (`chat_with_compaction.py`)
Advanced pattern for managing memory growth.

```bash
python examples/chat_with_compaction.py
```

**Demonstrates:**
- Strategies for handling long conversations
- Message batching to reduce costs
- When to trigger memory updates

---

## TypeScript Examples

### Chat (`chat.ts`)
TypeScript equivalent of the basic chat example.

```bash
npm run build
node dist/examples/chat.js
```

### Subject API (`subject.ts`)
TypeScript equivalent of the subject API example.

```bash
npm run build
node dist/examples/subject.js
```

---

## Environment Setup

All examples require a Letta API key:

```bash
export LETTA_API_KEY="your_letta_api_key"
```

Examples that use OpenAI also require:

```bash
export OPENAI_API_KEY="your_openai_api_key"
```

---

## Example Selection Guide

**New to the SDK?** Start with:
1. `subject.py` - Learn the core concepts
2. `chat.py` - See a practical chat application
3. `multicontext.py` - Understand multiple blocks

**Want to explore advanced features?**
- `archival_search.py` - Learn about semantic search
- `customer_support.py` - See a production-like use case

**Working on cost optimization?**
- `chat_with_compaction.py` - Memory management patterns

---

## Tips for Building Your Own Applications

1. **Block Descriptions Matter**: The description field guides how the Letta agent updates blocks. Be specific about what should be stored and when.

2. **Start with Few Blocks**: Begin with 2-3 blocks (like `human`, `summary`), then add more as needed.

3. **Batch Messages**: Call `add_messages()` with 5-10 messages at once to reduce costs, not after every single turn.

4. **Use Archival Sparingly**: Only set `skip_vector_storage=False` for messages you actually want to search later.

5. **Wait When Needed**: Call `wait_for_run()` when you need the latest block updates immediately. Otherwise, let updates happen asynchronously.

6. **Test Block Descriptions**: Experiment with different block descriptions to see what works best for your use case.

---

## Additional Resources

- [Main README](../README.md) - SDK overview and installation
- [Tutorial](../docs/tutorial.md) - Comprehensive walkthrough
- [Letta Docs](https://docs.letta.com) - Deep dive into Letta's architecture
- [Memory Blocks Guide](https://docs.letta.com/guides/agents/memory-blocks) - Best practices for designing blocks
