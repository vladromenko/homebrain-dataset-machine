import { useEffect, useMemo, useRef, useState } from 'react';
import { AssistantRuntimeProvider, useLocalRuntime, ThreadPrimitive, MessagePrimitive, ComposerPrimitive } from '@assistant-ui/react';
import { Send, Volume2, X, Bot } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { enableSpeech, muteSpeech } from '@/lib/speech';
import { api, lab, type Session } from '@/lib/api';
import { chatAdapter } from './chatAdapter';
import { VoiceInput } from './VoiceInput';

export function Assistant(props: {session: Session | null; onClose: () => void}) {
  const [history, setHistory] = useState<any[] | null>(null);
  useEffect(() => { api('/api/history').then(setHistory).catch(() => setHistory([])); }, []);
  return history ? <Conversation {...props} history={history}/> : <aside className="assistant">Loading conversation…</aside>;
}

function Conversation({ session, onClose, history }: any) {
  const context = useRef(session); context.current = session;
  const voiceEnabled = useRef(false);
  const [voice, setVoice] = useState(false);
  const [sources, setSources] = useState<any[]>([]);
  const adapter = useMemo(() => chatAdapter(context, voiceEnabled, setSources), []);
  const runtime = useLocalRuntime(adapter, {initialMessages: history.map((row: any) => ({role: row.role, content: row.text}))});
  useEffect(() => {
    const mute = () => {voiceEnabled.current = false; setVoice(false);};
    window.addEventListener('homebrain-mute-speech', mute);
    return () => window.removeEventListener('homebrain-mute-speech', mute);
  }, []);
  async function toggleVoice() {
    if (!voice) { await api(`${lab}/voice`, {enabled: false}); await enableSpeech(); }
    else muteSpeech();
    voiceEnabled.current = !voice; setVoice(!voice);
  }
  return <AssistantRuntimeProvider runtime={runtime}><aside className="assistant">
    <header><span><Bot size={18}/> Lab assistant</span>
      <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close assistant"><X size={16}/></Button></header>
    <div className="assistant-context">{session ? `${session.robot_id.toUpperCase()} · ${session.state.replaceAll('_', ' ')}` : 'Select a task to share its context'}
      <small>Local model · evidence tools · English</small></div>
    <ThreadPrimitive.Root className="thread">
      <Messages/>
      <ComposerPrimitive.Root className="composer"><ComposerPrimitive.Input placeholder="Ask about this task…" rows={3}/>
        <div><VoiceInput onText={text => runtime.thread.append({role: 'user', content: [{type: 'text', text}]})}/>
          <Button variant={voice ? 'secondary' : 'ghost'} size="icon" onClick={toggleVoice} aria-label="Toggle spoken replies"><Volume2 size={16}/></Button>
          <ComposerPrimitive.Send asChild><Button size="icon" aria-label="Send message"><Send size={16}/></Button></ComposerPrimitive.Send>
        </div>
      </ComposerPrimitive.Root>
    </ThreadPrimitive.Root>
    <Sources sources={sources}/>
    <p className="assistant-footnote">Assistant suggestions never establish physical safety or scientific acceptance.</p>
  </aside></AssistantRuntimeProvider>;
}

function Messages() {
  return <ThreadPrimitive.Viewport className="thread-messages">
    <ThreadPrimitive.Empty><div className="assistant-welcome"><h3>Work with the evidence.</h3>
      <p>Ask what comes next, whether an attempt saved, or why validation rejected it.</p></div></ThreadPrimitive.Empty>
    <ThreadPrimitive.Messages components={{UserMessage, AssistantMessage}}/>
  </ThreadPrimitive.Viewport>;
}

function Sources({ sources }: any) {
  if (!sources.length) return null;
  return <details className="source-cards"><summary>Sources & tool evidence · {sources.length}</summary>
    {sources.map((source: any, index: number) => <div key={index}><strong>{source.tool}</strong>
      <p>{source.result?.path || source.result?.source || 'Scoped native readback'}</p>
      <small>{source.result?.revision || source.result?.sha256 || 'Current request evidence'}</small></div>)}
  </details>;
}

function UserMessage() {
  return <MessagePrimitive.Root className="message user"><MessagePrimitive.Content/></MessagePrimitive.Root>;
}

function AssistantMessage() {
  return <MessagePrimitive.Root className="message assistant-message"><MessagePrimitive.Content/></MessagePrimitive.Root>;
}
