from ai_memory_sdk import Memory


def instance_scoped_example():
    print("== Instance-scoped subject example ==")
    memory = Memory(subject_id="user_sarah")

    # Create/ensure a block in this subject
    memory.initialize_memory(
        label="preferences",
        description="Known user preferences.",
        value="Likes cats",
        reset=True,
    )

    # Add a history block
    memory.initialize_memory(
        label="history",
        description="User history.",
        value="",
        reset=True,
    )

    # Add messages to the bound subject (unified API)
    run = memory.add_messages([
        {"role": "user", "content": "I love cats, and one time I went to the park"},
        {"role": "assistant", "content": "That sounds fun!"},
        {"role": "user", "content": "I also like dogs"},
        {"role": "assistant", "content": "Dogs are great too!"},
        {"role": "user", "content": "I was born in 1821. I fought in the War."},

    ])
    memory.wait_for_run(run)

    # Read blocks (raw and formatted)
    raw = memory.get_memory("preferences")
    formatted = memory.get_memory("preferences", prompt_formatted=True)
    print("Raw:", raw)
    print("Formatted:", formatted)

    # Read blocks (raw and formatted)
    raw = memory.get_memory("history")
    formatted = memory.get_memory("history", prompt_formatted=True)
    print("Raw:", raw)
    print("Formatted:", formatted)

    # Read blocks (raw and formatted)
    raw = memory.get_memory("history")
    formatted = memory.get_memory("history", prompt_formatted=True)
    print("Raw:", raw)
    print("Formatted:", formatted)

    # Read blocks (raw and formatted)
    raw = memory.get_memory("history")
    formatted = memory.get_memory("history", prompt_formatted=True)
    print("Raw:", raw)
    print("Formatted:", formatted)

    # # List and delete
    # blocks = memory.list_blocks()
    # print("Blocks:", [b.label if hasattr(b, 'label') else b.get('label') for b in blocks])
    # memory.delete_block("preferences")
    # memory.delete_block("history")
    # print("Deleted 'preferences'")

if __name__ == "__main__":
    instance_scoped_example()
