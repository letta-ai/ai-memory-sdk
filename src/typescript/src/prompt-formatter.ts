import * as fs from 'fs';
import { Message, File, MessageCreate } from './schemas';

const MESSAGES_PROMPT = "The following message interactions have occured";
const MESSAGES_TAG = "messages";
const MESSAGE_TOTAL_CHAR_LIMIT = 5000;

const FILE_TAG = "file";
const FILE_PART_TAG = "file_part";
const FILE_CHAR_LIMIT = 20000;

const SLEEP_TAG = "sleep_consolidation";

export function formatMessages(messages: MessageCreate[]): Array<{ role: string; content: string }> {
  const messageHistory = messages
    .map(msg => `${msg.role}: ${msg.content}`)
    .join('\n');

  return [{
    role: "user",
    content: `<${MESSAGES_TAG}>${MESSAGES_PROMPT}:\n${messageHistory}</${MESSAGES_TAG}>`
  }];
}

export function formatSleepPrompt(
  blocks: any[],
  archivalPassages?: string[] | null,
): Array<{ role: string; content: string }> {
  const blockLines = blocks
    .filter((b: any) => b.label)
    .map((b: any) => {
      const label = b.label;
      const description = b.description || '';
      const value = b.value || '';
      return `<block label="${label}" description="${description}">\n${value}\n</block>`;
    });
  const blocksSection = blockLines.join('\n\n');

  let archivalSection = '';
  if (archivalPassages && archivalPassages.length > 0) {
    const passagesText = archivalPassages.map(p => `- ${p}`).join('\n');
    archivalSection =
      `\n\nThe following are recent passages from archival (long-term) memory. ` +
      `Consider whether any of this information should be promoted into your ` +
      `active memory blocks, or whether it reveals patterns worth capturing:\n` +
      passagesText;
  }

  const prompt =
    `<${SLEEP_TAG}>\n` +
    `You are entering a sleep/consolidation phase. No new external information ` +
    `is being provided. Instead, review your current memory state and improve it.\n\n` +
    `Your tasks:\n` +
    `1. Identify and resolve any contradictions between memory blocks\n` +
    `2. Merge redundant information that appears across multiple blocks\n` +
    `3. Remove or condense stale or outdated information\n` +
    `4. Strengthen connections between related facts across blocks\n` +
    `5. Reorganize information within blocks for clarity and coherence\n` +
    `6. Note any gaps in your knowledge that future conversations should address\n\n` +
    `Current memory blocks:\n${blocksSection}` +
    `${archivalSection}\n\n` +
    `Update your memory blocks to reflect a consolidated, coherent understanding. ` +
    `Do not fabricate new information — only reorganize and refine what you already know.\n` +
    `</${SLEEP_TAG}>`;

  return [{ role: 'user', content: prompt }];
}

export function formatFiles(files: File[]): Array<{ role: string; content: string }> {
  const allMessages: Array<{ role: string; content: string }> = [];

  for (const file of files) {
    try {
      const fileContent = fs.readFileSync(file.file_path, 'utf-8');
      
      const fileContentChunks = [];
      for (let i = 0; i < fileContent.length; i += FILE_CHAR_LIMIT) {
        fileContentChunks.push(fileContent.slice(i, i + FILE_CHAR_LIMIT));
      }

      console.log(`Formatted file ${file.label} into ${fileContentChunks.length} separate messages`);

      for (let i = 0; i < fileContentChunks.length; i++) {
        const chunk = fileContentChunks[i];
        const partNumber = i + 1;
        const totalParts = fileContentChunks.length;

        const filePartContent = `<${FILE_PART_TAG} part=${partNumber}/${totalParts}>${chunk}</${FILE_PART_TAG}>`;
        const fileMessage = `<${FILE_TAG} label="${file.label}" description="${file.description}">${filePartContent}</${FILE_TAG}>`;

        allMessages.push({ role: "user", content: fileMessage });
      }
    } catch (error) {
      const errorMsg = `<${FILE_TAG} label="${file.label}" description="${file.description}">[Error reading file: ${error}]</${FILE_TAG}>`;
      allMessages.push({ role: "user", content: errorMsg });
    }
  }

  return allMessages;
}