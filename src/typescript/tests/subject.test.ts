import { Memory } from '../src/memory';

type Agent = { id: string; name: string; tags: string[] };
type Block = { id: string; label: string; description: string; limit: number; value: string };

function createFakeLetta() {
  let agentCounter = 1;
  let blockCounter = 1;
  let runCounter = 1;

  const agents: Record<string, Agent> = {};
  const agentBlocks: Record<string, string[]> = {};
  const blocks: Record<string, Block> = {};

  function listAgentsByTags(tags: string[]) {
    const hasAll = (arr: string[], req: string[]) => req.every(t => arr.includes(t));
    return Object.values(agents).filter(a => hasAll(a.tags, tags));
  }

  const fake = {
    agents: {
      create: async ({ name, tags }: { name: string; tags: string[]; model?: string; agentType?: string; initialMessageSequence?: any[] }) => {
        const id = `agent-${agentCounter++}`;
        agents[id] = { id, name, tags };
        agentBlocks[id] = [];
        return { id };
      },
      list: async ({ tags, matchAllTags }: { tags?: string[]; matchAllTags?: boolean }) => {
        if (!tags || tags.length === 0) return Object.values(agents);
        return listAgentsByTags(tags);
      },
      delete: async (agentId: string) => {
        delete agents[agentId];
        delete agentBlocks[agentId];
      },
      blocks: {
        attach: async (agentId: string, blockId: string) => {
          agentBlocks[agentId] = agentBlocks[agentId] || [];
          if (!agentBlocks[agentId].includes(blockId)) agentBlocks[agentId].push(blockId);
        },
        list: async (agentId: string) => {
          const ids = agentBlocks[agentId] || [];
          return ids.map(id => blocks[id]);
        },
        detach: async (agentId: string, blockId: string) => {
          agentBlocks[agentId] = (agentBlocks[agentId] || []).filter(id => id !== blockId);
        },
        retrieve: async (agentId: string, label: string) => {
          const ids = agentBlocks[agentId] || [];
          const found = ids.map(id => blocks[id]).find(b => b.label === label);
          if (!found) throw new Error('Block not found');
          return found;
        },
      },
      messages: {
        createAsync: async (_agentId: string, _payload: any) => ({ id: `run-${runCounter++}` }),
      },
      passages: {
        create: async (_agentId: string, _payload: any) => ({}),
        search: async (_agentId: string, _payload: any) => ({
          results: [
            { content: 'archival passage 1' },
            { content: 'archival passage 2' },
            { content: 'archival passage 3' },
          ],
        }),
      },
    },
    blocks: {
      create: async ({ label, description, limit, value }: { label: string; description: string; limit: number; value: string }) => {
        const id = `block-${blockCounter++}`;
        const block = { id, label, description, limit, value } as Block;
        blocks[id] = block;
        return block;
      },
      delete: async (blockId: string) => {
        delete blocks[blockId];
      },
    },
    runs: {
      retrieve: async (_runId: string) => ({ status: 'completed' }),
    },
  };

  return fake;
}

async function testInstanceScopedContext() {
  console.log('Testing instance-scoped subject...');

  const memory = new Memory({ subjectId: 'user_sarah' });
  // Inject fake client
  (memory as any).lettaClient = createFakeLetta();

  await memory.initializeMemory('preferences', 'Known user preferences.', 'Likes cats', 10000, true);
  // Use unified addMessages with bound subject
  const run = await memory.addMessages([{ role: 'user', content: 'I love cats' }]);
  await memory.waitForRun(run);

  const raw = await memory.getMemory('preferences');
  if (raw !== 'Likes cats') throw new Error(`Expected 'Likes cats', got ${raw}`);

  const formatted = await memory.getMemory('preferences', true);
  if (!formatted || !formatted.includes('<preferences') || !formatted.includes('Likes cats')) {
    throw new Error(`Unexpected formatted block: ${formatted}`);
  }

  const blocks = await memory.listBlocks();
  if (!Array.isArray(blocks) || blocks.length !== 1 || (blocks[0] as any).label !== 'preferences') {
    throw new Error(`Expected one block 'preferences', got ${JSON.stringify(blocks)}`);
  }

  await memory.deleteBlock('preferences');
  const afterDelete = await memory.getMemory('preferences');
  if (afterDelete !== null) throw new Error(`Expected null after delete, got ${afterDelete}`);

  console.log('✓ Instance-scoped subject passed');
}

