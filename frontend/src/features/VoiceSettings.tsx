import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { muteSpeech } from '@/lib/speech';
import { api, lab } from '@/lib/api';

export function VoiceSettings({ session }: any) {
  const [voice, setVoice] = useState<any>(null);
  const [output, setOutput] = useState('');
  const [input, setInput] = useState('');
  const [message, setMessage] = useState('');
  const refresh = () => api(`${lab}/voice`).then(setVoice).catch(error => setMessage(String(error)));
  useEffect(() => {
    refresh(); const timer = setInterval(refresh, 4000);
    return () => clearInterval(timer);
  }, []);
  async function authorize() {
    try {
      await api('/api/microphone/authorize', {device: input || voice.input.selected.id, confirmed: true});
      await refresh();
    } catch (error) { setMessage(String(error)); }
  }
  async function mode(enabled: boolean) {
    if (enabled) muteSpeech();
    try { setVoice(await api(`${lab}/voice`, {enabled, output: output || null, selection: session?.session_id || null})); }
    catch (error) { setMessage(String(error)); }
  }
  return <>
    <Card className="settings-card"><h2>Voice & persistent audio devices</h2>
      <p>Selected input: {voice?.input.selected?.name || 'No local microphone'} · {voice?.input.state || 'Checking'}</p>
      <DeviceChoice label="Microphone to authorize" devices={voice?.input.devices} value={input} set={setInput}/>
      <Button variant="outline" disabled={!voice?.input.selected} onClick={authorize}>Authorize this microphone</Button>
      <DeviceChoice label="Authorized local speaker" devices={voice?.outputs} value={output} set={setOutput}/>
      <div className="robot-tabs"><Button disabled={voice?.enabled} onClick={() => mode(true)}>Start local voice mode</Button>
        <Button variant="outline" disabled={!voice?.enabled} onClick={() => mode(false)}>Mute local voice mode</Button></div>
      <p>{voice?.state || 'Muted'} · Half duplex. Say “Hey, Homebrain” before a request. Local mode can work after the browser closes.</p>
      <p>Using browser push-to-talk or browser replies mutes local mode to keep one speech route active.</p>
      {message && <p role="status">{message}</p>}
      <p className="muted">An authorized dedicated microphone has priority. The authorized C920 remains a fallback. Discovery alone does not grant listening permission.</p>
    </Card>
    <SpeechBenchmark enabled={voice?.enabled}/>
  </>;
}

function DeviceChoice({ label, devices, value, set }: any) {
  return <label>{label}<select value={value} onChange={event => set(event.target.value)}>
    <option value="">Use current selection / no local output</option>
    {devices?.map((device: any) => <option key={device.id} value={device.id}>{device.name} · {device.kind}</option>)}
  </select></label>;
}

function SpeechBenchmark({ enabled }: any) {
  const [phrases, setPhrases] = useState<string[]>([]);
  const [reference, setReference] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { api(`${lab}/voice/benchmark`).then(data => {
    setPhrases(data.phrases); setReference(data.phrases[0]);
    if (data.latest) setMessage(`Last test: ${Math.round(data.latest.word_error_rate * 100)}% word error rate for one utterance.`);
  }); }, []);
  async function test() {
    setBusy(true); setMessage('Speak the reference now. Capturing eight seconds on Homebrain…');
    try {
      const result = await api(`${lab}/voice/benchmark`, {reference});
      setMessage(`Heard: “${result.recognized}”. Word error rate: ${Math.round(result.word_error_rate * 100)}%. Capture and recognition: ${result.elapsed_s.toFixed(1)} s. One utterance only.`);
    } catch (error) { setMessage(String(error)); }
    finally { setBusy(false); }
  }
  return <Card className="settings-card"><h2>English robotics speech test</h2>
    <p>Read the reference aloud near the selected Homebrain microphone. Mute local voice mode first.</p>
    <select aria-label="Reference sentence" value={reference} onChange={event => setReference(event.target.value)}>
      {phrases.map(phrase => <option key={phrase}>{phrase}</option>)}
    </select><p>{reference}</p>
    <Button disabled={busy || enabled || !reference} onClick={test}>Test microphone for eight seconds</Button>
    {message && <p role="status">{message}</p>}
  </Card>;
}
