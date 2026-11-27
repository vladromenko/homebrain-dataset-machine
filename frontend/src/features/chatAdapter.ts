import { type ChatModelAdapter, type ChatModelRunOptions, type ChatModelRunResult } from '@assistant-ui/react';
import { lab } from '@/lib/api';
import { speak } from '@/lib/speech';

async function* events(response: Response) {
  if (!response.ok || !response.body) throw new Error('Assistant connection unavailable');
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '', finished = false;
  while (!finished) {
    const chunk = await reader.read(); finished = chunk.done;
    buffer += decoder.decode(chunk.value, { stream: !finished });
    const lines = buffer.split('\n'); buffer = lines.pop() || '';
    for (const line of lines.filter(Boolean)) yield JSON.parse(line);
  }
  if (buffer.trim()) yield JSON.parse(buffer);
}

export function chatAdapter(context: any, voice: any, setSources: (sources: any[]) => void): ChatModelAdapter {
  return { async *run({ messages, abortSignal }: ChatModelRunOptions): AsyncGenerator<ChatModelRunResult, void> {
    const parts = messages[messages.length - 1].content as ReadonlyArray<{type: string; text?: string}>;
    const text = parts.filter(part => part.type === 'text').map(part => part.text || '').join(' ');
    const response = await fetch(`${lab}/chat`, {
      method: 'POST', credentials: 'same-origin', signal: abortSignal,
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text, conversation: 'operator', selection: context.current?.session_id || null}),
    });
    let answer = '';
    setSources([]);
    for await (const event of events(response)) {
      if (event.type === 'answer') answer += event.text;
      if (event.type === 'sources') setSources(event.sources);
      if (event.type === 'tool') yield {content: [{type: 'text', text: answer || `Checking evidence · ${event.tool}…`}]};
      if (answer) yield {content: [{type: 'text', text: answer}]};
    }
    if (voice.current && answer) await speak(answer);
  }};
}
