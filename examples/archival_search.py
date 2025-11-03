"""
Example: Using archival memory search with the AI Memory SDK

This example demonstrates:
1. Storing messages in archival memory (Letta's long-term storage)
2. Searching archival memory with semantic search
3. Using search results to inject relevant context
"""

from openai import OpenAI
from ai_memory_sdk import Memory


def chat_with_archival_memory():
    """Chat assistant that stores and searches conversation history"""

    openai_client = OpenAI()
    memory = Memory()
    user_id = "demo_user"

    # Initialize user memory
    print("Initializing memory...")
    memory.initialize_user_memory(user_id, reset=True)

    # Simulate a conversation with archival storage enabled
    print("\n=== Building conversation history ===")
    conversation_history = [
        {"role": "user", "content": "I love Python programming, especially for data science"},
        {"role": "assistant", "content": "Python is great for data science! Libraries like pandas and numpy are very powerful."},
        {"role": "user", "content": "I also enjoy TypeScript for web development"},
        {"role": "assistant", "content": "TypeScript adds great type safety to JavaScript projects."},
        {"role": "user", "content": "My favorite framework is React with Next.js"},
        {"role": "assistant", "content": "Next.js is excellent for building full-stack React applications!"},
    ]

    # Store messages in archival memory (skip_vector_storage=False)
    print("Storing messages in archival memory...")
    run = memory.add_messages(user_id, conversation_history, skip_vector_storage=False)
    memory.wait_for_run(run)
    print("✓ Conversation stored in archival memory\n")

    # Now demonstrate search
    print("=== Searching archival memory ===")

    queries = [
        "programming languages",
        "web development",
        "frameworks",
    ]

    for query in queries:
        print(f"\nQuery: '{query}'")
        results = memory.search(user_id, query)

        if results:
            print(f"Found {len(results)} relevant messages:")
            for i, result in enumerate(results[:3], 1):
                print(f"  {i}. {result[:80]}...")
        else:
            print("  No results found")

    # Example: Using search to enhance a response
    print("\n\n=== Using search to enhance responses ===")
    new_query = "What programming languages does the user like?"

    # Search for relevant context
    relevant_context = memory.search(user_id, "programming languages")

    # Get user memory block
    user_memory_prompt = memory.get_user_memory(user_id, prompt_formatted=True)

    # Build enhanced system prompt with search results
    context_str = "\n".join([f"- {ctx}" for ctx in relevant_context[:3]])
    system_prompt = f"""You are a helpful AI assistant with access to conversation history.

{user_memory_prompt}

Relevant conversation history:
{context_str}

Use this context to provide accurate, personalized responses."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": new_query}
    ]

    print(f"\nUser question: {new_query}")
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    answer = response.choices[0].message.content
    print(f"Assistant: {answer}\n")

    # Store this new interaction
    messages.append({"role": "assistant", "content": answer})
    run = memory.add_messages(user_id, messages, skip_vector_storage=False)
    memory.wait_for_run(run)

    print("✓ New interaction stored in archival memory")


if __name__ == "__main__":
    print("Archival Memory Search Example")
    print("=" * 50)
    chat_with_archival_memory()
