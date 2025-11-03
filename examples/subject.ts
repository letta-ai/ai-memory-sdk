import { Memory } from '@letta-ai/memory-sdk';

async function instanceScopedExample() {
  console.log('== Instance-scoped subject example ==');
  const memory = new Memory({ subjectId: 'user_sarah' });

  await memory.initializeMemory('preferences', 'Known user preferences.', 'Likes cats', 10000, true);

  const run = await memory.addMessages([
    { role: 'user', content: 'I love cats' },
  ]);
  await memory.waitForRun(run);

  const raw = await memory.getMemory('preferences');
  console.log('Raw:', raw);

  const formatted = await memory.getMemory('preferences', true);
  console.log('Formatted:', formatted);

  const blocks = await memory.listBlocks();
  console.log('Blocks:', blocks.map((b: any) => b.label));

  await memory.deleteBlock('preferences');
  console.log("Deleted 'preferences'");
}

async function explicitContextExample() {
  console.log('== Explicit subject example ==');
  const memory = new Memory();

  await memory.initializeSubject('project_alpha', true);
  await memory.initializeMemory('spec', 'Project spec', 'v1', 10000, false, 'project_alpha');

  const run = await memory.addMessagesToSubject('project_alpha', [
    { role: 'user', content: 'Kickoff complete' },
  ]);
  await memory.waitForRun(run);

  const spec = await memory.getMemory('spec', false, 'project_alpha');
  console.log('Spec:', spec);
}

async function main() {
  await instanceScopedExample();
  await explicitContextExample();
}

if (require.main === module) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
