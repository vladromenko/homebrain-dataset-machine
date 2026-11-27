import { useRef, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { api, lab } from '@/lib/api';

export function ObservationCapture() {
  const [seconds, setSeconds] = useState(30);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<any>(null);
  const key = useRef(crypto.randomUUID());
  async function capture() {
    if (busy) return;
    setBusy(true);
    try {
      const value = await api(`${lab}/observation-capture`, {seconds, idempotency_key: key.current});
      setResult(value);
      if (value.status === 'accepted') window.dispatchEvent(new Event('homebrain-capture-changed'));
    } catch (error) {setResult({status: 'unknown', message: String(error)});}
    finally {setBusy(false);}
  }
  return <Card className="settings-card"><h2>Record shared sensors</h2>
    <p>The native observation recorder saves available cameras, depth, lidar and telemetry. Diagnostic evidence is ineligible for motor training.</p>
    <select aria-label="Sensor recording duration" value={seconds} disabled={busy || !!result}
      onChange={event => setSeconds(Number(event.target.value))}>
      {[15, 30, 60].map(value => <option key={value} value={value}>{value} seconds</option>)}
    </select>{' '}<Button disabled={busy || !!result} onClick={capture}>{busy ? 'Requesting capture…' : 'Record sensors'}</Button>
    {result && <p role="status">{result.message} {result.native?.id}</p>}
    {result?.status !== 'unknown' && result && <Button variant="outline" onClick={() => {key.current = crypto.randomUUID(); setResult(null);}}>New capture</Button>}
    {result?.status === 'unknown' && <p>Inspect the native archives below before requesting another capture. Start is never replayed automatically.</p>}
  </Card>;
}
