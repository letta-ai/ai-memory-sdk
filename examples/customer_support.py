"""
Example: Customer support bot with multiple memory blocks

This example demonstrates a practical use case: a customer support chatbot that maintains:
- customer_profile: Basic customer information
- support_history: Summary of past support interactions
- policies: Company policies and procedures (read-only reference)

This showcases how different memory blocks serve different purposes:
- Some blocks are frequently updated (support_history)
- Some blocks are slowly changing (customer_profile)
- Some blocks provide reference information (policies)
"""

from openai import OpenAI
from ai_memory_sdk import Memory


def setup_support_bot(customer_id: str):
    """Initialize a customer support bot with multiple memory blocks"""

    memory = Memory(subject_id=customer_id)

    # Customer profile block - basic customer information
    memory.initialize_memory(
        label="customer_profile",
        description="Basic customer information including name, account type, and preferences. Update when customer provides new personal information.",
        value="Account type: Premium subscriber since 2023",
        char_limit=5000,
        reset=True,
    )

    # Support history block - evolving summary of past interactions
    memory.initialize_memory(
        label="support_history",
        description="A running summary of past support interactions, issues resolved, and ongoing concerns. Keep this concise and chronological.",
        value="",
        char_limit=8000,
        reset=True,
    )

    # Policies block - reference information
    memory.initialize_memory(
        label="policies",
        description="Company policies and procedures relevant to this customer. Read-only reference for the support agent.",
        value="""Premium Support Policies:
- Response time: 4 hours maximum
- Refund policy: Full refund within 30 days, prorated after
- Escalation: Technical issues go to engineering team
- Priority: Premium customers get priority queue
- Available 24/7 via chat, email, phone""",
        char_limit=10000,
        reset=True,
    )

    return memory


def handle_support_request(memory: Memory, customer_message: str) -> str:
    """Process a customer support request with memory context"""

    openai_client = OpenAI()

    # Retrieve all memory blocks for context
    customer_profile = memory.get_memory("customer_profile", prompt_formatted=True)
    support_history = memory.get_memory("support_history", prompt_formatted=True)
    policies = memory.get_memory("policies", prompt_formatted=True)

    # Build comprehensive system prompt
    system_prompt = f"""You are a helpful customer support agent. Use the customer information below to provide personalized, policy-compliant support.

{customer_profile}

{support_history}

{policies}

Important:
- Be empathetic and professional
- Reference past interactions when relevant
- Follow company policies strictly
- Update support history as you resolve issues"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": customer_message}
    ]

    # Generate response
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
    )

    assistant_response = response.choices[0].message.content

    # Update memory with this interaction
    # The Letta agent will automatically update relevant blocks based on their descriptions
    messages.append({"role": "assistant", "content": assistant_response})
    run = memory.add_messages(messages)
    memory.wait_for_run(run)

    return assistant_response


def demo_support_session():
    """Demonstrate a customer support session"""

    customer_id = "customer_alice_123"
    print(f"=== Customer Support Bot Demo ===")
    print(f"Customer ID: {customer_id}\n")

    # Setup
    print("Initializing support bot with memory blocks...")
    memory = setup_support_bot(customer_id)
    print("✓ Bot initialized with customer_profile, support_history, and policies blocks\n")

    # Simulate a support conversation
    interactions = [
        "Hi, I'm having trouble logging into my account. I keep getting an error message.",
        "My name is Alice Johnson. I've been a customer for about 2 years.",
        "The error says 'Invalid credentials' but I'm sure my password is correct.",
        "Oh wait, I might have caps lock on. Let me try again... Yes! That worked. Thanks!",
    ]

    for i, customer_msg in enumerate(interactions, 1):
        print(f"Customer: {customer_msg}")
        response = handle_support_request(memory, customer_msg)
        print(f"Agent: {response}\n")

        if i < len(interactions):
            input("Press Enter to continue...")
            print()

    # Show final memory state
    print("\n=== Final Memory State ===")
    print("\nCustomer Profile:")
    print(memory.get_memory("customer_profile"))

    print("\n\nSupport History:")
    print(memory.get_memory("support_history"))

    print("\n\n✓ Memory blocks updated with interaction details")


if __name__ == "__main__":
    demo_support_session()
