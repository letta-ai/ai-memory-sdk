# AI Memory SDK (TypeScript)

A lightweight wrapper around [Letta](https://letta.com)'s advanced memory management capabilities. Letta is a platform for building stateful AI agents that truly remember, learn, and evolve. The memory SDK exposes Letta's sophisticated memory architecture through a simplified TypeScript interface for general-purpose use cases like user profiles, conversation summaries, and domain-specific knowledge bases.

Under the hood, the SDK creates Letta agents configured to manage memory blocks. When you send messages, the agent asynchronously processes them and updates its memory blocks. This architecture leverages Letta's core strengths in persistent memory and stateful learning while providing a streamlined API for common memory patterns.

## Installation

```bash
npm install @letta-ai/memory-sdk
# or
yarn add @letta-ai/memory-sdk
```

## Setup

1. Set your API keys:
```bash
export LETTA_API_KEY="your-letta-api-key"
```

2. Build the project:
```bash
npm run build
```

## Quick Start

```typescript
import { Memory } from '@letta-ai/memory-sdk';

// Initialize the memory client
const client = new Memory({ 
  lettaApiKey: process.env.LETTA_API_KEY 
});

// Initialize user memory
await client.initializeUserMemory('user_123');

// Add messages to user's memory
const runId = await client.addMessages('user_123', [
  {
    role: 'user',
    content: 'Hi my name is Bob'
  },
  {
    role: 'assistant',
    content: 'Hi Bob, how can I help you today?'
  }
]);

// Wait for processing to complete
await client.waitForRun(runId);

// Retrieve user memory
const memory = await client.getUserMemory('user_123');
console.log('User memory:', memory);

// Search user's message history
const searchResults = await client.search('user_123', 'Bob');
console.log('Search results:', searchResults);
```

## Subject Model (Generalized API)
Beyond user-specific helpers, you can work with arbitrary subjects. Each subject is backed by a Letta agent with its own memory state and can hold multiple labeled memory blocks in its core memory.

Instance-scoped subject:
```ts
import { Memory } from '@letta-ai/memory-sdk'

const memory = new Memory({ subjectId: 'user_sarah' })

// Create a block (no-op if it exists and reset=false)
await memory.initializeMemory('preferences', 'Known user preferences.', 'Likes cats')

// Add messages to the bound context (unified API)
await memory.addMessages([
  { role: 'user', content: 'I love cats' }
])

// Read a block
const formatted = await memory.getMemory('preferences', true)
```

Explicit subject per call:
```ts
const memory = new Memory()
await memory.initializeSubject('project_alpha', true)
await memory.initializeMemory('spec', 'Project spec', 'v1', 10000, false, 'project_alpha')
await memory.addMessagesToSubject('project_alpha', [{ role: 'user', content: 'Kickoff done' }])
```

Naming conventions
- Agents: subjectId is included in the created agent name (`subconscious_agent_subject_<subjectId>`). Ensure your `subjectId` contains only characters allowed by Letta agent names. Recommended: letters, numbers, underscores, and dashes. Avoid characters like `:`.
- Blocks and tags: follow your Letta deployment’s constraints. Recommended: letters, numbers, underscores, and dashes.

SDK tagging
- Letta agents and passages (archival memory) created by this SDK are tagged with `ai-memory-sdk` for discoverability. The default `search` includes this tag.

## API Reference

### Constructor

#### `new Memory(config?: MemoryConfig)`

Creates a new Memory instance.

```typescript
interface MemoryConfig {
  lettaApiKey?: string;  // Letta API key (or use LETTA_API_KEY env var)
  baseUrl?: string;      // Base URL for local Letta server
  subjectId?: string;    // Optional default subject for instance-scoped operations
}
```

**Examples:**

```typescript
// Using API key
const client = new Memory({ 
  lettaApiKey: "your-api-key" 
});

// Using local server
const client = new Memory({ 
  baseUrl: "http://localhost:8283" 
});

// Using environment variable
const client = new Memory(); // Uses LETTA_API_KEY env var
```

### Methods

#### Subject Methods
Work with arbitrary subjects and labeled blocks.

- Unified addMessages: when a Memory instance has a `subjectId`, you can call `addMessages(messages, skipVectorStorage?)` without passing a userId.

- `initializeSubject(subjectId: string, reset?: boolean): Promise<string>`
- `listBlocks(subjectId?: string): Promise<any[]>`
- `initializeMemory(label: string, description: string, value?: string, charLimit?: number, reset?: boolean, subjectId?: string): Promise<string>`
- `getMemory(label: string, promptFormatted?: boolean, subjectId?: string): Promise<string | null>`
- `deleteBlock(label: string, subjectId?: string): Promise<void>`
- `addMessagesToSubject(subjectId: string, messages: any[], skipVectorStorage?: boolean): Promise<string>`
- `addMessagesHere(messages: any[], skipVectorStorage?: boolean): Promise<string>`

#### `initializeUserMemory(userId: string, options?: InitOptions): Promise<string>`

Initialize memory for a new user by creating a Letta agent with default blocks (human, summary).

```typescript
interface InitOptions {
  userContextBlockPrompt?: string;      // Default: "Details about the human user you are speaking to."
  userContextBlockCharLimit?: number;   // Default: 10000
  userContextBlockValue?: string;       // Default: ""
  summaryBlockPrompt?: string;         // Default: "A short (1-2 sentences) running summary of the conversation."
  summaryBlockCharLimit?: number;      // Default: 1000
  reset?: boolean;                     // Default: false - whether to reset existing memory
}
```

**Returns:** Letta agent ID for the user's memory

**Example:**
```typescript
const agentId = await client.initializeUserMemory('user_123', {
  userContextBlockValue: 'User is a software engineer who likes TypeScript',
  reset: true
});
```

#### `addMessages(userId: string, messages: Message[], skipVectorStorage?: boolean): Promise<string>`
#### `addMessages(messages: Message[], skipVectorStorage?: boolean): Promise<string>`

Send messages to a Letta agent to update memory blocks. Works either with a specific user (legacy) or instance-bound subject (unified).

```typescript
interface Message {
  role: string;          // 'user' or 'assistant'
  content: string;       // Message content
  name?: string;         // Optional name
  metadata?: Record<string, any>; // Optional metadata
}
```

**Parameters:**
- Legacy form: `userId`, `messages`, `skipVectorStorage`
- Unified form (requires `contextId` in Memory constructor): `messages`, `skipVectorStorage`

**Returns:** Run ID for the processing task

**Examples:**
```typescript
const runId = await client.addMessages('user_123', [
  {
    role: 'user',
    content: 'I love programming in TypeScript'
  },
  {
    role: 'assistant', 
    content: 'TypeScript is a great language! What do you like most about it?'
  }
], false); // Don't skip vector storage for searchability

// Unified form with a bound context
const bound = new Memory({ subjectId: 'user_sarah' });
const runId2 = await bound.addMessages([
  { role: 'user', content: 'I love cats' }
]);
```

#### `getUserMemory(userId: string, promptFormatted?: boolean): Promise<string | null>`

Retrieve a user's memory block (human block from core memory).

**Parameters:**
- `userId`: User identifier
- `promptFormatted`: Whether to return memory in XML format for prompts (default: false)

**Returns:** User memory block value or null if user doesn't exist

**Example:**
```typescript
// Get raw memory
const memory = await client.getUserMemory('user_123');

// Get formatted memory for use in prompts
const formattedMemory = await client.getUserMemory('user_123', true);
// Returns: <human description="Details about the human user...">User details here</human>
```

#### `getSummary(userId: string, promptFormatted?: boolean): Promise<string | null>`

Retrieve a user's conversation summary.

**Parameters:**
- `userId`: User identifier
- `promptFormatted`: Whether to return summary in XML format (default: false)

**Returns:** Summary string or null if user doesn't exist

**Example:**
```typescript
// Get raw summary
const summary = await client.getSummary('user_123');

// Get formatted summary  
const formattedSummary = await client.getSummary('user_123', true);
// Returns: <conversation_summary>User discussed TypeScript programming...</conversation_summary>
```

#### `search(userId: string, query: string, tags?: string[]): Promise<string[]>`

Search a user's archival memory (passages) with semantic search.

**Parameters:**
- `userId`: User identifier
- `query`: Search query
- `tags`: Optional tag filter (defaults to `['ai-memory-sdk', 'user']`)

**Returns:** Array of matching passage contents from archival memory

**Example:**
```typescript
const results = await client.search('user_123', 'programming');
const assistantOnly = await client.search('user_123', 'explain', ['assistant']);
console.log('Found messages:', results);
```

#### `getMemoryAgentId(userId: string): Promise<string | null>`

Get the Letta agent ID associated with a user.

**Parameters:**
- `userId`: User identifier

**Returns:** Agent ID or null if user doesn't exist

#### `waitForRun(runId: string): Promise<void>`

Wait for a background processing run to complete.

**Parameters:**
- `runId`: Run ID returned from `addMessages`

#### `deleteUser(userId: string): Promise<void>`

Delete a user and all associated data.

**Parameters:**
- `userId`: User identifier

**Example:**
```typescript
await client.deleteUser('user_123');
console.log('User deleted');
```

#### `addFiles(files: any[]): Promise<never>`

Add files to memory. Currently not implemented.

**Throws:** "Not implemented" error

## Usage Examples

### Basic Conversation Memory

```typescript
import { Memory } from './src/memory';

const client = new Memory();
const userId = 'user_123';

// Initialize user
await client.initializeUserMemory(userId);

// Simulate a conversation
const messages = [
  { role: 'user', content: 'Hi, I\'m working on a React project' },
  { role: 'assistant', content: 'That\'s great! React is a popular framework. What are you building?' },
  { role: 'user', content: 'A todo app with TypeScript' },
  { role: 'assistant', content: 'Excellent choice! TypeScript adds great type safety to React projects.' }
];

// Add messages with vector storage for searchability
const runId = await client.addMessages(userId, messages, false);
await client.waitForRun(runId);

// Check what the system learned about the user
const memory = await client.getUserMemory(userId);
console.log('User context:', memory);

// Search for specific topics
const reactResults = await client.search(userId, 'React');
const typescriptResults = await client.search(userId, 'TypeScript');

console.log('React mentions:', reactResults);
console.log('TypeScript mentions:', typescriptResults);
```

### Chat Example

Run the interactive chat example:

```bash
npm run build
node dist/examples/chat.js
```

### Subject Examples

```bash
npm run build
node dist/examples/subject.js
```

### Managing Multiple Users

```typescript
const client = new Memory();
const users = ['alice', 'bob', 'charlie'];

// Initialize memory for multiple users
for (const userId of users) {
  await client.initializeUserMemory(userId, {
    userContextBlockValue: `User ${userId} preferences and context`
  });
}

// Add different messages for each user
await client.addMessages('alice', [
  { role: 'user', content: 'I prefer Python for data science' }
]);

await client.addMessages('bob', [  
  { role: 'user', content: 'I love JavaScript and web development' }
]);

await client.addMessages('charlie', [
  { role: 'user', content: 'I work with Go for backend services' }
]);

// Retrieve each user's memory
for (const userId of users) {
  const memory = await client.getUserMemory(userId);
  console.log(`${userId}'s memory:`, memory);
}
```

## Development

### Running Tests

The SDK includes comprehensive tests that match the Python SDK functionality:

```bash
# Run all tests (includes build + traditional tests + Jest messages test)
npm test

