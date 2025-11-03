import { LettaClient } from '@letta-ai/letta-client';
import { formatMessages } from './prompt-formatter';
import { MessageCreate } from './schemas';

export interface MemoryConfig {
  lettaApiKey?: string;
  subjectId?: string; // Optional default subject for instance-scoped operations
}

export class Memory {
  private lettaClient: LettaClient;
  private subjectId?: string;

  constructor(config: MemoryConfig = {}) {
    const apiKey = config.lettaApiKey || process.env.LETTA_API_KEY;
    this.lettaClient = new LettaClient({ token: apiKey });
    this.subjectId = config.subjectId;
  }

  private async createSleeptimeAgent(name: string, tags: string[]): Promise<string> {
    const withDefault = Array.from(new Set([...(tags || []), 'ai-memory-sdk']));
    const agentState = await this.lettaClient.agents.create({
      name,
      model: 'openai/gpt-4',
      agentType: 'sleeptime_agent',
      initialMessageSequence: [],
      tags: withDefault,
    });
    return agentState.id;
  }

  private async getMatchingAgent(tags: string[]) {
    const agents = await this.lettaClient.agents.list({
      tags,
      matchAllTags: true,
    });
    return agents.length > 0 ? agents[0] : null;
  }

  private async findAgentByTag(tag: string) {
    const agents = await this.lettaClient.agents.list({ tags: [tag], matchAllTags: true });
    return agents.length > 0 ? agents[0] : null;
  }

  private subjectTags(subjectId: string): string[] {
    // Include namespaced, raw, and default SDK tag for compatibility and discoverability
    return [`subj:${subjectId}`, subjectId, 'ai-memory-sdk'];
  }

  private async getAgentForSubject(subjectId: string) {
    // Prefer namespaced tag, fallback to legacy raw tag
    return (await this.findAgentByTag(`subj:${subjectId}`)) || (await this.findAgentByTag(subjectId));
  }

  private async createContextBlock(
    agentId: string,
    label: string,
    description: string,
    charLimit: number = 10000,
    value: string = ''
  ): Promise<string> {
    const block = await this.lettaClient.blocks.create({
      label,
      description,
      limit: charLimit,
      value,
    });
    
    // Attach block to agent
    await this.lettaClient.agents.blocks.attach(agentId, block.id!);
    
    return block.id!;
  }

  private async listContextBlocks(agentId: string) {
    return await this.lettaClient.agents.blocks.list(agentId);
  }

  private async deleteContextBlock(agentId: string, blockId: string): Promise<void> {
    await this.lettaClient.agents.blocks.detach(agentId, blockId);
    await this.lettaClient.blocks.delete(blockId);
  }

  private async deleteAgent(agentId: string): Promise<void> {
    await this.lettaClient.agents.delete(agentId);
  }

  private async ensureSubject(subjectId: string): Promise<string> {
    const existing = await this.getAgentForSubject(subjectId);
    if (existing) return existing.id;
    const agentState = await this.lettaClient.agents.create({
      name: `subconscious_agent_subject_${subjectId}`,
      model: 'openai/gpt-4',
      agentType: 'sleeptime_agent',
      initialMessageSequence: [],
      tags: this.subjectTags(subjectId),
    });
    await this.lettaClient.agents.passages.create(agentState.id!, { text: `Initialized memory for subject ${subjectId}`, tags: ['ai-memory-sdk'] });
    return agentState.id!;
  }

  private getEffectiveSubject(passed?: string): string {
    const sid = passed ?? this.subjectId;
    if (!sid) {
      throw new Error('No subjectId provided and instance is not bound to a subject. Pass subjectId=... or set in constructor.');
    }
    return sid;
  }

  private async getBlockByLabel(agentId: string, label: string): Promise<any | null> {
    const blocks = await this.lettaClient.agents.blocks.list(agentId);
    return blocks.find((b: any) => (b as any).label === label) ?? null;
  }

  // Users must follow naming conventions for agents/blocks/tags; no sanitization is applied here.

