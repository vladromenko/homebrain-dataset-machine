import { lazy, Suspense, useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { api, lab } from '@/lib/api';
const WebViewer = lazy(() => import('@rerun-io/web-viewer-react'));

export function ReplayCatalog() {
  const [records, setRecords] = useState<any[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  useEffect(() => {
    const refresh = () => api(`${lab}/replays`).then(value => setRecords(value.captures)).catch(() => {});
    refresh(); const timer = setInterval(refresh, 4000);
    window.addEventListener('homebrain-capture-changed', refresh);
    return () => {clearInterval(timer); window.removeEventListener('homebrain-capture-changed', refresh);};
  }, []);
  return <>
    <div className="list-heading"><h2>Sensor archives & 3D replay</h2><span>Native MCAP · observation evidence</span></div>
    <div className="task-list">{records.map(record => <Card className="task-row" key={record.id}>
      <div><h3>{record.kind}</h3><p>{record.id} · {record.requested_seconds} s · {record.phase}</p>
        <p>Diagnostic evidence · training ineligible · native coordinate frames</p></div>
      <Button variant="outline" disabled={record.phase !== 'complete'} onClick={() => setSelected(record.id)}>Open replay</Button>
    </Card>)}</div>
    <Dialog open={!!selected} onOpenChange={value => {if (!value) setSelected(null);}}>
      <DialogContent className="replay-dialog"><DialogHeader><DialogTitle>Native sensor replay</DialogTitle></DialogHeader>
        {selected && <Replay identifier={selected}/>}
      </DialogContent>
    </Dialog>
  </>;
}

function Replay({identifier}: {identifier: string}) {
  const [state, setState] = useState<any>({state: 'pending'});
  const [url, setUrl] = useState('');
  useEffect(() => {
    let active = true, blob = '', pending = false;
    api(`${lab}/replays/${identifier}`, {}).then(setState).catch(error => setState({state: 'failed', message: String(error)}));
    const timer = setInterval(async () => {
      if (pending) return;
      pending = true;
      try {
        const value = await api(`${lab}/replays/${identifier}`);
        if (active) setState(value);
        if (active && value.state === 'ready' && !blob) {
          const response = await fetch(value.url, {credentials: 'same-origin'});
          if (!response.ok) throw new Error('Native derived view unavailable');
          blob = URL.createObjectURL(await response.blob());
          if (active) setUrl(blob);
        }
      } catch (error) {if (active) setState({state: 'failed', message: String(error)});}
      finally {pending = false;}
    }, 1500);
    return () => {active = false; clearInterval(timer); if (blob) URL.revokeObjectURL(blob);};
  }, [identifier]);
  return <div><p className="muted">Derived local view of the original MCAP. Native names and clocks are retained; unknown transforms remain unknown.</p>
    {url ? <Suspense fallback={<p>Loading local viewer…</p>}>
      <WebViewer width="100%" height="62vh" rrd={url} analytics="off" hideWelcomeScreen memoryLimit="512MB"/>
    </Suspense> : <div className="viewer-loading">{state.state === 'failed' ? state.message : 'Preparing synchronized local replay…'}</div>}
  </div>;
}
