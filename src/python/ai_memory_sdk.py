from typing import List, Dict, Any, Optional
import time
import os
from letta_client import Letta
from prompt_formatter import format_messages
from schemas import MessageCreate

class Memory: 
    """ A memory SDK for Letta

    Adds a general "subject" model while keeping user-specific helpers.
    One subject maps to one Letta agent; multiple labeled blocks (e.g. "human",
    "summary", "preferences") can be attached to that subject.
    """

    def __init__(self,
        api_key: Optional[str] = None,
        subject_id: Optional[str] = None,
    ):
        if api_key is None:
            api_key = os.getenv("LETTA_API_KEY")
        self.letta_client = Letta(token=api_key)
        # Optional default subject for instance-scoped operations
        self.subject_id = subject_id
        self._default_tag = "ai-memory-sdk"

    def _create_sleeptime_agent(self, name: str, tags: List[str]): 
        """ Create a subconscious agent that learns over time """ 
        # Ensure default SDK tag is present
        tags = list(dict.fromkeys((tags or []) + [self._default_tag]))
        agent_state = self.letta_client.agents.create(
            name=name,
            model="openai/gpt-4.1",
            agent_type="sleeptime_agent",
            initial_message_sequence=[], 
            tags=tags
        )
        return agent_state.id

    def _get_matching_agent(self, tags: List[str]): 
        """ Get an agent with matching tags """ 
        agents = self.letta_client.agents.list(tags=tags, match_all_tags=True)
        if agents:
            return agents[0]
        return None

    def _subject_tags(self, subject_id: str) -> List[str]:
        """Standardize tags for a subject. Include namespaced, raw, and SDK tag."""
        return [f"subj:{subject_id}", subject_id, self._default_tag]

    def _get_agent_for_subject(self, subject_id: str):
        """Find an agent for a given subject. Tries both new and legacy tag styles."""
        # Prefer the namespaced tag
        agent = self._get_matching_agent(tags=[f"subj:{subject_id}"])
        if agent:
            return agent
        # Fallback to raw tag only
        return self._get_matching_agent(tags=[subject_id])


    def _create_context_block(self, agent_id: str, label: str, description: str, char_limit: int = 10000, value: str = ""):
        """ Create a memory block for a subject """
        block = self.letta_client.blocks.create(
            label=label,
            description=description,
            limit=char_limit,
            value=value,
        )
        self.letta_client.agents.blocks.attach(agent_id=agent_id, block_id=block.id)
        return block.id

    def _list_context_blocks(self, agent_id: str):
        """ List all subject blocks for an agent """ 
        return self.letta_client.agents.blocks.list(agent_id=agent_id)

    def _delete_context_block(self, agent_id: str, block_id: str):
        """ Delete a context block """ 
        self.letta_client.agents.blocks.detach(agent_id=agent_id, block_id=block_id)
        self.letta_client.blocks.delete(block_id=block_id)

    def _delete_agent(self, agent_id: str):
        """ Delete an agent """ 
        self.letta_client.agents.delete(agent_id=agent_id)

    def _ensure_subject(self, subject_id: str) -> str:
        """Ensure a subject exists and return its agent id."""
        agent = self._get_agent_for_subject(subject_id)
        if agent:
            return agent.id
        # Create a new agent for this subject with both tags for compatibility
        agent_id = self._create_sleeptime_agent(name=f"subconscious_agent_subject_{subject_id}", tags=self._subject_tags(subject_id))
        # Create initial passage in archival memory
        self.letta_client.agents.passages.create(
            agent_id=agent_id,
            text=f"Initialized memory for subject {subject_id}",
            tags=[self._default_tag],
        )
        return agent_id

    def _get_effective_subject(self, subject_id: Optional[str]) -> str:
        """Resolve the effective subject id, preferring the instance default if not provided."""
        sid = subject_id or self.subject_id
        if not sid:
            raise ValueError("No subject_id provided and instance is not bound to a subject. "
                             "Pass subject_id=... or initialize Memory(subject_id=...).")
        return sid

    def _find_block_by_label(self, agent_id: str, label: str):
        """Find a block object attached to an agent by label, or return None."""
        blocks = self._list_context_blocks(agent_id)
        for b in blocks:
            b_label = getattr(b, "label", None)
            if b_label is None and isinstance(b, dict):
                b_label = b.get("label")
            if b_label == label:
                return b
        return None

    def _block_id(self, block_obj: Any) -> Optional[str]:
        """Get id from a block object that may be a model or dict."""
        if block_obj is None:
            return None
        bid = getattr(block_obj, "id", None)
        if bid is None and isinstance(block_obj, dict):
            bid = block_obj.get("id")
        return bid

    def _learn_messages_sync(
        self,
        agent_id: str,
        messages: List[Dict[str, Any]],
        skip_vector_storage: bool,
    ) -> str:
        """Learn messages and optionally store in archival memory.

        Args:
            agent_id: The Letta agent ID
            messages: List of messages to process
            skip_vector_storage: If False, also store messages in archival memory

        Returns:
            The run ID for tracking processing
        """
        formatted_messages = format_messages([MessageCreate(**msg) for msg in messages])
        letta_run = self.letta_client.agents.messages.create_async(
            agent_id=agent_id,
            messages=formatted_messages
        )

        # insert into archival memory sequentially
        if not skip_vector_storage:
            for message in messages:
                self.letta_client.agents.passages.create(
                    agent_id=agent_id,
                    text=message["content"],
                    tags=[message["role"], self._default_tag],
                )

        return letta_run.id

    def _format_block(self, block): 
        """ Format a block for a prompt """ 
        return f"<{block.label} description=\"{block.description}\">{block.value}</{block.label}>"

    def _get_run_status(self, run_id: str):
        """ Get the status of a run """ 

        run = self.letta_client.runs.retrieve(run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")
        return run.status

    def wait_for_run(self, run_id: str, timeout: int = 300):
        """Wait for a run to complete.

        Args:
            run_id: The run ID to wait for
            timeout: Maximum time to wait in seconds (default: 300)

        Raises:
            TimeoutError: If the run doesn't complete within the timeout period
        """
        start_time = time.time()
        while self._get_run_status(run_id) != "completed":
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Run {run_id} did not complete within {timeout} seconds")
            time.sleep(1)

    # ===== General Subject API =====

    def initialize_subject(self, subject_id: str, reset: bool = False) -> str:
        """Initialize a subject (agent). If it exists and reset is False, raise; otherwise recreate.

        Returns the agent id for the subject.
        """
        agent = self._get_agent_for_subject(subject_id)
        if agent:
            if reset:
                self._delete_agent(agent.id)
            else:
                raise ValueError(
                    f"Agent {agent.id} already exists for subject {subject_id}. "
                    f"Cannot re-initialize unless reset=True."
                )
        return self._ensure_subject(subject_id)

    def list_blocks(self, subject_id: Optional[str] = None):
        """List all blocks for a subject. If instance is bound, subject_id may be omitted."""
        sid = self._get_effective_subject(subject_id)
        agent = self._get_agent_for_subject(sid)
        if not agent:
            return []
        return self._list_context_blocks(agent.id)

    def initialize_memory(
        self,
        label: str,
        description: str,
        value: str = "",
        char_limit: int = 10000,
        reset: bool = False,
        subject_id: Optional[str] = None,
    ) -> str:
        """Create (or optionally reset) a labeled block within a subject.

        If the block exists and reset=False, this is a no-op and returns the existing block id.
        """
        sid = self._get_effective_subject(subject_id)
        agent_id = self._ensure_subject(sid)

        existing = self._find_block_by_label(agent_id, label)
        if existing and reset:
            self._delete_context_block(agent_id, self._block_id(existing))
            existing = None

        if existing:
            return self._block_id(existing)

        return self._create_context_block(
            agent_id=agent_id,
            label=label,
            description=description,
            char_limit=char_limit,
            value=value,
        )

    def get_memory(
        self,
        label: str,
        prompt_formatted: bool = False,
        subject_id: Optional[str] = None,
    ) -> Optional[str]:
        """Retrieve a labeled block from a subject. Returns None if missing."""
        sid = self._get_effective_subject(subject_id)
        agent = self._get_agent_for_subject(sid)
        if not agent:
            return None
        block = self._find_block_by_label(agent.id, label)
        if not block:
            return None
        if prompt_formatted:
            return self._format_block(block)
        value = getattr(block, "value", None)
        if value is None and isinstance(block, dict):
            value = block.get("value")
        return value

    def delete_block(self, label: str, subject_id: Optional[str] = None):
        """Delete a labeled block from a subject if it exists."""
        sid = self._get_effective_subject(subject_id)
        agent = self._get_agent_for_subject(sid)
        if not agent:
            return
        block = self._find_block_by_label(agent.id, label)
        if block:
            self._delete_context_block(agent.id, self._block_id(block))

    def add_messages_for_subject(
        self,
        subject_id: str,
        messages: List[Dict[str, Any]],
        skip_vector_storage: bool = True,
    ) -> str:
        """Add messages to a specific subject (generalized API)."""
        agent = self._get_agent_for_subject(subject_id)
        if agent:
            agent_id = agent.id
        else:
            agent_id = self._ensure_subject(subject_id)
        return self._learn_messages_sync(agent_id, messages, skip_vector_storage=skip_vector_storage)

    def add_messages_here(self, messages: List[Dict[str, Any]], skip_vector_storage: bool = True) -> str:
        """Add messages using the instance's bound subject_id."""
        sid = self._get_effective_subject(None)
        return self.add_messages_for_subject(sid, messages, skip_vector_storage=skip_vector_storage)

    def initialize_user_memory(self,
        user_id: str,
        user_context_block_prompt: str = "Details about the human user you are speaking to.",
        user_context_block_char_limit: int = 10000,
        user_context_block_value: str = "",
        summary_block_prompt: str = "A short (1-2 sentences) running summary of the conversation.",
        summary_block_char_limit: int = 1000,
        reset: bool = False # whether to reset existing memory
    ):
        """Initialize a user's memory with default blocks (human, summary).

        Args:
            user_id: Unique identifier for the user
            user_context_block_prompt: Description for the human block
            user_context_block_char_limit: Character limit for the human block
            user_context_block_value: Initial value for the human block
            summary_block_prompt: Description for the summary block
            summary_block_char_limit: Character limit for the summary block
            reset: If True, delete and recreate existing agent

        Returns:
            The Letta agent ID for this user
        """

        # check if agent already exists
        agent = self._get_matching_agent(tags=[user_id])
        if agent:
            if reset:
                self._delete_agent(agent.id)
            else:
                raise ValueError(f"Agent {agent.id} already exists for user {user_id}. Cannot re-initialize memory unless reset=True.")

        # create the Letta agent
        agent_id = self._create_sleeptime_agent(name=f"subconscious_agent_user_{user_id}", tags=[user_id])

        # create memory blocks
        self._create_context_block(agent_id=agent_id, label="human", description=user_context_block_prompt, char_limit=user_context_block_char_limit, value=user_context_block_value)
        self._create_context_block(agent_id=agent_id, label="summary", description=summary_block_prompt, char_limit=summary_block_char_limit, value="")

        # create initial passage in archival memory
        self.letta_client.agents.passages.create(
            agent_id=agent_id,
            text=f"Initialized memory for user {user_id}",
            tags=[self._default_tag],
        )
        return agent_id
            
    def add_messages(self, user_or_messages, messages: Optional[List[Dict[str, Any]]] = None, skip_vector_storage: bool = True): 
        """Add messages.

        Two modes:
        - Legacy user mode: add_messages(user_id: str, messages: List[...], skip_vector_storage=True)
        - Subject-bound mode: add_messages(messages: List[...], skip_vector_storage=True) when this instance
          was constructed with a subject_id.
        """
        # If first arg is a string, treat as legacy user mode
        if isinstance(user_or_messages, str):
            user_id = user_or_messages
            if messages is None:
                raise ValueError("messages must be provided when calling add_messages(user_id, messages, ...)" )
            agent = self._get_matching_agent(tags=[user_id])
            if agent:
                agent_id = agent.id
            else:
                agent_id = self.initialize_user_memory(user_id)
            return self._learn_messages_sync(agent_id, messages, skip_vector_storage=skip_vector_storage)

        # Otherwise, treat first arg as the messages list and use the bound subject
        inferred_messages = user_or_messages
        if not isinstance(inferred_messages, list):
            raise ValueError("First argument must be a user_id (str) or a messages list (List[Dict]).")
        sid = self._get_effective_subject(None)
        return self.add_messages_for_subject(sid, inferred_messages, skip_vector_storage=skip_vector_storage)

    def add_files(self, files: List[Dict[str, Any]]):
        """ Learn about files """ 
        raise NotImplementedError

    def get_user_memory(self, user_id: str, prompt_formatted: bool = False):
        """ Get the memory for a specific user """ 
        agent = self._get_matching_agent(tags=[user_id])
        if agent:
            block = self.letta_client.agents.blocks.retrieve(agent.id, "human")
            if prompt_formatted: 
                return self._format_block(block)
            return block.value
        return None


    def get_summary(self, user_id: str, prompt_formatted: bool = False):
        """ Get the summary for a specific user """ 
        agent = self._get_matching_agent(tags=[user_id])
        if agent:
            block = self.letta_client.agents.blocks.retrieve(agent.id, "summary")
            if prompt_formatted: 
                return f"<conversation_summary>{block.value}</conversation_summary>"
            return block.value
        return None

    def get_memory_agent_id(self, user_id: str):
        """ Get the agent ID for a specific user """ 
        agent = self._get_matching_agent(tags=[user_id])
        if agent:
            return agent.id
        return None

    def delete_user(self, user_id: str):
        """ Delete a user """ 
        agent = self._get_matching_agent(tags=[user_id])
        if agent:
            # deleting the agent also deleted associated messages/blocks
            self.letta_client.agents.delete(agent.id)
            print(f"Deleted agent {agent.id} for user {user_id}")

    def search(self, user_id: str, query: str, tags: Optional[List[str]] = None):
        """Search for stored user messages via semantic search.

        Default filters to user messages (tags=["user"]).
        Pass a custom list of tags to adjust filtering (e.g., ["assistant"], or [] for all).
        """
        agent = self._get_matching_agent(tags=[user_id])
        if agent:
            search_tags = tags if tags is not None else ["user"]
            response = self.letta_client.agents.passages.search(agent_id=agent.id, query=query, tags=search_tags)
            return [result.content for result in response.results]
