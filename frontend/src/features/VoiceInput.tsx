import { useRef, useState } from 'react';
import { Mic } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { api, lab } from '@/lib/api';
import { stopSpeech } from '@/lib/speech';

export function VoiceInput({ onText }: {onText: (text: string) => void}) {
  const [listening, setListening] = useState(false);
  const [source, setSource] = useState('mac');
  const [error, setError] = useState('');
  const recorder = useRef<MediaRecorder | null>(null);
  async function toggle() {
    if (recorder.current?.state === 'recording') { recorder.current.stop(); return; }
    if (listening) return;
    setError(''); setListening(true); stopSpeech();
    try {
      await api(`${lab}/voice`, {enabled: false});
      if (source === 'homebrain') {
        const result = await api('/api/microphone/capture', {});
        if (result.text) onText(result.text);
        else setError('No English speech detected. Authorize the microphone in Settings.');
        setListening(false);
      } else recorder.current = await browserCapture(onText, setListening, setError);
    } catch (failure) { setError(String(failure)); setListening(false); }
  }
  return <span className="voice-input">
    <select aria-label="Push-to-talk microphone" value={source} disabled={listening} onChange={event => setSource(event.target.value)}>
      <option value="mac">Mac mic</option><option value="homebrain">Homebrain mic</option>
    </select>
    <Button variant={listening ? 'destructive' : 'ghost'} size="icon" onClick={toggle}
      aria-label={listening ? 'Stop listening' : 'Push to talk'}><Mic size={16}/></Button>
    {error && <span role="alert">{error}</span>}
  </span>;
}

async function browserCapture(onText: any, setListening: any, setError: any) {
  const stream = await navigator.mediaDevices.getUserMedia({audio: true});
  const media = new MediaRecorder(stream);
  const chunks: BlobPart[] = [];
  media.ondataavailable = event => chunks.push(event.data);
  media.onstop = async () => {
    stream.getTracks().forEach(track => track.stop()); setListening(false);
    try {
      const response = await fetch('/api/transcribe', {method: 'POST', body: new Blob(chunks, {type: media.mimeType})});
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Speech recognition unavailable');
      if (result.text) onText(result.text);
    } catch (failure) { setError(String(failure)); }
  };
  media.start();
  setTimeout(() => { if (media.state === 'recording') media.stop(); }, 15000);
  return media;
}