async function testExplicitContext() {
  console.log('Testing explicit subject...');

  const memory = new Memory();
  (memory as any).lettaClient = createFakeLetta();

  await memory.initializeSubject('project_alpha', true);
  await memory.initializeMemory('spec', 'Project spec', 'v1', 10000, false, 'project:alpha');
  const run = await memory.addMessagesToSubject('project_alpha', [{ role: 'user', content: 'Kickoff complete' }]);
  await memory.waitForRun(run);

  const spec = await memory.getMemory('spec', false, 'project:alpha');
  if (spec !== 'v1') throw new Error(`Expected 'v1', got ${spec}`);

  console.log('✓ Explicit subject passed');
}

async function testSleepBasic() {
  console.log('Testing sleep() with blocks...');

  const memory = new Memory({ subjectId: 'user_sleep' });
  (memory as any).lettaClient = createFakeLetta();

  await memory.initializeMemory('human', 'User info', 'Name: Alice', 10000, true);
  await memory.initializeMemory('summary', 'Summary', 'First chat', 10000, true);

  const runId = await memory.sleep();
  if (!runId || !runId.startsWith('run-')) {
    throw new Error(`Expected run ID, got ${runId}`);
  }
  await memory.waitForRun(runId);

  console.log('✓ sleep() with blocks passed');
}

async function testSleepNoBlocks() {
  console.log('Testing sleep() with no blocks...');

  const memory = new Memory({ subjectId: 'user_sleep_empty' });
  (memory as any).lettaClient = createFakeLetta();

  // Ensure subject exists but has no blocks
  await memory.initializeSubject('user_sleep_empty', true);

  const runId = await memory.sleep();
  if (runId !== null) {
    throw new Error(`Expected null for empty blocks, got ${runId}`);
  }

  console.log('✓ sleep() with no blocks returns null');
}

async function testSleepWithArchival() {
  console.log('Testing sleep() with archival...');

  const memory = new Memory({ subjectId: 'user_sleep_arch' });
  (memory as any).lettaClient = createFakeLetta();

  await memory.initializeMemory('notes', 'Notes', 'Some notes', 10000, true);

  const runId = await memory.sleep({ includeArchival: true, archivalLimit: 2 });
  if (!runId || !runId.startsWith('run-')) {
    throw new Error(`Expected run ID, got ${runId}`);
  }

  console.log('✓ sleep() with archival passed');
}

async function testSleepExplicitSubject() {
  console.log('Testing sleep() with explicit subject...');

  const memory = new Memory();
  (memory as any).lettaClient = createFakeLetta();

  await memory.initializeSubject('project_sleep', true);
  await memory.initializeMemory('spec', 'Spec', 'v1', 10000, false, 'project_sleep');

  const runId = await memory.sleep({ subjectId: 'project_sleep' });
  if (!runId || !runId.startsWith('run-')) {
    throw new Error(`Expected run ID, got ${runId}`);
  }

  console.log('✓ sleep() with explicit subject passed');
}

async function testSleepNoSubjectThrows() {
  console.log('Testing sleep() without subject throws...');

  const memory = new Memory();
  (memory as any).lettaClient = createFakeLetta();

  let threw = false;
  try {
    await memory.sleep();
  } catch (e) {
    if (e instanceof Error && e.message.includes('No subjectId provided')) {
      threw = true;
    } else {
      throw e;
    }
  }
  if (!threw) throw new Error('Expected error for missing subjectId');

  console.log('✓ sleep() without subject throws');
}

async function runAllTests() {
  try {
    await testInstanceScopedContext();
    await testExplicitContext();
    await testSleepBasic();
    await testSleepNoBlocks();
    await testSleepWithArchival();
    await testSleepExplicitSubject();
    await testSleepNoSubjectThrows();
    console.log('✅ All context + sleep tests passed');
  } catch (err) {
    console.error('❌ Test failed:', err instanceof Error ? err.message : String(err));
    process.exit(1);
  }
}

if (require.main === module) {
  runAllTests();
}