# Run all test suites separately
npm run test:all

# Run Jest tests specifically  
npm run test:jest

# Run the messages test suite (equivalent to Python test_messages.py)
npm run test:messages

# Run specific test suites
npm run test:memory
npm run test:formatter
npm run test:subject

# Watch mode for development
npm run test:watch
```

### Watch Mode

```bash
npm run dev
```

### Clean Build

```bash
npm run clean
npm run build
```

## Schemas

### MessageCreate
```typescript
interface MessageCreate {
  content: string;
  role: string;
  name?: string;
  metadata?: Record<string, any>;
}
```

### Message
```typescript
interface Message {
  id: number;
  agent_id: string;
  content: string;
  processed: boolean;
  role?: string;
  name?: string;
  registered_at?: Date;
  processed_at?: Date;
  metadata?: Record<string, any>;
}
```

### File
```typescript
interface File {
  id: number;
  agent_id: string;
  file_path: string;
  file_hash: string;
  size: number;
  last_modified: Date;
  processed: boolean;
  label: string;
  description: string;
  registered_at?: Date;
  processed_at?: Date;
}
```

## Environment Variables

Set up your environment:

```bash
# For Letta Cloud
export LETTA_API_KEY="your-api-key-here"

# For local development
# No API key needed, just connect to local server at http://localhost:8283
```

## Error Handling

The SDK throws errors for:
- Invalid API keys or connection issues
- Attempting to reinitialize existing users without `reset: true`
- Network timeouts or server errors
- Calling unimplemented methods like `addFiles`

Always wrap SDK calls in try-catch blocks for production use:

```typescript
try {
  const runId = await client.addMessages(userId, messages);
  await client.waitForRun(runId);
  const memory = await client.getUserMemory(userId);
} catch (error) {
  console.error('Memory operation failed:', error.message);
  // Handle error appropriately
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

MIT License - see LICENSE file for details.
