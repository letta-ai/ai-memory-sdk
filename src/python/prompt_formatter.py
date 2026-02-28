from typing import List, Dict, Any, Optional
from schemas import Message, File


messages_prompt = "The following message interactions have occured"
messages_tag = "messages"
message_total_char_limit = 5000 # how many character are included in a message chunk accross all messages

sleep_tag = "sleep_consolidation"

file_tag = "file"
file_part_tag = "file_part"
file_char_limit = 20000 # how many character to include in file part 

def format_messages(messages: List[Message]) -> List[str]:
    """
    Format messages like the following: 

    user: hi my name is sarah
    assistant: Hello Sarah! I'm Sam. smiles warmly There's something special about first meetings, don't you think? Like opening a book to its first page, full of possibilities. I'd love to get to know you better - what brings you here today?
    assistant: Tool call returned Sent message successfully.

    """
    message_history = "\n".join([
        f"{msg.role}: {msg.content}" for msg in messages
    ])

    return [{"role": "user", "content": f"<{messages_tag}>{messages_prompt}:\n{message_history}</{messages_tag}>"}]

def format_sleep_prompt(
    blocks: List[Any],
    archival_passages: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    """
    Format a sleep/consolidation prompt containing the current memory state.

    The prompt asks the agent to review its own memory blocks and consolidate them:
    resolve contradictions, merge redundancies, prune stale info, and reorganize.
    """
    # Format current block state
    block_lines = []
    for block in blocks:
        label = getattr(block, "label", None)
        description = getattr(block, "description", "")
        value = getattr(block, "value", "")
        if label is None:
            continue
        block_lines.append(
            f'<block label="{label}" description="{description}">\n{value}\n</block>'
        )
    blocks_section = "\n\n".join(block_lines)

    # Optional archival section
    archival_section = ""
    if archival_passages:
        passages_text = "\n".join(f"- {p}" for p in archival_passages)
        archival_section = (
            f"\n\nThe following are recent passages from archival (long-term) memory. "
            f"Consider whether any of this information should be promoted into your "
            f"active memory blocks, or whether it reveals patterns worth capturing:\n"
            f"{passages_text}"
        )

    prompt = (
        f"<{sleep_tag}>\n"
        f"You are entering a sleep/consolidation phase. No new external information "
        f"is being provided. Instead, review your current memory state and improve it.\n\n"
        f"Your tasks:\n"
        f"1. Identify and resolve any contradictions between memory blocks\n"
        f"2. Merge redundant information that appears across multiple blocks\n"
        f"3. Remove or condense stale or outdated information\n"
        f"4. Strengthen connections between related facts across blocks\n"
        f"5. Reorganize information within blocks for clarity and coherence\n"
        f"6. Note any gaps in your knowledge that future conversations should address\n\n"
        f"Current memory blocks:\n{blocks_section}"
        f"{archival_section}\n\n"
        f"Update your memory blocks to reflect a consolidated, coherent understanding. "
        f"Do not fabricate new information — only reorganize and refine what you already know.\n"
        f"</{sleep_tag}>"
    )

    return [{"role": "user", "content": prompt}]


def format_files(files: List[File]) -> List[Dict[str, str]]:
    """
    Format files into multiple separate messages, ensuring each message stays under file_char_limit.
    Each file part becomes its own message.
    """
    all_messages = []
    
    for file in files:
        try:
            # Read file content from disk
            with open(file.file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except Exception as e:
            # If we can't read the file, send an error message
            error_msg = f"<{file_tag} label=\"{file.label}\" description=\"{file.description}\">[Error reading file: {str(e)}]</{file_tag}>"
            all_messages.append({"role": "user", "content": error_msg})
            continue
            
        # chunk up file content into parts 
        file_content_chunks = [file_content[i:i + file_char_limit] for i in range(0, len(file_content), file_char_limit)]
        
        # Create a separate message for each file part
        for i, chunk in enumerate(file_content_chunks):
            part_number = i + 1
            total_parts = len(file_content_chunks)
            
            # Create the message content for this specific part
            file_part_content = f"<{file_part_tag} part={part_number}/{total_parts}>{chunk}</{file_part_tag}>"
            file_message = f"<{file_tag} label=\"{file.label}\" description=\"{file.description}\">{file_part_content}</{file_tag}>"
            
            all_messages.append({"role": "user", "content": file_message})
    
    return all_messages
    

    
