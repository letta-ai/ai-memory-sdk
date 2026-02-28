import { formatMessages, formatFiles, formatSleepPrompt } from '../src/prompt-formatter';
import { MessageCreate, File } from '../src/schemas';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

function testFormatMessages() {
  console.log('Testing formatMessages...');

  const messages: MessageCreate[] = [
    {
      role: 'user',
      content: 'hi my name is sarah'
    },
    {
      role: 'assistant',
      content: 'Hello Sarah! I\'m Sam. *smiles warmly* There\'s something special about first meetings, don\'t you think?'
    },
    {
      role: 'assistant',
      content: 'Tool call returned Sent message successfully.'
    }
  ];

  const formatted = formatMessages(messages);
  
  if (formatted.length !== 1) {
    throw new Error(`Expected 1 formatted message, got ${formatted.length}`);
  }

  if (formatted[0].role !== 'user') {
    throw new Error(`Expected role 'user', got '${formatted[0].role}'`);
  }

  const content = formatted[0].content;
  const expectedParts = [
    '<messages>',
    'The following message interactions have occured',
    'user: hi my name is sarah',
    'assistant: Hello Sarah!',
    'assistant: Tool call returned',
    '</messages>'
  ];

  for (const part of expectedParts) {
    if (!content.includes(part)) {
      throw new Error(`Expected content to contain '${part}', got: ${content}`);
    }
  }

  console.log('✓ formatMessages works correctly');
}

function testFormatMessagesEmpty() {
  console.log('Testing formatMessages with empty array...');

  const messages: MessageCreate[] = [];
  const formatted = formatMessages(messages);
  
  if (formatted.length !== 1) {
    throw new Error(`Expected 1 formatted message, got ${formatted.length}`);
  }

  const content = formatted[0].content;
  if (!content.includes('<messages>') || !content.includes('</messages>')) {
    throw new Error(`Expected content to contain messages tags, got: ${content}`);
  }

  console.log('✓ formatMessages handles empty array correctly');
}

function testFormatMessagesWithMetadata() {
  console.log('Testing formatMessages with metadata...');

  const messages: MessageCreate[] = [
    {
      role: 'user',
      content: 'Hello',
      name: 'testUser',
      metadata: { timestamp: '2023-01-01' }
    }
  ];

  const formatted = formatMessages(messages);
  const content = formatted[0].content;
  
  if (!content.includes('user: Hello')) {
    throw new Error(`Expected content to contain 'user: Hello', got: ${content}`);
  }

  console.log('✓ formatMessages handles metadata correctly');
}

function testFormatFilesSmall() {
  console.log('Testing formatFiles with small file...');

  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'test-'));
  const testFile = path.join(tempDir, 'test.txt');
  const fileContent = 'This is a test file content.';

  try {
    fs.writeFileSync(testFile, fileContent);

    const files: File[] = [
      {
        id: 1,
        agent_id: 'test-agent',
        file_path: testFile,
        file_hash: 'test-hash',
        size: fileContent.length,
        last_modified: new Date(),
        processed: false,
        label: 'test-file',
        description: 'A test file'
      }
    ];

    const formatted = formatFiles(files);
    
    if (formatted.length !== 1) {
      throw new Error(`Expected 1 formatted file, got ${formatted.length}`);
    }

    if (formatted[0].role !== 'user') {
      throw new Error(`Expected role 'user', got '${formatted[0].role}'`);
    }

    const content = formatted[0].content;
    const expectedParts = [
      '<file label="test-file" description="A test file">',
      '<file_part part=1/1>',
      fileContent,
      '</file_part>',
      '</file>'
    ];

    for (const part of expectedParts) {
      if (!content.includes(part)) {
        throw new Error(`Expected content to contain '${part}', got: ${content}`);
      }
    }

    console.log('✓ formatFiles handles small files correctly');

  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
}