  private async learnMessages(agentId: string, messages: Record<string, any>[], skipVectorStorage: boolean = true): Promise<string> {
    const messageCreates = messages.map(msg => ({
      content: msg.content,
      role: msg.role,
      name: msg.name,
      metadata: msg.metadata
    } as MessageCreate));
    const formattedMessages = formatMessages(messageCreates);
    
    console.log('FORMATTED MESSAGES', formattedMessages);
    console.log('AGENT ID', agentId);
    
    const lettaRun = await this.lettaClient.agents.messages.createAsync(agentId, {
      messages: formattedMessages as any,
    });
    
    // Insert into archival in parallel if not skipping vector storage
    if (!skipVectorStorage) {
      const tasks = messages.map(message => 
        this.lettaClient.agents.passages.create(agentId, {
          text: message.content,
          tags: [message.role, 'ai-memory-sdk'],
        })
      );
      await Promise.all(tasks);
    }
    
    return lettaRun.id!;
  }

  private formatBlock(block: any): string {
    return `<${block.label} description="${block.description}">${block.value}</${block.label}>`;
  }

  private async getRunStatus(runId: string): Promise<string> {
    const run = await this.lettaClient.runs.retrieve(runId);
    if (!run) {
      throw new Error(`Run ${runId} not found`);
    }
    return run.status!;
  }

