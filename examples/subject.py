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

    # Add messages to the bound subject (unified API)
    run = memory.add_messages([
        {"role": "user", "content": "I love cats"}
    ])
    memory.wait_for_run(run)

    # Read blocks (raw and formatted)
    raw = memory.get_memory("preferences")
    formatted = memory.get_memory("preferences", prompt_formatted=True)
    print("Raw:", raw)
    print("Formatted:", formatted)

    # List and delete
    blocks = memory.list_blocks()
    print("Blocks:", [b.label if hasattr(b, 'label') else b.get('label') for b in blocks])
    memory.delete_block("preferences")
    print("Deleted 'preferences'")


def explicit_subject_example():
    print("== Explicit subject example ==")
    memory = Memory()

    # Initialize a named subject (agent)
    memory.initialize_subject("project_alpha", reset=True)

    # Create a block under this subject
    memory.initialize_memory(
        label="spec",
        description="Project spec",
        value="v1",
        subject_id="project_alpha",
    )

    # Add messages to that subject
    run = memory.add_messages_for_subject("project_alpha", [
        {"role": "user", "content": "Kickoff complete"}
    ])
    memory.wait_for_run(run)

    spec = memory.get_memory("spec", subject_id="project_alpha")
    print("Spec:", spec)


if __name__ == "__main__":
    instance_scoped_example()
    explicit_subject_example()