function testFormatFilesLarge() {
  console.log('Testing formatFiles with large file...');

  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'test-'));
  const testFile = path.join(tempDir, 'test.txt');
  // Create a file larger than FILE_CHAR_LIMIT (20000)
  const largeContent = 'a'.repeat(25000);

  try {
    fs.writeFileSync(testFile, largeContent);

    const files: File[] = [
      {
        id: 1,
        agent_id: 'test-agent',
        file_path: testFile,
        file_hash: 'test-hash',
        size: largeContent.length,
        last_modified: new Date(),
        processed: false,
        label: 'large-file',
        description: 'A large test file'
      }
    ];

    const formatted = formatFiles(files);
    
    if (formatted.length <= 1) {
      throw new Error(`Expected multiple formatted messages for large file, got ${formatted.length}`);
    }

    if (!formatted[0].content.includes('part=1/2')) {
      throw new Error(`Expected first part to contain 'part=1/2', got: ${formatted[0].content}`);
    }

    if (!formatted[1].content.includes('part=2/2')) {
      throw new Error(`Expected second part to contain 'part=2/2', got: ${formatted[1].content}`);
    }

    console.log('✓ formatFiles chunks large files correctly');

  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
}

function testFormatFilesError() {
  console.log('Testing formatFiles with non-existent file...');

  const files: File[] = [
    {
      id: 1,
      agent_id: 'test-agent',
      file_path: '/non/existent/file.txt',
      file_hash: 'test-hash',
      size: 0,
      last_modified: new Date(),
      processed: false,
      label: 'missing-file',
      description: 'A missing file'
    }
  ];

  const formatted = formatFiles(files);
  
  if (formatted.length !== 1) {
    throw new Error(`Expected 1 formatted message for error case, got ${formatted.length}`);
  }

  const content = formatted[0].content;
  if (!content.includes('[Error reading file:') || !content.includes('missing-file')) {
    throw new Error(`Expected error message and file label, got: ${content}`);
  }

  console.log('✓ formatFiles handles file errors gracefully');
}

function testFormatFilesMultiple() {
  console.log('Testing formatFiles with multiple files...');

  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'test-'));
  const file1Content = 'Content of file 1';
  const file2Content = 'Content of file 2';
  const testFile1 = path.join(tempDir, 'test1.txt');
  const testFile2 = path.join(tempDir, 'test2.txt');

  try {
    fs.writeFileSync(testFile1, file1Content);
    fs.writeFileSync(testFile2, file2Content);

    const files: File[] = [
      {
        id: 1,
        agent_id: 'test-agent',
        file_path: testFile1,
        file_hash: 'test-hash-1',
        size: file1Content.length,
        last_modified: new Date(),
        processed: false,
        label: 'file1',
        description: 'First test file'
      },
      {
        id: 2,
        agent_id: 'test-agent',
        file_path: testFile2,
        file_hash: 'test-hash-2',
        size: file2Content.length,
        last_modified: new Date(),
        processed: false,
        label: 'file2',
        description: 'Second test file'
      }
    ];

    const formatted = formatFiles(files);
    
    if (formatted.length !== 2) {
      throw new Error(`Expected 2 formatted messages, got ${formatted.length}`);
    }

    if (!formatted[0].content.includes('file1') || !formatted[0].content.includes(file1Content)) {
      throw new Error(`First formatted message missing file1 content: ${formatted[0].content}`);
    }

    if (!formatted[1].content.includes('file2') || !formatted[1].content.includes(file2Content)) {
      throw new Error(`Second formatted message missing file2 content: ${formatted[1].content}`);
    }

    console.log('✓ formatFiles handles multiple files correctly');

  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
}