  async waitForRun(runId: string): Promise<void> {
    while (await this.getRunStatus(runId) !== 'completed') {
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }

  // ===== General Subject API =====

  async initializeSubject(subjectId: string, reset: boolean = false): Promise<string> {
    const existing = await this.getAgentForSubject(subjectId);
    if (existing) {
      if (reset) {
        await this.deleteAgent(existing.id);
      } else {
        throw new Error(`Agent ${existing.id} already exists for subject ${subjectId}. Cannot re-initialize unless reset=true.`);
      }
    }
    return await this.ensureSubject(subjectId);
  }

  async listBlocks(subjectId?: string): Promise<any[]> {
    const sid = this.getEffectiveSubject(subjectId);
    const agent = await this.getAgentForSubject(sid);
    if (!agent) return [];
    return await this.lettaClient.agents.blocks.list(agent.id);
  }

  async initializeMemory(
    label: string,
    description: string,
    value: string = '',
    charLimit: number = 10000,
    reset: boolean = false,
    subjectId?: string,
  ): Promise<string> {
    const sid = this.getEffectiveSubject(subjectId);
    const agentId = await this.ensureSubject(sid);

    let existing = await this.getBlockByLabel(agentId, label);
    if (existing && reset) {
      await this.deleteBlock(label, sid);
      existing = null;
    }
    if (existing) {
      return (existing as any).id;
    }
    return await this.createContextBlock(agentId, label, description, charLimit, value);
  }

  async getMemory(label: string, promptFormatted: boolean = false, subjectId?: string): Promise<string | null> {
    const sid = this.getEffectiveSubject(subjectId);
    const agent = await this.getAgentForSubject(sid);
    if (!agent) return null;
    const block = await this.getBlockByLabel(agent.id, label);
    if (!block) return null;
    if (promptFormatted) return this.formatBlock(block);
    return (block as any).value ?? null;
  }

  async deleteBlock(label: string, subjectId?: string): Promise<void> {
    const sid = this.getEffectiveSubject(subjectId);
    const agent = await this.getAgentForSubject(sid);
    if (!agent) return;
    const block = await this.getBlockByLabel(agent.id, label);
    if (!block) return;
    await this.lettaClient.agents.blocks.detach(agent.id, (block as any).id);
    await this.lettaClient.blocks.delete((block as any).id);
  }

  async addMessagesToSubject(subjectId: string, messages: Record<string, any>[], skipVectorStorage: boolean = true): Promise<string> {
    const agent = await this.getAgentForSubject(subjectId);
    const agentId = agent ? agent.id : await this.ensureSubject(subjectId);
    return await this.learnMessages(agentId, messages, skipVectorStorage);
  }

  async addMessagesHere(messages: Record<string, any>[], skipVectorStorage: boolean = true): Promise<string> {
    const sid = this.getEffectiveSubject();
    return await this.addMessagesToSubject(sid, messages, skipVectorStorage);
  }

  async initializeUserMemory(
    userId: string,
    options: {
      userContextBlockPrompt?: string;
      userContextBlockCharLimit?: number;
      userContextBlockValue?: string;
      summaryBlockPrompt?: string;
      summaryBlockCharLimit?: number;
      reset?: boolean;
    } = {}
  ): Promise<string> {
    const {
      userContextBlockPrompt = 'Details about the human user you are speaking to.',
      userContextBlockCharLimit = 10000,
      userContextBlockValue = '',
      summaryBlockPrompt = 'A short (1-2 sentences) running summary of the conversation.',
      summaryBlockCharLimit = 1000,
      reset = false,
    } = options;

    // Check if agent already exists
    const existingAgent = await this.getMatchingAgent([userId]);
    if (existingAgent) {
      if (reset) {
        await this.deleteAgent(existingAgent.id);
      } else {
        throw new Error(
          `Agent ${existingAgent.id} already exists for user ${userId}. Cannot re-initialize memory unless deleted.`
        );
      }
    }

    // Create the agent
    const agentId = await this.createSleeptimeAgent(
      `subconscious_agent_user_${userId}`,
      [userId]
    );

    // Create context blocks
    await this.createContextBlock(
      agentId,
      'human',
      userContextBlockPrompt,
      userContextBlockCharLimit,
      userContextBlockValue
    );
    await this.createContextBlock(
      agentId,
      'summary',
      summaryBlockPrompt,
      summaryBlockCharLimit,
      ''
    );

    // Attach a single archival memory (workaround)
    await this.lettaClient.agents.passages.create(agentId, {
      text: `Initialized memory for user ${userId}`,
      tags: ['ai-memory-sdk'],
    });

    return agentId;
  }

  async addMessages(messages: Record<string, any>[], skipVectorStorage?: boolean): Promise<string>;
  async addMessages(userId: string, messages: Record<string, any>[], skipVectorStorage?: boolean): Promise<string>;
  async addMessages(arg1: any, arg2?: any, arg3?: any): Promise<string> {
    // Overloads:
    // - addMessages(messages, skipVectorStorage?) when instance is bound to subjectId
    // - addMessages(userId, messages, skipVectorStorage?) for legacy user mode
    if (typeof arg1 === 'string') {
      const userId = arg1 as string;
      const messages = arg2 as Record<string, any>[];
      const skipVectorStorage = (typeof arg3 === 'boolean') ? arg3 : true;
      let agentId: string;
      const agent = await this.getMatchingAgent([userId]);
      if (agent) {
        agentId = agent.id;
      } else {
        agentId = await this.initializeUserMemory(userId);
      }
      return await this.learnMessages(agentId, messages, skipVectorStorage);
    }

    // Treat first arg as messages for the bound context
    const messages = arg1 as Record<string, any>[];
    const skipVectorStorage = (typeof arg2 === 'boolean') ? arg2 : true;
    const sid = this.getEffectiveSubject();
    return await this.addMessagesToSubject(sid, messages, skipVectorStorage);
  }

  async addFiles(files: Record<string, any>[]): Promise<never> {
    throw new Error('Not implemented');
  }

  async getUserMemory(userId: string, promptFormatted: boolean = false): Promise<string | null> {
    const agent = await this.getMatchingAgent([userId]);
    if (agent) {
      const block = await this.lettaClient.agents.blocks.retrieve(agent.id, 'human');
      if (promptFormatted) {
        return this.formatBlock(block);
      }
      return block.value;
    }
    return null;
  }

  async getSummary(userId: string, promptFormatted: boolean = false): Promise<string | null> {
    const agent = await this.getMatchingAgent([userId]);
    if (agent) {
      const block = await this.lettaClient.agents.blocks.retrieve(agent.id, 'summary');
      if (promptFormatted) {
        return `<conversation_summary>${block.value}</conversation_summary>`;
      }
      return block.value;
    }
    return null;
  }

  async getMemoryAgentId(userId: string): Promise<string | null> {
    const agent = await this.getMatchingAgent([userId]);
    if (agent) {
      return agent.id;
    }
    return null;
  }

  async deleteUser(userId: string): Promise<void> {
    const agent = await this.getMatchingAgent([userId]);
    if (agent) {
      // Deleting the agent also deletes associated messages/blocks
      await this.lettaClient.agents.delete(agent.id);
      console.log(`Deleted agent ${agent.id} for user ${userId}`);
    }
  }

  async search(userId: string, query: string, tags?: string[]): Promise<string[]> {
    const agent = await this.getMatchingAgent([userId]);
    if (agent) {
      const response = await this.lettaClient.agents.passages.search(agent.id, {
        query,
        tags: tags ?? ['ai-memory-sdk', 'user'],
      });
      return response.results.map(result => result.content);
    }
    return [];
  }
}