function testFormatSleepPromptBasic() {
  console.log('Testing formatSleepPrompt with blocks...');

  const blocks = [
    { label: 'human', description: 'User info', value: 'Name: Alice' },
    { label: 'summary', description: 'Conversation summary', value: 'Discussed cats' },
  ];

  const result = formatSleepPrompt(blocks);

  if (result.length !== 1) {
    throw new Error(`Expected 1 message, got ${result.length}`);
  }
  if (result[0].role !== 'user') {
    throw new Error(`Expected role 'user', got '${result[0].role}'`);
  }

  const content = result[0].content;
  const expected = [
    '<sleep_consolidation>',
    'sleep/consolidation phase',
    '<block label="human" description="User info">',
    'Name: Alice',
    '<block label="summary" description="Conversation summary">',
    'Discussed cats',
    '</sleep_consolidation>',
  ];
  for (const part of expected) {
    if (!content.includes(part)) {
      throw new Error(`Expected content to contain '${part}'`);
    }
  }

  console.log('✓ formatSleepPrompt basic works correctly');
}

function testFormatSleepPromptWithArchival() {
  console.log('Testing formatSleepPrompt with archival passages...');

  const blocks = [
    { label: 'human', description: 'User info', value: 'Name: Bob' },
  ];
  const archival = ['User mentioned liking jazz', 'User works at Acme Corp'];

  const result = formatSleepPrompt(blocks, archival);
  const content = result[0].content;

  if (!content.includes('archival (long-term) memory')) {
    throw new Error('Expected archival section header');
  }
  if (!content.includes('- User mentioned liking jazz')) {
    throw new Error('Expected first archival passage');
  }
  if (!content.includes('- User works at Acme Corp')) {
    throw new Error('Expected second archival passage');
  }

  console.log('✓ formatSleepPrompt with archival works correctly');
}

function testFormatSleepPromptNoArchival() {
  console.log('Testing formatSleepPrompt without archival...');

  const blocks = [
    { label: 'notes', description: 'Notes', value: 'Some notes' },
  ];

  const result = formatSleepPrompt(blocks, null);
  const content = result[0].content;

  if (content.includes('archival (long-term) memory')) {
    throw new Error('Should not contain archival section when null');
  }

  const result2 = formatSleepPrompt(blocks, []);
  if (result2[0].content.includes('archival (long-term) memory')) {
    throw new Error('Should not contain archival section when empty array');
  }

  console.log('✓ formatSleepPrompt without archival works correctly');
}

function testFormatSleepPromptSkipsLabelless() {
  console.log('Testing formatSleepPrompt skips blocks without labels...');

  const blocks = [
    { label: 'human', description: 'Info', value: 'Alice' },
    { description: 'No label', value: 'Should be skipped' },
    { label: '', description: 'Empty label', value: 'Also skipped' },
  ];

  const result = formatSleepPrompt(blocks);
  const content = result[0].content;

  if (!content.includes('Alice')) {
    throw new Error('Expected labeled block content');
  }
  if (content.includes('Should be skipped')) {
    throw new Error('Block without label should be skipped');
  }

  console.log('✓ formatSleepPrompt skips labelless blocks');
}

function runAllTests() {
  console.log('Running Prompt Formatter tests...\n');

  try {
    testFormatMessages();
    console.log();
    
    testFormatMessagesEmpty();
    console.log();
    
    testFormatMessagesWithMetadata();
    console.log();
    
    testFormatFilesSmall();
    console.log();
    
    testFormatFilesLarge();
    console.log();
    
    testFormatFilesError();
    console.log();
    
    testFormatFilesMultiple();
    console.log();

    testFormatSleepPromptBasic();
    console.log();

    testFormatSleepPromptWithArchival();
    console.log();

    testFormatSleepPromptNoArchival();
    console.log();

    testFormatSleepPromptSkipsLabelless();
    console.log();

    console.log('✅ All Prompt Formatter tests passed!');
  } catch (error) {
    console.error('❌ Test failed:', error instanceof Error ? error.message : String(error));
    process.exit(1);
  }
}

if (require.main === module) {
  runAllTests();
}